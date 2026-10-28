from flask import Flask, render_template, request, send_from_directory
from google import genai
from PIL import Image
import os
import sqlite3
import time
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "database.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================================
# GEMINI AI
# ============================================================

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Set your Gemini API key in the .env file."
    )

client = genai.Client(api_key=api_key)


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return render_template("home.html")


# ============================================================
# GENERATE PAGE
# ============================================================

@app.route("/generate")
def generate_page():
    return render_template("generate.html")


# ============================================================
# FEATURES
# ============================================================

@app.route("/features")
def features():
    return render_template("features.html")


# ============================================================
# ABOUT
# ============================================================

@app.route("/about")
def about():
    return render_template("about.html")

# =============================================================
# FLOWCHART
# =============================================================
@app.route("/flowchart")
def flowchart():
    return render_template("flowchart.html")
# ============================================================
# UPLOADED FILES
# ============================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# ============================================================
# GENERATE CAPTION
# ============================================================

@app.route("/generate-caption", methods=["POST"])
def generate():

    # Get content type
    content_type = request.form.get("content_type", "image")

    # ========================================================
    # IMAGE CAPTION GENERATION
    # ========================================================

    if content_type == "image":

        # Get uploaded image
        image = request.files.get("image")

        # Check image
        if image is None or image.filename == "":
            return render_template(
                "generate.html",
                error="Please select an image."
            )

        # Get user selections
        platform = request.form.get("platform", "Instagram")
        style = request.form.get("style", "Aesthetic")
        length = request.form.get("length", "Medium")

        # ----------------------------------------------------
        # Save Image
        # ----------------------------------------------------

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            image.filename
        )

        image.save(filepath)

        # ----------------------------------------------------
        # Open Image
        # ----------------------------------------------------

        img = Image.open(filepath)

        # ----------------------------------------------------
        # AI Prompt
        # ----------------------------------------------------

      
        prompt = f"""
You are a skilled social media caption writer who understands
visual storytelling, illustrations, photography and human emotions.

Analyze the uploaded image carefully before writing anything.

Platform: {platform}
Selected style: {style}
Requested length: {length}

STEP 1 — UNDERSTAND THE IMAGE

Identify:
- What is actually visible?
- What is the main scene, activity or moment?
- What mood or atmosphere is supported by the visuals?
- Is it a photograph, digital illustration, anime-style artwork,
  fantasy artwork, landscape, portrait or another visual type?
- What makes this particular image distinctive?

IMPORTANT:
Visual style and image context are different things.

For example, "anime character" describes a type of subject.
It does not explain the scene, mood or story.

If the image is an illustrated fantasy scene, describe the actual
visible setting, activity and atmosphere when supported by evidence.
Do not stop at labels such as "anime character", "cartoon girl",
"beautiful image" or "nice picture".

Do not assume that an illustration depicts a real event.
Do not invent a location, relationship, activity or backstory.
Do not claim a specific character identity unless it is certain
and relevant to the caption.

STEP 2 — WRITE 3 DISTINCT CAPTIONS

Write exactly 3 captions that:
- Match the actual image and its visible context.
- Sound natural, personal and human-written.
- Feel specific to this image, not suitable for every image.
- Express the scene or mood instead of merely listing objects.
- Have different wording and perspectives.
- Avoid robotic phrases and unnecessary descriptions.
- Do not all start with the same words.
- Do not mention "AI", "image", "photo" or "picture".

Platform: {platform}
Style: {style}

Style instructions:
Aesthetic: soft, expressive, elegant and visually fitting.
Funny: playful and relatable only when appropriate.
Professional: clear, polished and purposeful.
Motivational: inspiring without forced positivity.
Travel: travel-related only when supported by the image.

LENGTH:
Short: 8-10 words per caption.
Medium: 11-13 words per caption.
Long: 13-16 words per caption.

STEP 3 — CHECK YOUR WORK

Before responding, check that:
- Each caption reflects the actual image.
- No unsupported story or detail has been invented.
- The captions are not generic or repetitive.
- The selected style and requested length are followed.
- Artwork is understood as artwork, not automatically as a real scene.

Return ONLY in this exact format:

Image Category:
<short description of the main scene or visual context>

Caption 1:
<caption>

Caption 2:
<caption>

Caption 3:
<caption>

Hashtags:
<exactly 5 relevant hashtags>

Emojis:
<exactly 3 relevant emojis>

The category should describe the scene or context when possible,
not merely label the subject as an anime or cartoon character.
Hashtags and emojis must match the actual image.
"""

        # ----------------------------------------------------
        # Gemini AI Request
        # ----------------------------------------------------

      
   
        # Gemini AI Request with Retry

        try:
            output = None

            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model="gemini-3.5-flash-lite",
                        contents=[prompt, img]
                    )

                    output = (response.text or "").strip()
                    if not output:
                         raise ValueError("Gemini returned an empty response.")
                    break

                except Exception as e:
                    error_message = str(e).upper()

                    temporary_error = any(
                        term in error_message
                        for term in [
                            "503",
                            "UNAVAILABLE",
                            "HIGH DEMAND",
                            "429",
                            "RESOURCE_EXHAUSTED"
                        ]
                    )

                    if not temporary_error or attempt == 2:
                        raise

                    wait_seconds = 2 ** (attempt + 1)
                    print(
                        f"Gemini temporarily unavailable. "
                        f"Retrying in {wait_seconds} seconds..."
                    )
                    time.sleep(wait_seconds)

        except Exception as e:
            print("\n========== IMAGE ERROR ==========")
            print(str(e))
            print("=================================\n")

            return render_template(
                "generate.html",
                error="Image processing failed. Please try again later."
            )

        # Variables — same indentation as try/except above
        category = ""
        caption1 = ""
        caption2 = ""
        caption3 = ""
        hashtags = ""
        emojis = ""

        section = None

      
        # Parse Gemini Response
        for line in output.splitlines():
            line = line.strip()

            if not line:
                continue

            lower = line.lower()

            if lower.startswith("image category"):
                section = "category"
                if ":" in line:
                    category = line.split(":", 1)[1].strip()
                continue

            elif lower.startswith("caption 1"):
                section = "caption1"
                if ":" in line:
                    caption1 = line.split(":", 1)[1].strip()
                continue

            elif lower.startswith("caption 2"):
                section = "caption2"
                if ":" in line:
                    caption2 = line.split(":", 1)[1].strip()
                continue

            elif lower.startswith("caption 3"):
                section = "caption3"
                if ":" in line:
                    caption3 = line.split(":", 1)[1].strip()
                continue

            elif lower.startswith("hashtags"):
                section = "hashtags"
                if ":" in line:
                    hashtags = line.split(":", 1)[1].strip()
                continue

            elif lower.startswith("emojis"):
                section = "emojis"
                if ":" in line:
                    emojis = line.split(":", 1)[1].strip()
                continue

            # Handle multiline responses
            if section == "category":
                category += " " + line
            elif section == "caption1":
                caption1 += " " + line
            elif section == "caption2":
                caption2 += " " + line
            elif section == "caption3":
                caption3 += " " + line
            elif section == "hashtags":
                hashtags += " " + line
            elif section == "emojis":
                emojis += " " + line

        # ----------------------------------------------------
        # Clean Output
        # ----------------------------------------------------

        category = category.strip()
        caption1 = caption1.strip()
        caption2 = caption2.strip()
        caption3 = caption3.strip()
        hashtags = hashtags.strip()
        emojis = emojis.strip()

        # ----------------------------------------------------
        # Save Caption to SQLite
        # ----------------------------------------------------

        try:

            conn = sqlite3.connect(DB_PATH)

            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO captions
                (image_name, caption, hashtags, emojis)
                VALUES (?, ?, ?, ?)
            """, (
                image.filename,
                caption1,
                hashtags,
                emojis
            ))

            conn.commit()
            conn.close()

        except Exception as e:

            print("Database error:", str(e))

        # ----------------------------------------------------
        # Show Result
        # ----------------------------------------------------

        return render_template(
            "generate.html",
            category=category,
            caption1=caption1,
            caption2=caption2,
            caption3=caption3,
            hashtags=hashtags,
            emojis=emojis,
            image_file=image.filename
        )


    # ========================================================
    # VIDEO CAPTION GENERATION
    # ========================================================

    elif content_type == "video":

        # ----------------------------------------------------
        # Get uploaded video
        # ----------------------------------------------------

        video = request.files.get("video")

        # ----------------------------------------------------
        # Check video
        # ----------------------------------------------------

        if video is None or video.filename == "":
            return render_template(
                "generate.html",
                error="Please select a video."
            )

        # ----------------------------------------------------
        # Get user selections
        # ----------------------------------------------------

        platform = request.form.get("platform", "Instagram")
        style = request.form.get("style", "Aesthetic")
        length = request.form.get("length", "Medium")

        # ----------------------------------------------------
        # Save Video
        # ----------------------------------------------------

        video_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            video.filename
        )

        video.save(video_path)

        # ----------------------------------------------------
        # AI Prompt for Video
        # ----------------------------------------------------

       
        prompt = f"""
