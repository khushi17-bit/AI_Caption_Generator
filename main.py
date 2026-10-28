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
You are an expert social media caption writer.

Analyze the uploaded image carefully and understand what is actually visible.

Platform: {platform}
Style: {style}
Caption Length: {length}

Create exactly 3 different, natural and meaningful social media captions.

Return ONLY in this exact format:

Image Category:
<one short category>

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

RULES:

- All captions must be relevant to the uploaded image.
- All 3 captions must be different.
- Write naturally like a real person.
- Do not invent people, locations, objects or events.
- Do not say "this image", "this photo" or "this picture".
- Do not use unnecessary words.

LENGTH:

Short:
8-10 words.

Medium:
11-13 words.

Long:
13-16 words.

STYLE:

Aesthetic:
Soft, elegant and visually appealing.

Funny:
Light, natural and relatable.

Professional:
Clear, polished and confident.

Motivational:
Positive and inspiring.

Travel:
Natural and engaging travel-related wording when appropriate.

HASHTAGS:
Exactly 5 relevant hashtags.

EMOJIS:
Exactly 3 relevant emojis.
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
You are an advanced social media caption generator.

Your job is NOT simply to identify objects in the video.

Your main job is to understand the STORY, EVENT, ACTIVITY and CONTEXT
of the video.

Analyze the uploaded video carefully from beginning to end.

FIRST determine what the video is actually about.

Pay special attention to:

- The main event or occasion
- What people are doing
- The overall activity
- The relationship between the different visual elements
- The mood and atmosphere
- Important actions happening in the video
- Objects that help identify the event
- Text, decorations, signs or other clues visible in the video

IMPORTANT CONTEXT RULE:

Do NOT make the caption mainly about an object when that object is
only part of a larger event.

For example:

If the video shows someone cutting a cake with birthday decorations,
the main context is likely a BIRTHDAY CELEBRATION, not simply "cake".

GOOD:
"Celebrating another year of life, surrounded by love, laughter and my favorite people."

BAD:
"A delicious cake making the celebration extra sweet."

The cake is an important clue, but the EVENT is the birthday.

If the video shows decorations, candles, people celebrating,
birthday wishes, or a cake-cutting ceremony, consider the overall
birthday celebration rather than focusing only on the cake.

However, NEVER assume "birthday" if there is no reasonable visual
evidence for it.

Do not invent:

- Age
- Location
- Names
- Relationships
- Specific people
- Events
- Emotions
- Activities

Only use information supported by the video.

Platform: {platform}
Style: {style}
Caption Length: {length}

Create exactly 3 different captions.

The 3 captions must:

1. Focus on the main event or story.
2. Include important context from the video.
3. Sound natural and human.
4. Be meaningful rather than generic.
5. Be different from each other.
6. Match the selected platform and style.
7. Avoid unnecessary description of individual objects.

Return ONLY in this format:

Image Category:
<main event or activity>

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

LENGTH:

Short:
8-10 words.

Medium:
11-13 words.

Long:
13-16 words.

STYLE:

Aesthetic:
Soft, elegant and visually appealing.

Funny:
Light, playful and relatable.

Professional:
Polished and natural.

Motivational:
Positive and inspiring when appropriate.

Travel:
Travel-focused only when the video is actually about travel.

HASHTAGS:
Exactly 5 hashtags related to the MAIN EVENT or CONTEXT,
not just individual objects.

EMOJIS:
Exactly 3 emojis related to the MAIN EVENT or CONTEXT.

FINAL QUALITY CHECK:

Before creating the captions, determine:

"What is this video REALLY about?"

Then write the captions around that answer.

Do not simply describe the most obvious object.

For example:

Birthday celebration → birthday-focused caption.
Wedding celebration → wedding-focused caption.
Travel journey → travel-focused caption.
Graduation → graduation-focused caption.
Festival celebration → festival-focused caption.
Food preparation → food/cooking-focused caption.

The final captions should explain the EXPERIENCE or EVENT,
not merely list what is visible.
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
