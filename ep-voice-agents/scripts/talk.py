"""
Talk to your ElevenLabs agent from the terminal.

Usage:
    uv run python scripts/talk.py

Press Ctrl+C to end the conversation.
"""

import os
import signal
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

    # Prompt for dynamic variables required by the agent
    candidate_name = input("Candidate name: ").strip() or "Test Candidate"
    company_name = input("Company name: ").strip() or "EP Group"

    client = ElevenLabs(api_key=api_key)

    audio_interface = DefaultAudioInterface()
    # Reduce input buffer from 250ms to 100ms for snappier mic pickup
    audio_interface.INPUT_FRAMES_PER_BUFFER = 1600  # 100ms @ 16kHz

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
                    "optimize_streaming_latency": 4,  # max optimization (1-4)
                },
            },
        ),
        callback_agent_response=lambda response: print(f"\n  Agent: {response}"),
        callback_user_transcript=lambda transcript: print(f"\n  You:   {transcript}"),
        callback_latency_measurement=lambda latency: print(f"  [latency: {latency}ms]"),
    )

    # Graceful shutdown on Ctrl+C
    signal.signal(signal.SIGINT, lambda sig, frame: conversation.end_session())

    print("\n--- EP Voice Agent ---")
    print(f"Agent ID: {agent_id}")
    print("Press Ctrl+C to end the conversation.\n")
    print("Starting session...\n")

    conversation.start_session()
    conversation_id = conversation.wait_for_session_end()

    print(f"\n--- Session ended ---")
    print(f"Conversation ID: {conversation_id}")
    print("View transcript at: https://elevenlabs.io/app/conversational-ai")


if __name__ == "__main__":
    main()