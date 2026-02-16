"""
Checkpoint 3 — Identity context loads cleanly
"""
from core.identity import load_identity_context, build_system_prompt_block

ctx = load_identity_context()
print("=== TECHNICAL MODE ===")
print(build_system_prompt_block(ctx, "technical"))
print("\n" + "="*50 + "\n")
print("=== NON-TECHNICAL MODE ===")
print(build_system_prompt_block(ctx, "nontechnical"))
print("\n✅ Identity context loaded and system prompts generated successfully")
