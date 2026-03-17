---
name: learner-profile
description: "Build and manage personalized learner profiles with lesson plans and progress tracking. Use when: user wants to create a learning profile, set learning preferences, configure learning style, choose study materials, enable gamification, get AI-powered study recommendations, generate a lesson plan, start a lesson, get taught, view learning progress, or check their streak/points. Triggers: learner profile, learning style, study plan, learning preferences, gamify learning, learning recommendations, teach me, next lesson, my progress, lesson plan, learning dashboard, show my streak, show my points."
---

# Learner Profile Builder

Build a personalized learner profile that captures learning style, preferred materials, focus areas, and gamification preferences — then generate AI-powered learning recommendations, structured lesson plans, and interactive lessons using Snowflake Cortex.

## Workflow

```
Start
  ↓
Step 1: Setup (database/schema + table creation)
  ↓
Step 2: Gather Profile (name, style, materials, focus)
  ↓
  ⚠️ STOP: Confirm profile details
  ↓
Step 3: Gamification Preferences
  ↓
Step 4: Generate AI Recommendations (Cortex AI_COMPLETE)
  ↓
Step 5: Review & Approve
  ↓
  ⚠️ STOP: Confirm before saving
  ↓
Step 6: Save to Snowflake
  ↓
Step 7: Generate Lesson Plan (break AI plan into individual lessons)
  ↓
Done — Profile + Lesson Plan saved

═══════════════════════════════════
  Ongoing (triggered by user):
═══════════════════════════════════

"teach me" / "next lesson" → Step 8: Teach Mode
"my progress" / "dashboard" → Step 9: Progress Dashboard
```

---

### Step 1: Setup

**Goal:** Ensure the target database, schema, and table exist.

**Actions:**

1. **Ask** the user which database and schema to use for storing learner profiles:
   ```
   Which database and schema should I use to store your learner profile?
   Example: MY_DB.MY_SCHEMA
   ```

2. **Create** the tables if they don't exist:
   ```sql
   CREATE TABLE IF NOT EXISTS <DB>.<SCHEMA>.LEARNER_PROFILES (
       PROFILE_ID NUMBER AUTOINCREMENT PRIMARY KEY,
       LEARNER_NAME VARCHAR NOT NULL,
       LEARNING_STYLE VARCHAR NOT NULL,
       PREFERRED_MATERIALS VARCHAR NOT NULL,
       FOCUS_AREAS VARCHAR NOT NULL,
       GAMIFICATION BOOLEAN DEFAULT FALSE,
       GAMIFICATION_PREFS VARCHAR,
       AI_RECOMMENDATIONS VARCHAR,
       CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
       UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
   );

   CREATE TABLE IF NOT EXISTS <DB>.<SCHEMA>.LESSON_PLANS (
       PLAN_ID NUMBER AUTOINCREMENT PRIMARY KEY,
       PROFILE_ID NUMBER NOT NULL,
       PLAN_NAME VARCHAR NOT NULL,
       MONTH NUMBER,
       MONTH_THEME VARCHAR,
       WEEKLY_SCHEDULE VARCHAR,
       RESOURCES VARCHAR,
       CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
   );

   CREATE TABLE IF NOT EXISTS <DB>.<SCHEMA>.LESSONS (
       LESSON_ID NUMBER AUTOINCREMENT PRIMARY KEY,
       PROFILE_ID NUMBER NOT NULL,
       PLAN_ID NUMBER NOT NULL,
       LESSON_NUMBER NUMBER NOT NULL,
       TITLE VARCHAR NOT NULL,
       DESCRIPTION VARCHAR,
       LESSON_TYPE VARCHAR,
       NOTEBOOK_PATH VARCHAR,
       STATUS VARCHAR DEFAULT 'not_started',
       POINTS_EARNED NUMBER DEFAULT 0,
       STARTED_AT TIMESTAMP_NTZ,
       COMPLETED_AT TIMESTAMP_NTZ,
       CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
   );

   CREATE TABLE IF NOT EXISTS <DB>.<SCHEMA>.LEARNER_PROGRESS (
       PROFILE_ID NUMBER PRIMARY KEY,
       TOTAL_POINTS NUMBER DEFAULT 0,
       CURRENT_STREAK NUMBER DEFAULT 0,
       LONGEST_STREAK NUMBER DEFAULT 0,
       CURRENT_LEVEL VARCHAR DEFAULT 'ML Apprentice',
       LAST_ACTIVITY_DATE DATE,
       UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
   );
   ```

