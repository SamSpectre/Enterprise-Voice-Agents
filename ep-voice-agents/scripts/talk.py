"""
Talk to your ElevenLabs agent from the terminal.

Usage:
    uv run python scripts/talk.py

Press 'q' + Enter to end the conversation.
"""

import os
import threading
from dotenv import load_dotenv

load_dotenv()

from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation, ConversationInitiationData
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface


def main():
    agent_id = os.getenv("AGENT_ID")
    api_key = os.getenv("ELEVENLABS_API_KEY")

    if not agent_id or not api_key:
        print("Error: Set AGENT_ID and ELEVENLABS_API_KEY in your .env file")
        return

    candidate_name = input("Candidate name: ").strip() or "Test Candidate"
    company_name = input("Company name: ").strip() or "EP Group"

    client = ElevenLabs(api_key=api_key)

    audio_interface = DefaultAudioInterface()
    audio_interface.INPUT_FRAMES_PER_BUFFER = 1600  # 100ms @ 16kHz

    # Patch stop() to swallow PyAudio crash on Windows
    _original_stop = audio_interface.stop

    def _safe_stop():
        try:
            _original_stop()
        except OSError:
            pass

    audio_interface.stop = _safe_stop

    stop = threading.Event()

    conversation = Conversation(
        client=client,
        agent_id=agent_id,
        requires_auth=True,
        audio_interface=audio_interface,
        config=ConversationInitiationData(
            dynamic_variables={
                "candidate_name": candidate_name,
                "company_name": company_name,
            },
            conversation_config_override={
                "tts": {
                    "optimize_streaming_latency": 4,
                },
            },
        ),
        callback_agent_response=lambda response: print(f"\n  Agent: {response}"),
        callback_user_transcript=lambda transcript: print(f"\n  You:   {transcript}"),
        callback_latency_measurement=lambda latency: print(f"  [latency: {latency}ms]"),
        callback_end_session=lambda: stop.set(),
    )

    print("\n--- EP Voice Agent ---")
    print(f"Agent ID: {agent_id}")
    print("Type 'q' and press Enter to end the conversation.\n")
    print("Starting session...\n")

    conversation.start_session()

    # Wait for quit input or agent ending the session
    def wait_for_quit():
        while not stop.is_set():
            try:
                line = input()
                if line.strip().lower() == "q":
                    stop.set()
            except EOFError:
                stop.set()

    quit_thread = threading.Thread(target=wait_for_quit, daemon=True)
    quit_thread.start()
    stop.wait()

    print("\n--- Session ended ---")
    os._exit(0)


if __name__ == "__main__":
    main()
