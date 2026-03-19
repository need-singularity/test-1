"""Fixed evaluation set for reasoning accuracy measurement."""

# Ground truth: questions with known answers
# Format: (subject, relation, expected_answer, difficulty, category)
EVAL_QUERIES = [
    # Level 1: Direct facts (IQ ~100)
    ("cat", "IsA", "mammal", 1, "biology"),
    ("dog", "IsA", "mammal", 1, "biology"),
    ("car", "IsA", "vehicle", 1, "transport"),
    ("gravity", "IsA", "force", 1, "physics"),
    ("atom", "HasA", "electron", 1, "chemistry"),
    ("red", "IsA", "color", 1, "general"),
    ("king", "IsA", "man", 1, "general"),
    ("doctor", "IsA", "profession", 1, "general"),
    ("cell", "HasA", "dna", 1, "biology"),
    ("molecule", "MadeOf", "atom", 1, "chemistry"),

    # Level 2: Indirect / multi-hop (IQ ~130)
    ("cat", "IsA", "animal", 2, "biology"),  # cat → mammal → animal
    ("dog", "IsA", "animal", 2, "biology"),  # dog → mammal → animal
    ("electron", "PartOf", "atom", 2, "chemistry"),  # reverse relation
    ("energy", "RelatedTo", "mass", 2, "physics"),
    ("supply", "RelatedTo", "market", 2, "economics"),

    # Level 3: Analogical (IQ ~160)
    # These test if the system can find structural similarity
    # We test by checking if find_analogy returns reasonable matches
]

# Ground truth analogies: (source, target_domain, expected_target_in_mapping)
EVAL_ANALOGIES = [
    ("gravity", "economics", "price"),      # force structure ≈ price structure
    ("force", "economics", "price"),        # same pattern
    ("atom", "biology", "cell"),            # fundamental unit in different domain
    ("energy", "economics", "capital"),     # conserved quantity
    ("mass", "economics", "supply"),        # inertial quantity
]

# Ground truth knowledge triples (injected into every test)
EVAL_KNOWLEDGE = [
    ("cat", "IsA", "mammal"), ("cat", "IsA", "animal"), ("cat", "HasA", "fur"),
    ("dog", "IsA", "mammal"), ("dog", "IsA", "animal"), ("dog", "HasA", "tail"),
    ("mammal", "IsA", "animal"), ("fish", "IsA", "animal"), ("bird", "IsA", "animal"),
    ("car", "IsA", "vehicle"), ("truck", "IsA", "vehicle"), ("bus", "IsA", "vehicle"),
    ("vehicle", "HasA", "wheels"), ("car", "HasA", "engine"),
    ("red", "IsA", "color"), ("blue", "IsA", "color"), ("green", "IsA", "color"),
    ("gravity", "IsA", "force"), ("mass", "RelatedTo", "gravity"),
    ("energy", "RelatedTo", "mass"), ("force", "RelatedTo", "mass"),
    ("price", "RelatedTo", "supply"), ("price", "RelatedTo", "demand"),
    ("supply", "RelatedTo", "market"), ("demand", "RelatedTo", "market"),
    ("atom", "HasA", "electron"), ("atom", "HasA", "proton"), ("atom", "HasA", "neutron"),
    ("molecule", "MadeOf", "atom"), ("cell", "HasA", "dna"),
    ("dna", "HasA", "gene"), ("protein", "MadeOf", "gene"),
    ("king", "IsA", "man"), ("queen", "IsA", "woman"),
    ("doctor", "IsA", "profession"), ("teacher", "IsA", "profession"),
    ("capital", "RelatedTo", "market"), ("capital", "RelatedTo", "investment"),
]
