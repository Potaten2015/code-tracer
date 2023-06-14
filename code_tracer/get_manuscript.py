from dotenv import load_dotenv

load_dotenv()


def create_payload(change_files, config):
    changes = {filename: [values[0]["content"], values[-1]["content"]] for filename, values in change_files.items()}
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


def get_manuscript(payload):
    pass