---
name: ml_recommendations
description: >
  ML-powered movie and TV show recommendations based on your Plex viewing history.
  Automatically imports your watch history, trains a machine learning model on your
  preferences, and provides personalized recommendations. Use this skill when the
  user wants personalized content suggestions, viewing history analysis, or to set
  up automated recommendations.
tags:
  - plex
  - recommendations
  - ml
  - machine-learning
  - personalization
  - viewing-history
tools:
  - auto_train_from_plex
  - import_plex_history
  - train_recommender
  - record_viewing
  - recommend_content
  - get_recommender_stats
  - reset_recommender
---

# ML Recommendations Skill

Use this skill when the user asks for:

## Setup & Training
- "Set up movie recommendations based on my Plex history"
- "Train a recommendation model from my viewing history"
- "Auto-train from Plex"
- "Import my Plex watching history"
- "Use my watch history to train recommendations"

## Getting Recommendations
- "What should I watch tonight?"
- "Recommend something based on what I like"
- "Which of these movies should I watch?"
- "Rank these shows for me"
- "What will I enjoy most from this list?"

## Recording Views
- "Record that I watched [movie name]"
- "I finished watching [show]"
- "I abandoned [movie] halfway through"
- "Add this to my viewing history"

## Stats & Monitoring
- "Show my recommendation stats"
- "How many movies have I recorded?"
- "Is my model trained?"
- "What's my viewing history like?"

## Typical Workflow

1. **One-time setup** (easiest):
   ```
   User: "Auto-train my recommendation model from Plex"
   → Calls: auto_train_from_plex(50)
   → Imports last 50 watched items
   → Trains ML model automatically
   → Ready to use!
   ```

2. **Manual setup**:
   ```
   User: "Import my Plex viewing history"
   → Calls: import_plex_history(50)
   
   User: "Train the recommendation model"
   → Calls: train_recommender()
   ```

3. **Get recommendations**:
   ```
   User: "I have Dune, Knives Out, and The Northman available. Which should I watch?"
   → Calls: recommend_content([
       {title: "Dune", genre: "SciFi", year: 2021, rating: 8.0, runtime: 155},
       {title: "Knives Out", genre: "Mystery", year: 2019, rating: 7.9, runtime: 130},
       {title: "The Northman", genre: "Drama", year: 2022, rating: 7.0, runtime: 137}
     ])
   → Returns ranked list with ML scores
   ```

## How It Works

The ML recommender:
1. **Learns from your behavior**: Analyzes which movies/shows you finish vs. abandon
2. **Identifies patterns**: Discovers your preferences for genres, runtimes, ratings, eras
3. **Predicts enjoyment**: Ranks new content by probability you'll finish watching it
4. **Gets smarter over time**: Improves as you watch more content

## Required Data

- **Minimum**: 20 viewing events to train
- **Optimal**: 50+ viewing events for better accuracy
- Each event includes: title, genre, year, rating, runtime, finished/abandoned

## Tool Reference

### auto_train_from_plex(import_limit)
One-click setup: imports Plex history + trains model automatically
- **When to use**: User wants instant setup with no manual steps
- **Example**: "Auto-train my recommendations from Plex"

### import_plex_history(limit)
Import viewing history from Plex (without training)
- **When to use**: User wants to review data before training
- **Example**: "Import my last 50 watched items"

### train_recommender()
Train the ML model on recorded viewing history
- **When to use**: After importing or manually recording 20+ items
- **Example**: "Train my recommendation model"

### record_viewing(title, genre, year, rating, runtime, finished)
Manually record a single viewing event
- **When to use**: User wants to add specific movies not in Plex
- **Example**: "Record that I watched The Matrix"

### recommend_content(available_items)
Rank a list of movies/shows by predicted enjoyment
- **When to use**: User has specific options and wants recommendations
- **Example**: "Which of these should I watch?"
- **Note**: Requires trained model

### get_recommender_stats()
View recommendation system statistics
- **When to use**: User wants to check model status or history
- **Example**: "Show my recommender stats"

### reset_recommender()
Clear all data and start fresh
- **When to use**: User wants to rebuild from scratch
- **Example**: "Reset my recommendation data"

## Common Patterns

**Pattern**: User asks "what should I watch?"
→ First check if model is trained (get_recommender_stats)
→ If not trained: auto_train_from_plex()
→ If trained: ask for specific options to rank

**Pattern**: User provides movie list
→ Extract movie details (title, genre, year, rating, runtime)
→ Call recommend_content() with formatted data
→ Return ranked list with explanations

**Pattern**: User mentions watching something
→ Extract movie details
→ Call record_viewing() with finished=True
→ Suggest training if approaching 20 items

## Error Handling

- **"No trained model"**: Guide user to run auto_train_from_plex()
- **"Not enough data"**: Tell user how many more views needed (20 minimum)
- **"Tool not found"**: Verify Plex server is running with ML tools enabled

## Example Interactions

```
User: "Set up movie recommendations for me"
Assistant: I'll import your Plex viewing history and train a model.
→ auto_train_from_plex(50)
Response: "Imported 47 items, trained model with 85% accuracy. Ready!"

User: "What should I watch: Dune or The Northman?"
Assistant: Let me rank those for you.
→ recommend_content([{Dune details}, {Northman details}])
Response: "Based on your preferences: 
1. Dune (88% match) - You tend to finish SciFi films
2. The Northman (42% match) - You often abandon slow dramas"

User: "I watched Inception and loved it"
Assistant: I'll record that.
→ record_viewing("Inception", "SciFi", 2010, 8.8, 148, True)
Response: "Recorded! Total views: 48. Model accuracy improving."
```

## Notes

- Model learns YOUR unique preferences (not generic ratings)
- "Finished" means you watched most/all of it
- "Abandoned" means you stopped watching early
- Requires at least 20 viewing events for initial training
- More data = better recommendations
- Model automatically saves and persists between sessions