from google.cloud import texttospeech
import os


def text_to_speech(text, output_location, logger ):
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    output_file = os.path.join(output_location, 'audio.mp3')
    with open("output.mp3", "wb") as out:
        out.write(response.audio_content)
        logger.info(f'Audio content written to file: {output_file}')