3. **Verify** the table was created successfully by running:
   ```sql
   DESCRIBE TABLE <DB>.<SCHEMA>.LEARNER_PROFILES;
   ```

**Output:** Table exists and is ready for inserts.

**Next:** Proceed to Step 2.

---

### Step 2: Gather Learner Profile

**Goal:** Collect the learner's core profile information.

**Actions:**

1. **Ask** the user for their **name**:
   ```
   What name should we use for this learner profile?
   ```

2. **Ask** the user to select their **learning style** (single select):

   | Style | Description |
   |-------|-------------|
   | Visual | Learn best through images, diagrams, charts, and spatial understanding |
   | Auditory | Learn best through listening, discussion, and verbal explanation |
   | Reading/Writing | Learn best through reading text, taking notes, and writing summaries |
   | Kinesthetic | Learn best through hands-on practice, experiments, and physical activity |

3. **Ask** the user to select their **preferred learning materials** (multi-select):

   | Material | Description |
   |----------|-------------|
   | Videos | Video tutorials, recorded lectures, visual walkthroughs |
   | Articles | Blog posts, documentation, written tutorials |
   | Books | Textbooks, reference books, comprehensive guides |
   | Interactive Labs | Hands-on coding exercises, sandboxes, guided projects |
   | Podcasts | Audio content, interviews, discussion-based learning |

4. **Ask** the user for their **focus areas** (free text):
   ```
   What topics or subjects do you want to focus on?
   Examples: "Python, machine learning, data engineering" or "Snowflake, SQL optimization, dbt"
   ```

**⚠️ MANDATORY STOPPING POINT**: Present the collected profile back to the user for confirmation before proceeding.

```
Here's what I've captured so far:

- Name: [name]
- Learning Style: [style]
- Preferred Materials: [materials]
- Focus Areas: [focus]

Does this look correct? (Yes / Edit)
```

**Next:** Proceed to Step 3.

---

### Step 3: Gamification Preferences

**Goal:** Determine if the learner wants gamified learning and which elements they prefer.

**Actions:**

1. **Ask** the user if they want to **gamify** their learning (single select):

   | Option | Description |
   |--------|-------------|
   | Yes | Add game-like elements to make learning more engaging and trackable |
   | No | Keep learning straightforward without gamification mechanics |

2. **If Yes**, ask which **gamification elements** they want (multi-select):

   | Element | Description |
   |---------|-------------|
   | Points | Earn points for completing lessons, exercises, and milestones |
   | Badges | Unlock achievement badges for mastering topics and streaks |
   | Streaks | Track consecutive days of learning to build consistency |
   | Leaderboards | Compare progress with other learners for friendly competition |

   Store the selected elements as a comma-separated string (e.g., `"Points, Badges, Streaks"`).

3. **If No**, set `GAMIFICATION` to `FALSE` and `GAMIFICATION_PREFS` to `NULL`.

**Next:** Proceed to Step 4.

---

### Step 4: Generate AI Recommendations

**Goal:** Use Snowflake Cortex `AI_COMPLETE` to generate a personalized learning plan based on the full profile.

**Actions:**

1. **Construct** the prompt using the collected profile data:

   ```sql
   SELECT AI_COMPLETE(
        'claude-opus-4-6',
       CONCAT(
           'You are an expert learning coach. Based on the following learner profile, ',
           'create a personalized learning plan with specific, actionable recommendations.\n\n',
           'Learner Profile:\n',
           '- Name: ', '<learner_name>', '\n',
           '- Learning Style: ', '<learning_style>', '\n',
           '- Preferred Materials: ', '<preferred_materials>', '\n',
           '- Focus Areas: ', '<focus_areas>', '\n',
           '- Gamification Enabled: ', '<yes_or_no>', '\n',
           '<if gamification is enabled, add: - Gamification Preferences: <gamification_prefs>\n>',
           '\n',
           'Please provide:\n',
           '1. A structured weekly learning plan tailored to their style and materials\n',
           '2. Specific resource recommendations (types matching their preferred materials)\n',
           '3. Milestone checkpoints for tracking progress\n',
           '<if gamification enabled, add: 4. A gamification strategy using their chosen elements (how to earn points/badges/etc.)\n>',
           '4. Tips for maintaining motivation based on their learning style\n\n',
           'Keep the plan practical and immediately actionable.'
       )
   ) AS AI_RECOMMENDATIONS;
   ```

2. **Execute** the query and capture the AI-generated recommendations.

3. **Store** the recommendations text for use in Step 5.

**Next:** Proceed to Step 5.

