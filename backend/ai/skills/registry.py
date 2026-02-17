import os
import yaml
import logging
from typing import Dict, List, Optional
from backend.ai.skills.model import Skill

logger = logging.getLogger("QLM.AI.Skills")

class SkillRegistry:
    """
    Manages loading and retrieval of AI skills.
    Parses Markdown files with YAML frontmatter.
    """
    def __init__(self, skills_dir: str = "backend/ai/skills"):
        self.skills_dir = skills_dir
        self.skills: Dict[str, Skill] = {}
        self._load_skills()

    def _load_skills(self):
        self.skills.clear()
        if not os.path.exists(self.skills_dir):
            return

        for filename in os.listdir(self.skills_dir):
            if filename.endswith(".md"):
                try:
                    self._parse_skill_file(filename)
                except Exception as e:
                    logger.error(f"Failed to load skill {filename}: {e}")

    def _parse_skill_file(self, filename: str):
        path = os.path.join(self.skills_dir, filename)
        with open(path, "r") as f:
            content = f.read()

        # Split Frontmatter
        parts = content.split("---")
        if len(parts) >= 3:
            # YAML Exists
            yaml_content = parts[1]
            markdown_content = "---".join(parts[2:]).strip()

            meta = yaml.safe_load(yaml_content)
            skill_id = filename.replace(".md", "")

            skill = Skill(
                id=skill_id,
                name=meta.get("name", skill_id),
                description=meta.get("description", ""),
                tags=meta.get("tags", []),
                content=markdown_content
            )
            self.skills[skill_id] = skill
        else:
            # Legacy/Raw Markdown support
            skill_id = filename.replace(".md", "")
            self.skills[skill_id] = Skill(
                id=skill_id,
                name=skill_id,
                description="Legacy Skill",
                content=content
            )

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        return self.skills.get(skill_id)

    def list_skills(self) -> List[Skill]:
        return list(self.skills.values())

    def search_skills(self, query: str) -> List[Skill]:
        """
        Simple keyword search.
        """
        query = query.lower()
        results = []
        for s in self.skills.values():
            if query in s.name.lower() or query in s.description.lower() or query in s.content.lower():
                results.append(s)
            elif any(query in tag.lower() for tag in s.tags):
                results.append(s)
        return results

# Singleton
skill_registry = SkillRegistry()
