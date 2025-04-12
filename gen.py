from html.parser import HTMLParser
from urllib.request import urlopen, Request
import re
from datetime import datetime
import urllib.request
import time

profile_url = "https://roadmap.sh/u/kiberam"

class ProfileParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skills = {}
        self.projects = {}
        self.current_section = None
        self.current_skill = None
        self.current_percent = None
        self.current_project = None
        self.current_likes = None
        self.in_skill_anchor = False
        self.in_project_anchor = False
        self.in_project_likes = False
        self.skill_content = []  # Accumulate content within skill anchor

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        
        if tag == 'h2':
            self.current_section = None
        
        if tag == 'a' and 'href' in attrs:
            href = attrs['href']
            if self.current_section == 'skills' and '?s=' in href:
                self.in_skill_anchor = True
                self.skill_content = []  # Reset for new skill
            elif self.current_section == 'projects' and '/projects/' in href:
                self.in_project_anchor = True
                self.current_project = href.split('/projects/')[-1]
        
        if self.in_project_anchor and tag == 'span':
            self.in_project_likes = True

    def handle_data(self, data):
        data = data.strip()
        if not data:
            return
        
        if not self.current_section:
            if "Skills I have mastered" in data:
                self.current_section = 'skills'
            elif "Projects I have worked on" in data:
                self.current_section = 'projects'
        
        if self.in_skill_anchor:
            self.skill_content.append(data)
            # Check if we've accumulated a percentage
            full_content = ''.join(self.skill_content)
            if '%' in full_content:
                # Extract name (before last numeric part) and percent
                parts = [x for x in self.skill_content if x and not x.startswith('<!--')]
                if len(parts) >= 2:
                    self.current_skill = parts[0]  # First content is name
                    percent_str = re.sub(r'[^\d]', '', full_content)  # Extract digits from full content
                    if percent_str:
                        self.current_percent = int(percent_str)
        
        elif self.in_project_anchor and self.in_project_likes and data.isdigit():
            self.current_likes = int(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.in_skill_anchor:
            if self.current_skill and self.current_percent is not None:
                self.skills[self.current_skill] = self.current_percent
            self.reset_skill_state()
        
        if tag == 'a' and self.in_project_anchor:
            if self.current_project and self.current_likes is not None:
                self.projects[self.current_project] = self.current_likes
            self.reset_project_state()
        
        if tag == 'span':
            self.in_project_likes = False

    def reset_skill_state(self):
        self.in_skill_anchor = False
        self.current_skill = None
        self.current_percent = None
        self.skill_content = []

    def reset_project_state(self):
        self.in_project_anchor = False
        self.current_project = None
        self.current_likes = None
        
def fetch_logo(skill, max_retries=3, delay=2):
    """Check if logo exists on SimpleIcons, fallback to gnubash"""
    simple_icon_url = f"https://simpleicons.org/icons/{skill.lower()}.svg"
    
    # Create request with proper headers
    req = urllib.request.Request(
        simple_icon_url,
        headers={'User-Agent': 'Mozilla/5.0 (compatible; SkillBadgeGenerator/1.0)'}
    )
    
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    return skill
                raise Exception("Unexpected status code")
        except urllib.error.HTTPError as e:
            if e.code == 404:  
                return "gnubash"
            # Other HTTP errors might be temporary, so retry
            if attempt == max_retries - 1:
                return "gnubash"
            time.sleep(delay)
        except (urllib.error.URLError, Exception):
            if attempt == max_retries - 1:
                return "gnubash"
            time.sleep(delay)

def get_color(percent):
    """Return color based on percentage"""
    if percent >= 80: return "brightgreen"
    elif percent >= 60: return "green"
    elif percent >= 40: return "yellow"
    return "red"

def generate_markdown(skills, projects):
    output = []
    
    output.append("## Hi there 👋\n")
    
    # Header with badges
    output.append("""
<div align="center">

# My Developer Profile
[![Roadmap.sh](https://img.shields.io/badge/Profile%20Data%20Source-roadmap.sh-blue?style=flat&logo=icloud)]({0})
![Updated](https://img.shields.io/static/v1?label=Updated&message={1}&color=green)
""".format(profile_url, datetime.now().strftime("%Y-%m-%d")))

    # Skills Section with Icons
    if skills:
        output.append("\n## 🛠️ Skills\n")
        output.append('<div align="center">\n')
        output.append('<table><tr><td valign="top" width="50%">\n\n')
        output.append("### Technical Proficiencies\n")
        
        for skill, percent in skills.items():
            icon = fetch_logo(skill.lower())
                
            filled = percent // 10
            empty = 10 - filled
            bar = "▰" * filled + "▱" * empty
            output.append(f" ![{skill}](https://img.shields.io/badge/{skill}-{percent}%25-{get_color(percent)}?style=flat&logo={icon})  `{bar}`\n")

        output.append('\n</td><td valign="top" width="50%">\n\n')
        output.append("### Skill Distribution\n")
        output.append('<img src="https://skillicons.dev/icons?i=bash,python,go,linux,docker" alt="Skill Icons"/>\n')
        output.append('<img src="https://skillicons.dev/icons?i=kubernetes,ansible,aws,githubactions" alt="Skill Icons"/>\n')
        output.append("\n</td></tr></table>")
        output.append("\n</div>\n")

    # Projects Section
    if projects:
        output.append("\n## 🚀 Projects\n")
        for project, likes in projects.items():
            pretty_name = ' '.join(word.capitalize() for word in project.split('-'))
            output.append(f"🔗 [{pretty_name}](https://roadmap.sh/projects/{project}) ({likes} 👍)\n")
    
    # Footer
    output.append("""
<div align="center">
<br/>
<i>Automatically generated from <a href="{0}">roadmap.sh profile</a></i>
</div>
""".format(profile_url))
   
    return '\n'.join(output)


    
def main():
    try:
        # Fetch the page
        req = Request(profile_url, 
                     headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req) as response:
            html_content = response.read().decode('utf-8')

        # Parse the HTML
        parser = ProfileParser()
        parser.feed(html_content)

        # Generate and print markdown
        markdown = generate_markdown(parser.skills, parser.projects)
        print(markdown)
        
        # Write to README.md
        with open('README.md', 'w') as f:
            f.write(markdown)
        print("\nSuccessfully updated README.md")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
