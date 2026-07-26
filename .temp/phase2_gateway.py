path = r"G:\projects\ai数据隐私隔离\gateway_core.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add a tier-aware engine selection comment in the __init__ method
old_init = '''    def __init__(self) -> None:
        self.mask_engine = get_mask_engine()
        self.target_url = config.TARGET_LLM
        self.timeout = 120.0'''

new_init = '''    def __init__(self) -> None:
        self.mask_engine = get_mask_engine()
        self.target_url = config.TARGET_LLM
        self.timeout = 120.0
        # Tier-aware engine selection:
        # Enterprise tier uses AC automaton (Phase 4: rust_src/ac_matcher)
        # Pro/Lite use the standard regex-based engine.
        # if config.tier == "enterprise":
        #     from ac_engine import AcEngine
        #     self.ac_engine = AcEngine()
        # else:
        #     self.ac_engine = None'''

content = content.replace(old_init, new_init)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("gateway_core.py updated with tier-aware engine selection")
