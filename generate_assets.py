import os

def create_svg(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)

base_dir = r"c:\Users\Admin\Downloads\third-eye\third-eye\static\assets"

# Faces
face1 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 250">
    <path d="M40,100 C40,20 160,20 160,100 C160,180 140,240 100,240 C60,240 40,180 40,100 Z" fill="none" stroke="#333" stroke-width="2" stroke-dasharray="2 1"/>
</svg>'''
face2 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 250">
    <path d="M30,90 C30,10 170,10 170,90 C170,190 130,230 100,230 C70,230 30,190 30,90 Z" fill="none" stroke="#333" stroke-width="2" stroke-dasharray="3 1"/>
</svg>'''
face3 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 250">
    <path d="M50,110 C50,30 150,30 150,110 C150,170 120,220 100,220 C80,220 50,170 50,110 Z" fill="none" stroke="#333" stroke-width="2" stroke-dasharray="1 2"/>
</svg>'''

# Lips
lip1 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40">
    <path d="M10,20 Q50,10 90,20 Q50,30 10,20" fill="none" stroke="#333" stroke-width="1.5" stroke-dasharray="2 1"/>
    <path d="M10,20 Q50,20 90,20" fill="none" stroke="#333" stroke-width="1" stroke-dasharray="1 1"/>
</svg>'''
lip2 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40">
    <path d="M15,20 Q50,5 85,20 Q50,35 15,20" fill="none" stroke="#333" stroke-width="2" stroke-dasharray="3 1"/>
    <path d="M15,20 Q50,22 85,20" fill="none" stroke="#333" stroke-width="1"/>
</svg>'''
lip3 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40">
    <path d="M5,20 Q50,15 95,20 Q50,25 5,20" fill="none" stroke="#333" stroke-width="1.5" stroke-dasharray="4 2"/>
    <path d="M5,20 Q50,20 95,20" fill="none" stroke="#333" stroke-width="0.5"/>
</svg>'''

# Eyes (pair)
eye1 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 150 40">
    <!-- Left Eye -->
    <path d="M10,20 Q30,10 50,20 Q30,30 10,20" fill="none" stroke="#333" stroke-width="1.5" stroke-dasharray="2 1"/>
    <circle cx="30" cy="20" r="5" fill="#555"/>
    <circle cx="30" cy="20" r="2" fill="#222"/>
    <!-- Right Eye -->
    <path d="M100,20 Q120,10 140,20 Q120,30 100,20" fill="none" stroke="#333" stroke-width="1.5" stroke-dasharray="2 1"/>
    <circle cx="120" cy="20" r="5" fill="#555"/>
    <circle cx="120" cy="20" r="2" fill="#222"/>
</svg>'''

eye2 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 150 40">
    <!-- Left Eye -->
    <path d="M15,20 Q30,5 45,20 Q30,30 15,20" fill="none" stroke="#333" stroke-width="1.5" stroke-dasharray="3 1"/>
    <circle cx="30" cy="18" r="6" fill="#444"/>
    <circle cx="30" cy="18" r="2" fill="#111"/>
    <!-- Right Eye -->
    <path d="M105,20 Q120,5 135,20 Q120,30 105,20" fill="none" stroke="#333" stroke-width="1.5" stroke-dasharray="3 1"/>
    <circle cx="120" cy="18" r="6" fill="#444"/>
    <circle cx="120" cy="18" r="2" fill="#111"/>
</svg>'''

eye3 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 150 40">
    <!-- Left Eye -->
    <path d="M5,20 Q30,15 55,20 Q30,25 5,20" fill="none" stroke="#333" stroke-width="1.5" stroke-dasharray="1 1"/>
    <circle cx="30" cy="20" r="4" fill="#666"/>
    <!-- Right Eye -->
    <path d="M95,20 Q120,15 145,20 Q120,25 95,20" fill="none" stroke="#333" stroke-width="1.5" stroke-dasharray="1 1"/>
    <circle cx="120" cy="20" r="4" fill="#666"/>
</svg>'''

# Noses
nose1 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 80">
    <path d="M30,10 L30,60" fill="none" stroke="#333" stroke-width="1.5" stroke-dasharray="2 2"/>
    <path d="M20,60 Q30,70 40,60" fill="none" stroke="#333" stroke-width="1.5" stroke-dasharray="2 2"/>
    <path d="M15,55 Q20,50 20,60" fill="none" stroke="#333" stroke-width="1"/>
    <path d="M45,55 Q40,50 40,60" fill="none" stroke="#333" stroke-width="1"/>
</svg>'''
nose2 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 80">
    <path d="M30,5 L30,55" fill="none" stroke="#333" stroke-width="2" stroke-dasharray="3 1"/>
    <path d="M15,65 Q30,75 45,65" fill="none" stroke="#333" stroke-width="2" stroke-dasharray="3 1"/>
    <path d="M15,55 Q20,60 15,65" fill="none" stroke="#333" stroke-width="1"/>
    <path d="M45,55 Q40,60 45,65" fill="none" stroke="#333" stroke-width="1"/>
</svg>'''
nose3 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 80">
    <path d="M25,20 L25,60" fill="none" stroke="#333" stroke-width="1" stroke-dasharray="1 2"/>
    <path d="M35,20 L35,60" fill="none" stroke="#333" stroke-width="1" stroke-dasharray="1 2"/>
    <path d="M25,60 Q30,65 35,60" fill="none" stroke="#333" stroke-width="1.5"/>
</svg>'''

# Hair
hair1 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 150">
    <path d="M30,100 C20,10 180,10 170,100 C150,50 50,50 30,100 Z" fill="#444" stroke="#222" stroke-width="2"/>
    <path d="M50,80 C80,30 120,30 150,80" fill="none" stroke="#222" stroke-width="1" stroke-dasharray="2 1"/>
</svg>'''
hair2 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 150">
    <path d="M20,120 C10,50 100,5 190,50 C180,100 190,130 190,130 C150,80 50,80 20,120 Z" fill="#555" stroke="#333" stroke-width="2"/>
</svg>'''
hair3 = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 150">
    <path d="M40,90 Q100,20 160,90 Q100,60 40,90 Z" fill="#333"/>
    <path d="M50,90 Q100,40 150,90" fill="none" stroke="#111" stroke-width="2"/>
</svg>'''

create_svg(os.path.join(base_dir, "faces", "face1.svg"), face1)
create_svg(os.path.join(base_dir, "faces", "face2.svg"), face2)
create_svg(os.path.join(base_dir, "faces", "face3.svg"), face3)

create_svg(os.path.join(base_dir, "lips", "lip1.svg"), lip1)
create_svg(os.path.join(base_dir, "lips", "lip2.svg"), lip2)
create_svg(os.path.join(base_dir, "lips", "lip3.svg"), lip3)

create_svg(os.path.join(base_dir, "eyes", "eye1.svg"), eye1)
create_svg(os.path.join(base_dir, "eyes", "eye2.svg"), eye2)
create_svg(os.path.join(base_dir, "eyes", "eye3.svg"), eye3)

create_svg(os.path.join(base_dir, "noses", "nose1.svg"), nose1)
create_svg(os.path.join(base_dir, "noses", "nose2.svg"), nose2)
create_svg(os.path.join(base_dir, "noses", "nose3.svg"), nose3)

create_svg(os.path.join(base_dir, "hair", "hair1.svg"), hair1)
create_svg(os.path.join(base_dir, "hair", "hair2.svg"), hair2)
create_svg(os.path.join(base_dir, "hair", "hair3.svg"), hair3)

print("Assets created successfully.")
