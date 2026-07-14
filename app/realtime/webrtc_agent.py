"""
WebRTC entry point: a LiveKit agent worker that joins a room, listens to a
caller's microphone track over real WebRTC, runs it through the same
streaming transcription -> pipeline -> TTS chain as the WebSocket endpoint,
and publishes the spoken reply back into the room as an audio track.

LiveKit (https://livekit.io, Apache-2.0) is self-hosted via
docker-compose.yml's `livekit` service — no phone number or paid telephony
account required. This gets browser/mobile-app callers onto real WebRTC;
it does not by itself answer PSTN phone calls (that needs a SIP trunk
provider in front of LiveKit, e.g. Twilio or Telnyx, which is a config
addition, not a code change, once a trunk is provisioned).

Run with:  python -m app.realtime.webrtc_agent dev
"""

import asyncio
import logging

from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
)

from app.config import settings
from app.services.streaming_transcriber import StreamingSession
from app.services.synthesizer import get_synthesizer, SynthesisError
from app.main import get_transcriber  # reuse the same Groq transcriber factory
from app.pipeline import run_text_pipeline

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
NUM_CHANNELS = 1


async def _publish_reply(room: rtc.Room, mp3_bytes: bytes):
    """Decode the synthesized MP3 to PCM and publish it as a LiveKit audio track."""
    import io
    from pydub import AudioSegment

    audio = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
    audio = audio.set_frame_rate(SAMPLE_RATE).set_channels(NUM_CHANNELS).set_sample_width(2)

    source = rtc.AudioSource(SAMPLE_RATE, NUM_CHANNELS)
    track = rtc.LocalAudioTrack.create_audio_track("agent-reply", source)
    await room.local_participant.publish_track(track)

    frame_ms = 20
    frame_samples = SAMPLE_RATE * frame_ms // 1000
    raw = audio.raw_data
    frame_bytes = frame_samples * 2
    for i in range(0, len(raw), frame_bytes):
        chunk = raw[i : i + frame_bytes]
        if len(chunk) < frame_bytes:
            chunk = chunk + b"\x00" * (frame_bytes - len(chunk))
        frame = rtc.AudioFrame(
            data=chunk, sample_rate=SAMPLE_RATE, num_channels=NUM_CHANNELS,
            samples_per_channel=frame_samples,
        )
        await source.capture_frame(frame)
        await asyncio.sleep(frame_ms / 1000)


async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info(f"Voice agent joined room {ctx.room.name}")

    session = StreamingSession(transcriber=get_transcriber())
    synthesizer = get_synthesizer()

    @ctx.room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication, participant):
        if track.kind != rtc.TrackKind.KIND_AUDIO:
            return
        asyncio.create_task(_consume_audio(track))

    async def _consume_audio(track: rtc.Track):
        stream = rtc.AudioStream(track, sample_rate=SAMPLE_RATE, num_channels=NUM_CHANNELS)
        async for event in stream:
            frame = event.frame
            session.push_frame(bytes(frame.data))

            if session.is_utterance_complete():
                final = session.finalize()
                if final is None or not final.text.strip():
                    continue
                logger.info(f"Caller said: {final.text}")
                pipeline_result = run_text_pipeline(final.text)
                logger.info(
                    f"Routed to {pipeline_result.specialty} "
                    f"(confidence={pipeline_result.confidence:.2f})"
                )
                try:
                    mp3_bytes = synthesizer.synthesize(pipeline_result.reply_text)
                    await _publish_reply(ctx.room, mp3_bytes)
                except SynthesisError as e:
                    logger.warning(f"TTS reply failed: {e}")

    await asyncio.Future()  # keep the job alive until the room closes


def _prewarm(proc: JobProcess):
    proc.userdata["transcriber"] = get_transcriber()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=_prewarm,
            ws_url=settings.livekit_url,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
    )
