"""
DEMO: Real Symbolic AI in Action.
This script demonstrates the new engines working together.
"""
import sys
from metanucleus.core_unification import struct, sym, var
from metanucleus.phi_calculus import phi_calculus, CalculusResult
from metanucleus.phi_intent import phi_intent
from metanucleus.knowledge_graph import get_kb
from nsr.advanced_inference import create_standard_engine

def demo_math():
    print("\n--- 1. Testing New Calculus Engine (PEMDAS) ---")
    expr = "1 + 2 * 3"
    print(f"Input: '{expr}'")
    # We simulate the parse object
    class MockParse:
        text = expr
    
    result = phi_calculus(MockParse)
    print(f"Normalized: {result.expression_normalized}")
    print(f"Result: {result.result}")
    print(f"Correct? {result.result == 7.0} (Expected 7.0, Old AI would say 9.0)")
    for step in result.steps:
        print(f"  step: {step}")

def demo_logic():
    print("\n--- 2. Testing Real Inference Engine (Forward Chaining) ---")
    engine = create_standard_engine()
    
    # Symbols
    rain = sym("rain")
    wet = sym("wet_floor")
    slip = sym("slippery")
    
    # Facts: Rain causes Wet Floor. Wet Floor causes Slippery.
    f1 = struct("causes", rain, wet)
    f2 = struct("causes", wet, slip)
    
    print("Adding Facts:")
    print(f"  1. {f1}")
    print(f"  2. {f2}")
    
    engine.add_fact(f1)
    engine.add_fact(f2)
    
    print("\nRunning Inference (Deriving Transitive Causality)...")
    derivations = engine.run_until_fixpoint()
    
    for d in derivations:
        print(f"  [LOGIC] {d}")
        
    # Verify if it derived 'causes(rain, slippery)'
    expected = struct("causes", rain, slip)
    has_derived = any(str(f) == str(expected) for f in engine.facts)
    print(f"\nSuccess? {has_derived}")
    if has_derived:
        print("  >> The AI successfully reasoned that Rain causes Slippery!")

def demo_intent():
    print("\n--- 3. Testing Symbolic Pattern Matching ---")
    # Mock parse for "define apple"
    class MockParse1:
        text = "define apple"
        tokens = [type('T',(),{'lower':'define'}), type('T',(),{'lower':'apple'})]
    
    result = phi_intent(MockParse1)
    print(f"Input: 'define apple'")
    print(f"Intent: {result.label}")
    print(f"Variables Extracted: {result.variables}")
    
    if result.variables.get('target') == 'apple':
        print("  >> Successfully bound 'apple' to variable ?target")

def main():
    print("=== METANUCLEUS REBORN: SYMBOLIC AI DEMO ===")
    demo_math()
    demo_logic()
    demo_intent()
    print("\n=== DEMO COMPLETE ===")

if __name__ == "__main__":
    main()