---

### Step 5: Review & Approve

**Goal:** Present the complete profile and AI recommendations for user approval.

**Actions:**

1. **Present** the full profile summary:

   ```
   === Learner Profile Summary ===

   Name:               [name]
   Learning Style:     [style]
   Preferred Materials: [materials]
   Focus Areas:        [focus]
   Gamification:       [Yes/No]
   Gamification Prefs: [prefs or N/A]

   === AI-Generated Learning Plan ===

   [AI recommendations text]

   ================================
   ```

2. **⚠️ MANDATORY STOPPING POINT**: Ask the user to approve or modify:

   ```
   Would you like to:
   1. Save this profile as-is
   2. Regenerate the AI recommendations
   3. Edit profile details (go back to Step 2)
   4. Cancel without saving
   ```

   - **If 1:** Proceed to Step 6
   - **If 2:** Return to Step 4 to regenerate
   - **If 3:** Return to Step 2
   - **If 4:** End workflow without saving

**Next:** Proceed to Step 6.

---

### Step 6: Save to Snowflake

**Goal:** Persist the learner profile to the Snowflake table.

**Actions:**

1. **Insert** the profile into the table:

   ```sql
   INSERT INTO <DB>.<SCHEMA>.LEARNER_PROFILES (
       LEARNER_NAME,
       LEARNING_STYLE,
       PREFERRED_MATERIALS,
       FOCUS_AREAS,
       GAMIFICATION,
       GAMIFICATION_PREFS,
       AI_RECOMMENDATIONS
   ) VALUES (
       '<learner_name>',
       '<learning_style>',
       '<preferred_materials>',
       '<focus_areas>',
       <TRUE_or_FALSE>,
       '<gamification_prefs_or_NULL>',
       '<ai_recommendations_escaped>'
   );
   ```

   **IMPORTANT:** Properly escape single quotes in the AI recommendations text before inserting.

2. **Verify** the insert by querying the new row:

   ```sql
   SELECT PROFILE_ID, LEARNER_NAME, LEARNING_STYLE, CREATED_AT
   FROM <DB>.<SCHEMA>.LEARNER_PROFILES
   WHERE LEARNER_NAME = '<learner_name>'
   ORDER BY CREATED_AT DESC
   LIMIT 1;
   ```

3. **Present** confirmation to the user:

   ```
   Profile saved successfully!

   Profile ID: [id]
   Learner:    [name]
   Created:    [timestamp]

   Your personalized learning plan is stored and ready to reference.
   To view your profile later, run:
     SELECT * FROM <DB>.<SCHEMA>.LEARNER_PROFILES WHERE PROFILE_ID = [id];
   ```

**Output:** Profile persisted in Snowflake with AI-generated learning plan.

**Next:** Proceed to Step 7.

---

### Step 7: Generate Lesson Plan

**Goal:** Break the AI recommendations into structured, ordered lessons and persist them.

**Actions:**

1. **Use AI_COMPLETE** to decompose the AI recommendations into individual lessons:

   ```sql
   SELECT AI_COMPLETE(
       'claude-opus-4-6',
       CONCAT(
           'You are a curriculum designer. Given the following learning plan, break it into ',
           'individual numbered lessons. Each lesson should be a single focused topic.\n\n',
           'Learning Plan:\n', '<ai_recommendations_text>', '\n\n',
           'Learner preferences:\n',
           '- Learning Style: ', '<learning_style>', '\n',
           '- Preferred Materials: ', '<preferred_materials>', '\n\n',
           'For each lesson, output EXACTLY this format (one per line, pipe-delimited):\n',
           'LESSON_NUMBER|MONTH|TITLE|DESCRIPTION|LESSON_TYPE\n\n',
           'LESSON_TYPE must be one of: video, article, interactive_lab\n',
           'Choose LESSON_TYPE based on the learner''s preferred materials and what fits the topic.\n',
           'Generate 12-15 lessons covering the full 3-month plan.\n',
           'Output ONLY the pipe-delimited lines, no headers or other text.'
       )
   ) AS LESSON_BREAKDOWN;
   ```

2. **Parse** the AI output and insert each lesson into the LESSONS table.

3. **Insert** the lesson plan summary into LESSON_PLANS (one row per month):

   ```sql
   INSERT INTO <DB>.<SCHEMA>.LESSON_PLANS (PROFILE_ID, PLAN_NAME, MONTH, MONTH_THEME, WEEKLY_SCHEDULE, RESOURCES)
   VALUES (<profile_id>, '<plan_name>', <month>, '<month_theme>', '<weekly_schedule>', '<resources>');
   ```

