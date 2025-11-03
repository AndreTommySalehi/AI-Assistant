import json
import os
from datetime import datetime


class ReflectionEngine:
    """
    Allows Jarvis to reflect on his responses and improve them
    - Checks factual accuracy
    - Evaluates tone/personality fit
    - Identifies when to use multi-step reasoning
    """
    
    def __init__(self, llm_handler, data_dir="./jarvis_data"):
        self.llm = llm_handler
        self.data_dir = data_dir
        self.reflection_log_file = os.path.join(data_dir, "reflections.json")
        self.reflections = self._load_reflections()
        
        # Settings
        self.enable_reflection = True
        self.reflection_threshold = 0.6  # Only reflect if confidence < 60%
        
    def _load_reflections(self):
        """Load past reflections"""
        if os.path.exists(self.reflection_log_file):
            try:
                with open(self.reflection_log_file, 'r') as f:
                    return json.load(f)
            except:
                return {"reflections": [], "improvements": 0}
        return {"reflections": [], "improvements": 0}
    
    def _save_reflections(self):
        """Save reflections to file"""
        with open(self.reflection_log_file, 'w') as f:
            json.dump(self.reflections, f, indent=2)
    
    def should_reflect(self, user_query, initial_response):
        """
        Determine if response needs reflection
        
        Reflect when:
        - Complex factual questions
        - Uncertain responses (contains "I'm not sure", "might be")
        - Technical/detailed queries
        """
        
        if not self.enable_reflection:
            return False
        
        response_lower = initial_response.lower()
        query_lower = user_query.lower()
        
        # Check for uncertainty markers
        uncertainty_phrases = [
            "i'm not sure", "i don't know", "unclear", "uncertain",
            "might be", "possibly", "perhaps", "maybe", "could be"
        ]
        
        has_uncertainty = any(phrase in response_lower for phrase in uncertainty_phrases)
        
        # Check for complex queries
        complex_indicators = [
            'why', 'how does', 'explain', 'compare', 'analyze',
            'what happens if', 'difference between', 'relationship between'
        ]
        
        is_complex = any(indicator in query_lower for indicator in complex_indicators)
        
        # Check if response is very short for a complex query
        is_too_brief = is_complex and len(initial_response.split()) < 30
        
        return has_uncertainty or is_too_brief
    
    def reflect_and_improve(self, user_query, initial_response, context=None):
        """
        Have Jarvis reflect on his response and potentially improve it
        
        Returns: (improved_response, was_improved, reflection_notes)
        """
        
        reflection_prompt = f"""You are reviewing your own response for quality and accuracy.

USER ASKED: {user_query}

YOUR INITIAL RESPONSE:
{initial_response}

{"CONTEXT AVAILABLE:\n" + context if context else ""}

SELF-CRITIQUE INSTRUCTIONS:
1. Is your response factually accurate? Any uncertainty?
2. Is it detailed enough for the question asked?
3. Does it directly answer what was asked?
4. Is the tone appropriate (professional, helpful)?
5. Could you provide more value with examples or explanations?

Provide your analysis as JSON:
{{
  "accuracy_score": 0.0-1.0,
  "completeness_score": 0.0-1.0,
  "issues_found": ["list", "of", "issues"],
  "needs_improvement": true/false,
  "improved_response": "your better response here (or null if original is fine)"
}}

Be honest - if your original response is good, say needs_improvement: false.
Only improve if there's a real issue.

JSON:"""
        
        try:
            critique = self.llm.generate(reflection_prompt, use_search_context=False)
            
            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', critique, re.DOTALL)
            
            if json_match:
                analysis = json.loads(json_match.group(0))
                
                needs_improvement = analysis.get('needs_improvement', False)
                improved = analysis.get('improved_response')
                
                # Log the reflection
                self.reflections["reflections"].append({
                    "timestamp": datetime.now().isoformat(),
                    "query": user_query,
                    "original_response": initial_response,
                    "analysis": analysis,
                    "was_improved": needs_improvement and improved is not None
                })
                
                if needs_improvement and improved:
                    self.reflections["improvements"] += 1
                    self._save_reflections()
                    
                    return (
                        improved,
                        True,
                        {
                            "accuracy": analysis.get('accuracy_score', 0),
                            "completeness": analysis.get('completeness_score', 0),
                            "issues": analysis.get('issues_found', [])
                        }
                    )
                else:
                    self._save_reflections()
                    return (initial_response, False, None)
            
        except Exception as e:
            print(f"[Reflection Error]: {e}")
            return (initial_response, False, None)
        
        # If reflection fails, return original
        return (initial_response, False, None)
    
    def chain_of_thought(self, user_query, context=None):
        """
        Use chain-of-thought reasoning for complex questions
        Breaks down problem into steps before answering
        """
        
        cot_prompt = f"""Complex question detected. Use step-by-step reasoning.

USER QUESTION: {user_query}

{"CONTEXT:\n" + context if context else ""}

THINK STEP BY STEP:

1. What is the user really asking?
2. What information do I need to answer this?
3. What's the logical approach to solve this?
4. What's my conclusion?

After your reasoning, provide:
FINAL ANSWER: [your complete answer here]

Begin thinking:"""
        
        try:
            reasoning = self.llm.generate(cot_prompt, use_search_context=False)
            
            # Extract final answer
            if "FINAL ANSWER:" in reasoning:
                final_answer = reasoning.split("FINAL ANSWER:")[1].strip()
                
                # Log that we used chain-of-thought
                self.reflections["reflections"].append({
                    "timestamp": datetime.now().isoformat(),
                    "query": user_query,
                    "method": "chain_of_thought",
                    "reasoning": reasoning,
                    "answer": final_answer
                })
                self._save_reflections()
                
                return final_answer
            else:
                return reasoning
                
        except Exception as e:
            print(f"[CoT Error]: {e}")
            return None
    
    def get_stats(self):
        """Get reflection statistics"""
        total_reflections = len(self.reflections.get("reflections", []))
        improvements = self.reflections.get("improvements", 0)
        
        return {
            "total_reflections": total_reflections,
            "improvements_made": improvements,
            "improvement_rate": improvements / total_reflections if total_reflections > 0 else 0,
            "enabled": self.enable_reflection
        }
    
    def toggle_reflection(self, enabled=None):
        """Turn reflection on/off"""
        if enabled is None:
            self.enable_reflection = not self.enable_reflection
        else:
            self.enable_reflection = enabled
        
        return self.enable_reflection


