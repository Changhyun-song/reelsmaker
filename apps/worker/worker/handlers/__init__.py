from worker.handlers.script import handle_script_generate, handle_script_structure
from worker.handlers.scene import handle_scene_plan, handle_scene_regenerate
from worker.handlers.shot import handle_shot_plan, handle_shot_regenerate
from worker.handlers.frame import handle_frame_plan, handle_frame_regenerate
from worker.handlers.image import handle_image_generate
from worker.handlers.video import handle_video_generate
from worker.handlers.tts import handle_tts_generate
from worker.handlers.subtitle import handle_subtitle_generate
from worker.handlers.timeline import handle_timeline_compose
from worker.handlers.render import handle_render_final
from worker.handlers.story_prompts import handle_story_prompts

__all__ = [
    "handle_script_generate",
    "handle_script_structure",
    "handle_scene_plan",
    "handle_scene_regenerate",
    "handle_shot_plan",
    "handle_shot_regenerate",
    "handle_frame_plan",
    "handle_frame_regenerate",
    "handle_image_generate",
    "handle_video_generate",
    "handle_tts_generate",
    "handle_subtitle_generate",
    "handle_timeline_compose",
    "handle_render_final",
    "handle_story_prompts",
]
