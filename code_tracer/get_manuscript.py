from dotenv import load_dotenv
import openai
import json
import os
import tiktoken

load_dotenv()


def create_payload(change_files, config, logger):
    logger.info("Creating GPT payload...")
    changes = {filename: {"beginning": values[0]["content"], "end": values[-1]["content"]} for filename, values in change_files.items()}
    
    payload = {
        "video_catch_phrase": config.get("video_catch_phrase"),
        "total_progress": config.get("total_progress"),
        "project_name": config.get("project_name"),
        "sessions": config.get("render_sessions"),
        "changes": changes,
        "seconds": config.get("video_length"),
        "sub_project": config.get("sub_project"),
    }
    return payload


def get_manuscript(payload, config, logger):
    model = "gpt-3.5-turbo"
    encoding = tiktoken.encoding_for_model(model)
    logger.info("Using GPT to generate manuscript...")
    context = open(config.get("context_filepath"), "r").read()
    tokens = {}
    for filename, file_changes in payload["changes"].items():
        tokens[filename] = len(encoding.encode(json.dumps(file_changes)))
    encoded = encoding.encode(f"{json.dumps(payload)} {context}")
    logger.info(f"Tokens per file: {tokens}")
    logger.info(f"Total tokens: {len(encoded)}")
    openai.api_key = config.get("openai_api_key")
    completion = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": json.dumps(payload)},
        ]
    )
    response = completion.choices[0].message.content
    response_json = json.loads(response)
    config.set("total_progress", response_json["total_progress"])
    config.write()
    output_location = config.get("video_output_dir")
    output_file = os.path.join(output_location, 'gpt_response.json')
    with open(output_file, "w") as out:
        json.dump(response_json, out, indent=4)
        logger.info(f'GPT response written to file: {output_file}')
    manuscript = response_json["manuscript"]
    return manuscript