4. **Insert** each lesson into the LESSONS table:

   ```sql
   INSERT INTO <DB>.<SCHEMA>.LESSONS (PROFILE_ID, PLAN_ID, LESSON_NUMBER, TITLE, DESCRIPTION, LESSON_TYPE)
   VALUES (<profile_id>, <plan_id>, <lesson_number>, '<title>', '<description>', '<lesson_type>');
   ```

5. **Initialize** the learner's progress record:

   ```sql
   INSERT INTO <DB>.<SCHEMA>.LEARNER_PROGRESS (PROFILE_ID, TOTAL_POINTS, CURRENT_STREAK, LONGEST_STREAK, CURRENT_LEVEL, LAST_ACTIVITY_DATE)
   VALUES (<profile_id>, 0, 0, 0, 'ML Apprentice', NULL);
   ```

6. **Present** the lesson plan to the user:

   ```
   Lesson plan created! Here's your learning path:

   Month 1: [theme]
     Lesson 1: [title] (interactive_lab)
     Lesson 2: [title] (video)
     ...

   Month 2: [theme]
     ...

   Month 3: [theme]
     ...

   Total: [N] lessons | Say "teach me" to start!
   ```

**Output:** Structured lesson plan saved to LESSON_PLANS and LESSONS tables.

---

### Step 8: Teach Mode (Ongoing)

**Trigger:** User says "teach me", "next lesson", or "start lesson".

**Goal:** Deliver the next lesson from the learner's plan, tailored to their profile.

**Actions:**

1. **Load** the learner's profile and find the next incomplete lesson:

   ```sql
   SELECT l.*, lp.PLAN_NAME, lp.MONTH_THEME,
          p.LEARNING_STYLE, p.PREFERRED_MATERIALS, p.GAMIFICATION, p.GAMIFICATION_PREFS
   FROM <DB>.<SCHEMA>.LESSONS l
   JOIN <DB>.<SCHEMA>.LESSON_PLANS lp ON l.PLAN_ID = lp.PLAN_ID
   JOIN <DB>.<SCHEMA>.LEARNER_PROFILES p ON l.PROFILE_ID = p.PROFILE_ID
   WHERE l.PROFILE_ID = <profile_id>
     AND l.STATUS != 'completed'
   ORDER BY l.LESSON_NUMBER ASC
   LIMIT 1;
   ```

2. **Mark** the lesson as in_progress:

   ```sql
   UPDATE <DB>.<SCHEMA>.LESSONS
   SET STATUS = 'in_progress', STARTED_AT = CURRENT_TIMESTAMP()
   WHERE LESSON_ID = <lesson_id>;
   ```

3. **Generate** the lesson content using AI_COMPLETE, incorporating:
   - The lesson title and description
   - The learner's style (visual → diagrams, charts; auditory → explain verbally; kinesthetic → hands-on code)
   - The lesson type (video → recommend specific videos; article → explain concepts; interactive_lab → create a Snowflake notebook)

4. **If lesson_type = 'interactive_lab':**
   - Create a Jupyter notebook with code cells, markdown explanations, and visual outputs
   - Upload to Snowflake workspace using `cortex artifact create notebook`
   - Store the notebook path in LESSONS.NOTEBOOK_PATH

5. **If lesson_type = 'video' or 'article':**
   - Present curated resource recommendations
   - Include a summary of key concepts with visual aids matching learning style
   - Provide practice exercises inline

6. **After lesson delivery, ask** the user to confirm completion.

7. **On completion**, update the lesson and progress:

   ```sql
   UPDATE <DB>.<SCHEMA>.LESSONS
   SET STATUS = 'completed', COMPLETED_AT = CURRENT_TIMESTAMP(), POINTS_EARNED = <points>
   WHERE LESSON_ID = <lesson_id>;
   ```

   ```sql
   UPDATE <DB>.<SCHEMA>.LEARNER_PROGRESS
   SET TOTAL_POINTS = TOTAL_POINTS + <points>,
       CURRENT_STREAK = CASE
           WHEN LAST_ACTIVITY_DATE = CURRENT_DATE() - 1 OR LAST_ACTIVITY_DATE IS NULL
           THEN CURRENT_STREAK + 1
           WHEN LAST_ACTIVITY_DATE = CURRENT_DATE() THEN CURRENT_STREAK
           ELSE 1
       END,
       LONGEST_STREAK = GREATEST(LONGEST_STREAK, CURRENT_STREAK + 1),
       CURRENT_LEVEL = CASE
           WHEN TOTAL_POINTS + <points> >= 10000 THEN 'ML Master'
           WHEN TOTAL_POINTS + <points> >= 5001 THEN 'ML Engineer'
           WHEN TOTAL_POINTS + <points> >= 1001 THEN 'ML Practitioner'
           ELSE 'ML Apprentice'
       END,
       LAST_ACTIVITY_DATE = CURRENT_DATE(),
       UPDATED_AT = CURRENT_TIMESTAMP()
   WHERE PROFILE_ID = <profile_id>;
   ```