class MultiAgentDebate:
    """
    Multi-agent debate system - multiple LLMs argue to reach better answers
    Uses different "personas" to get diverse perspectives
    """
    
    def __init__(self, llm_handler):
        self.llm = llm_handler
        self.debate_log = []
        
        # Different agent personas
        self.agents = {
            "optimist": "You are optimistic and see possibilities. Focus on potential and opportunities.",
            "skeptic": "You are skeptical and critical. Point out flaws, risks, and uncertainties.",
            "analyst": "You are analytical and data-driven. Focus on facts, logic, and evidence.",
            "pragmatist": "You are practical and realistic. Focus on what's actionable and feasible."
        }
    
    def debate(self, user_query, rounds=2):
        """
        Run a multi-agent debate
        
        Process:
        1. Each agent gives their perspective
        2. Agents respond to each other
        3. Synthesize final answer from debate
        """
        
        debate_history = []
        
        # Round 1: Initial perspectives
        print("\n[Multi-Agent Debate Starting...]")
        
        for agent_name, agent_persona in self.agents.items():
            agent_prompt = f"""{agent_persona}

USER QUESTION: {user_query}

Give your perspective (2-3 sentences):"""
            
            try:
                perspective = self.llm.generate(agent_prompt, use_search_context=False)
                debate_history.append({
                    "agent": agent_name,
                    "round": 1,
                    "statement": perspective
                })
                print(f"  [{agent_name.upper()}]: {perspective[:100]}...")
            except Exception as e:
                print(f"  [{agent_name}] failed: {e}")
        
        # Round 2+: Agents respond to each other
        for round_num in range(2, rounds + 1):
            previous_statements = "\n\n".join([
                f"{h['agent'].upper()}: {h['statement']}"
                for h in debate_history if h['round'] == round_num - 1
            ])
            
            for agent_name, agent_persona in self.agents.items():
                response_prompt = f"""{agent_persona}

USER QUESTION: {user_query}

OTHER AGENTS SAID:
{previous_statements}

Your response to their points (2-3 sentences):"""
                
                try:
                    response = self.llm.generate(response_prompt, use_search_context=False)
                    debate_history.append({
                        "agent": agent_name,
                        "round": round_num,
                        "statement": response
                    })
                except Exception as e:
                    print(f"  [{agent_name}] round {round_num} failed: {e}")
        
        # Synthesize final answer
        all_perspectives = "\n\n".join([
            f"{h['agent'].upper()} (Round {h['round']}): {h['statement']}"
            for h in debate_history
        ])
        
        synthesis_prompt = f"""Multiple AI agents debated this question. Synthesize the best answer.

USER QUESTION: {user_query}

DEBATE TRANSCRIPT:
{all_perspectives}

Based on all perspectives, what's the most accurate and balanced answer?
Synthesize the strongest points from each agent.

FINAL ANSWER:"""
        
        try:
            final_answer = self.llm.generate(synthesis_prompt, use_search_context=False)
            
            # Log the debate
            self.debate_log.append({
                "timestamp": datetime.now().isoformat(),
                "query": user_query,
                "debate": debate_history,
                "final_answer": final_answer
            })
            
            print(f"\n[Debate concluded - synthesized answer generated]")
            
            return final_answer, debate_history
            
        except Exception as e:
            print(f"[Synthesis Error]: {e}")
            # Fall back to just combining perspectives
            return all_perspectives, debate_history
    
    def quick_debate(self, user_query, agent1="optimist", agent2="skeptic"):
        """
        Quick 2-agent debate for faster processing
        """
        
        # Agent 1's perspective
        perspective1 = self.llm.generate(
            f"{self.agents[agent1]}\n\nQUESTION: {user_query}\n\nYour view:",
            use_search_context=False
        )
        
        # Agent 2's counter-perspective
        perspective2 = self.llm.generate(
            f"{self.agents[agent2]}\n\nQUESTION: {user_query}\n\n{agent1.upper()} SAID: {perspective1}\n\nYour counter-view:",
            use_search_context=False
        )
        
        # Synthesize
        synthesis = self.llm.generate(
            f"Synthesize these perspectives:\n\n{agent1}: {perspective1}\n\n{agent2}: {perspective2}\n\nBalanced answer:",
            use_search_context=False
        )
        
        return synthesis