import re

with open('src/generator.py', 'r') as f:
    content = f.read()

# Fix all mismatched brackets in random.choice patterns
# Pattern: random.choice(['...X'})  ->  random.choice(['...X'])
content = re.sub(r"random\.choice\(\['([^']+)'\)\}", r"random.choice(['\1'])}", content)

with open('src/generator.py', 'w') as f:
    f.write(content)

print("Fixed!")