8. **Present** a completion summary with gamification update:

   ```
   Lesson [N] complete! ✓

   Points earned:    +[points]
   Total points:     [total]
   Current streak:   [streak] days
   Level:            [level]

   Next up: Lesson [N+1] — [title]
   Say "next lesson" to continue or "my progress" for full dashboard.
   ```

---

### Step 9: Progress Dashboard (Ongoing)

**Trigger:** User says "my progress", "dashboard", "show my points", or "show my streak".

**Goal:** Display the learner's current progress across all dimensions.

**Actions:**

1. **Query** the learner's progress and lesson status:

   ```sql
   SELECT
       p.TOTAL_POINTS, p.CURRENT_STREAK, p.LONGEST_STREAK, p.CURRENT_LEVEL,
       COUNT(CASE WHEN l.STATUS = 'completed' THEN 1 END) AS LESSONS_COMPLETED,
       COUNT(CASE WHEN l.STATUS = 'in_progress' THEN 1 END) AS LESSONS_IN_PROGRESS,
       COUNT(CASE WHEN l.STATUS = 'not_started' THEN 1 END) AS LESSONS_REMAINING,
       COUNT(*) AS TOTAL_LESSONS,
       SUM(l.POINTS_EARNED) AS POINTS_FROM_LESSONS
   FROM <DB>.<SCHEMA>.LEARNER_PROGRESS p
   JOIN <DB>.<SCHEMA>.LESSONS l ON p.PROFILE_ID = l.PROFILE_ID
   WHERE p.PROFILE_ID = <profile_id>
   GROUP BY p.TOTAL_POINTS, p.CURRENT_STREAK, p.LONGEST_STREAK, p.CURRENT_LEVEL;
   ```

2. **Query** the lesson-by-lesson breakdown:

   ```sql
   SELECT LESSON_NUMBER, TITLE, LESSON_TYPE, STATUS, POINTS_EARNED, COMPLETED_AT
   FROM <DB>.<SCHEMA>.LESSONS
   WHERE PROFILE_ID = <profile_id>
   ORDER BY LESSON_NUMBER;
   ```

3. **Present** the dashboard:

   ```
   === Learning Dashboard: [name] ===

   Level:           [level]
   Total Points:    [points] / [next_level_threshold]
   Current Streak:  [streak] days
   Longest Streak:  [longest] days

   Progress: [completed]/[total] lessons ([percentage]%)
   ██████████░░░░░░░░░░ 50%

   Lessons:
   ✓ 1. [title] (interactive_lab) — 350 pts
   ► 2. [title] (video) — in progress
   ○ 3. [title] (article) — not started
   ...

   Month 1: [theme] — [X/Y complete]
   Month 2: [theme] — [X/Y complete]
   Month 3: [theme] — [X/Y complete]

   Say "next lesson" to continue learning!
   ```

---

## Stopping Points

- ✋ After Step 2: Confirm profile details before proceeding
- ✋ After Step 5: Approve final profile and recommendations before saving
- ✋ After Step 7: Review generated lesson plan before teaching begins
- ✋ After each lesson in Step 8: Confirm completion before awarding points

**Resume rule:** Upon user approval, proceed directly to the next step without re-asking.

## Output

A complete learner profile stored in `<DB>.<SCHEMA>.LEARNER_PROFILES` containing:
- Learning style, preferred materials, and focus areas
- Gamification preferences (if enabled)
- AI-generated personalized learning plan and recommendations

A structured lesson plan in `<DB>.<SCHEMA>.LESSON_PLANS` and `<DB>.<SCHEMA>.LESSONS` containing:
- Individual lessons broken out from the AI plan, ordered by month
- Lesson type matched to learner's preferred materials
- Completion status, points earned, and notebook paths

Progress tracking in `<DB>.<SCHEMA>.LEARNER_PROGRESS` containing:
- Total points, current/longest streak, current level
- Updated automatically as lessons are completed