You are an expert social media storyteller and caption writer.

Analyze the uploaded video as a sequence of visual moments.
Understand the overall scene and activity before writing captions.

Platform: {platform}
Selected style: {style}
Requested length: {length}

STEP 1 — UNDERSTAND THE VIDEO

Determine:
- What is happening throughout the video?
- What is the main activity, event or experience?
- How do the visible moments connect?
- What atmosphere or mood is supported by the visuals?
- What makes this video different from a generic video?

Do not describe only the most obvious object.
Understand the overall context using the available visual evidence.

For example:
- Cake cutting with birthday decorations may indicate a birthday.
- Wedding rituals or wedding decorations may indicate a wedding.
- A sequence of scenic locations may indicate a travel experience.
- An illustrated animation should be understood as animation,
  not automatically described as a real-life event.

These are examples, not assumptions. Use them only when supported
by the actual video.

Do not invent dialogue, names, ages, relationships, locations,
events or emotions that cannot reasonably be inferred.

STEP 2 — WRITE 3 CAPTIONS

Create exactly 3 different captions that:
- Explain the main experience, event or activity.
- Reflect the overall video, not just one frame.
- Sound natural, expressive and human-written.
- Include meaningful context without inventing a story.
- Avoid generic phrases and repetitive wording.
- Do not use robotic openings or unnecessary descriptions.

Style:
Aesthetic: soft, expressive and visually fitting.
Funny: playful and relatable when appropriate.
Professional: polished and natural.
Motivational: inspiring when supported by the context.
Travel: travel-focused only if the video is about travel.

Length:
Short: 8-10 words per caption.
Medium: 11-13 words per caption.
Long: 13-16 words per caption.

STEP 3 — QUALITY CHECK

Check that all captions:
- Reflect the actual video context.
- Are distinct from one another.
- Match the selected style and length.
- Do not invent events or unsupported details.
- Describe the experience rather than simply listing objects.

Return ONLY in this exact format:

Image Category:
<main event, activity or visual context>

Caption 1:
<caption>

Caption 2:
<caption>

Caption 3:
<caption>

Hashtags:
<exactly 5 relevant hashtags>

Emojis:
<exactly 3 relevant emojis>

Hashtags and emojis must match the video's main context.
If the video is animation or artwork, do not automatically
describe it as a real-life event.
"""


        # ----------------------------------------------------
        # Process Video with Gemini
        # ----------------------------------------------------

        try:

            # Upload video to Gemini
            uploaded_video = client.files.upload(
                file=video_path
            )

            print(
                "Video uploaded. Waiting for Gemini to process it..."
            )

            # ------------------------------------------------
            # Wait until video becomes ACTIVE
            # ------------------------------------------------

            while (
                not uploaded_video.state
                or uploaded_video.state.name != "ACTIVE"
            ):

                print("Video processing...")
                print("Current state:", uploaded_video.state)

                if (
                    uploaded_video.state
                    and uploaded_video.state.name == "FAILED"
                ):
                    raise RuntimeError(
                        "Gemini failed to process the video."
                    )

                time.sleep(5)

                uploaded_video = client.files.get(
                    name=uploaded_video.name
                )

            print(
                "Video is ACTIVE. Generating caption..."
            )

           
            # ------------------------------------------------
            # Generate captions from video
            # ------------------------------------------------

            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=[
                    prompt,
                    uploaded_video
                ]
            )

            output = (response.text or "").strip()

            if not output:
                raise ValueError("Gemini returned an empty response.")

            print("\n========== GEMINI VIDEO OUTPUT ==========")
            print(output)
            print("=========================================\n")

            # ------------------------------------------------
            # Variables
            # ------------------------------------------------

            category = ""
            caption1 = ""
            caption2 = ""
            caption3 = ""
            hashtags = ""
            emojis = ""

            section = None

            # ------------------------------------------------
            # Parse Gemini Response
            # ------------------------------------------------

            for line in output.splitlines():

                line = line.strip()

                if not line:
                    continue

                lower = line.lower()

                if lower.startswith("image category"):

                    section = "category"

                    if ":" in line:
                        category = line.split(
                            ":", 1
                        )[1].strip()

                    continue

                elif lower.startswith("caption 1"):

                    section = "caption1"

                    if ":" in line:
                        value = line.split(
                            ":", 1
                        )[1].strip()

                        if value:
                            caption1 = value

                    continue

                elif lower.startswith("caption 2"):

                    section = "caption2"

                    if ":" in line:
                        value = line.split(
                            ":", 1
                        )[1].strip()

                        if value:
                            caption2 = value

                    continue

                elif lower.startswith("caption 3"):

                    section = "caption3"

                    if ":" in line:
                        value = line.split(
                            ":", 1
                        )[1].strip()

                        if value:
                            caption3 = value

                    continue

                elif lower.startswith("hashtags"):

                    section = "hashtags"

                    if ":" in line:
                        value = line.split(
                            ":", 1
                        )[1].strip()

                        if value:
                            hashtags = value

                    continue

                elif lower.startswith("emojis"):

                    section = "emojis"

                    if ":" in line:
                        value = line.split(
                            ":", 1
                        )[1].strip()

                        if value:
                            emojis = value

                    continue

                # Add remaining lines
                if section == "category":
                    category += " " + line

                elif section == "caption1":
                    caption1 += " " + line

                elif section == "caption2":
                    caption2 += " " + line

                elif section == "caption3":
                    caption3 += " " + line

                elif section == "hashtags":
                    hashtags += " " + line

                elif section == "emojis":
                    emojis += " " + line

            # ------------------------------------------------
            # Clean Output
            # ------------------------------------------------

            category = category.strip()
            caption1 = caption1.strip()
            caption2 = caption2.strip()
            caption3 = caption3.strip()
            hashtags = hashtags.strip()
            emojis = emojis.strip()

            # ------------------------------------------------
            # Show Video Result
            # IMPORTANT: generate.html, not index.html
            # ------------------------------------------------

            return render_template(
                "generate.html",
                category=category,
                caption1=caption1,
                caption2=caption2,
                caption3=caption3,
                hashtags=hashtags,
                emojis=emojis,
                image_file=video.filename
            )

        except Exception as e:

            print("\n========== VIDEO ERROR ==========")
            print(str(e))
            print("=================================\n")

            return render_template(
                "generate.html",
                error="Video processing failed: " + str(e)
            )


    # ========================================================
    # UNKNOWN CONTENT TYPE
    # ========================================================

    else:

        return render_template(
            "generate.html",
            error="Invalid content type."
        )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)
