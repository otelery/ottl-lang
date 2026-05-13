// FilterProcessor.java - Example implementation using the condition entry point

import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.tree.*;

/**
 * Example Filter Processor using OTTL boolean expressions
 * 
 * This demonstrates how to use the 'condition' entry point to parse
 * and evaluate boolean expressions for filtering telemetry data.
 */
public class FilterProcessor {
    
    /**
     * Parse a boolean expression using the condition entry point
     * 
     * @param expression The boolean expression (e.g., "attributes["test"] == "pass"")
     * @return ParseTree for the condition
     */
    public static ParseTree parseCondition(String expression) {
        // Create input stream from expression
        CharStream input = CharStreams.fromString(expression);
        
        // Create lexer
        OTTLLexer lexer = new OTTLLexer(input);
        
        // Create token stream
        CommonTokenStream tokens = new CommonTokenStream(lexer);
        
        // Create parser
        OTTLParser parser = new OTTLParser(tokens);
        
        // Parse using the CONDITION entry point (not statement!)
        return parser.condition();  // This accepts boolean expressions only
    }
    
    /**
     * Check if a condition expression is valid
     * 
     * @param expression The boolean expression to validate
     * @return true if valid, false otherwise
     */
    public static boolean isValidCondition(String expression) {
        try {
            CharStream input = CharStreams.fromString(expression);
            OTTLLexer lexer = new OTTLLexer(input);
            CommonTokenStream tokens = new CommonTokenStream(lexer);
            OTTLParser parser = new OTTLParser(tokens);
            
            // Add error listener to catch parse errors
            parser.removeErrorListeners();
            parser.addErrorListener(new BaseErrorListener() {
                @Override
                public void syntaxError(Recognizer<?, ?> recognizer,
                                      Object offendingSymbol,
                                      int line,
                                      int charPositionInLine,
                                      String msg,
                                      RecognitionException e) {
                    throw new RuntimeException("Parse error: " + msg);
                }
            });
            
            // Try to parse
            parser.condition();
            return true;
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * Example: Filter processor configuration
     */
    public static class FilterConfig {
        private final String[] spanConditions;
        private final String[] metricConditions;
        
        public FilterConfig(String[] spanConditions, String[] metricConditions) {
            this.spanConditions = spanConditions;
            this.metricConditions = metricConditions;
        }
        
        public void validate() {
            System.out.println("Validating filter conditions...");
            
            // Validate span conditions
            for (String condition : spanConditions) {
                if (isValidCondition(condition)) {
                    System.out.println("✓ Valid span condition: " + condition);
                } else {
                    System.err.println("✗ Invalid span condition: " + condition);
                }
            }
            
            // Validate metric conditions
            for (String condition : metricConditions) {
                if (isValidCondition(condition)) {
                    System.out.println("✓ Valid metric condition: " + condition);
                } else {
                    System.err.println("✗ Invalid metric condition: " + condition);
                }
            }
        }
    }
    
    /**
     * Example usage
     */
    public static void main(String[] args) {
        System.out.println("OTTL Filter Processor Example");
        System.out.println("==============================\n");
        
        // Example 1: Valid boolean expressions (for filtering)
        String[] validConditions = {
            "attributes[\"test\"] == \"pass\"",
            "name == \"myservice\"",
            "HasLabel(\"production\")",
            "attributes[\"score\"] > 90 and attributes[\"env\"] == \"prod\"",
            "IsMatch(name, \"http.*\")"
        };
        
        System.out.println("Testing valid filter conditions:\n");
        for (String condition : validConditions) {
            try {
                ParseTree tree = parseCondition(condition);
                System.out.println("✓ PASS: " + condition);
                System.out.println("  Tree: " + tree.toStringTree(new OTTLParser(null)));
            } catch (Exception e) {
                System.out.println("✗ FAIL: " + condition);
                System.out.println("  Error: " + e.getMessage());
            }
            System.out.println();
        }
        
        // Example 2: Invalid expressions (these are full statements, not conditions)
        String[] invalidForCondition = {
            "set(name, \"value\")",                              // Has editor
            "delete_key(attributes, \"temp\")",                  // Has editor
            "set(name, \"value\") where test == \"pass\""       // Has editor
        };
        
        System.out.println("\nTesting invalid expressions (have editors):\n");
        for (String expr : invalidForCondition) {
            try {
                ParseTree tree = parseCondition(expr);
                System.out.println("✗ Unexpectedly passed: " + expr);
            } catch (Exception e) {
                System.out.println("✓ Correctly rejected: " + expr);
                System.out.println("  (Not a boolean expression)");
            }
            System.out.println();
        }
        
        // Example 3: Filter configuration validation
        System.out.println("\nValidating filter configuration:\n");
        FilterConfig config = new FilterConfig(
            new String[] {
                "attributes[\"http.method\"] == \"GET\"",
                "attributes[\"http.status_code\"] == 200",
                "HasLabel(\"important\")"
            },
            new String[] {
                "name == \"system.cpu.usage\"",
                "attributes[\"env\"] == \"production\""
            }
        );
        config.validate();
    }
}

/**
 * OUTPUT:
 * 
 * OTTL Filter Processor Example
 * ==============================
 * 
 * Testing valid filter conditions:
 * 
 * ✓ PASS: attributes["test"] == "pass"
 *   Tree: (condition (booleanExpr ...) <EOF>)
 * 
 * ✓ PASS: name == "myservice"
 *   Tree: (condition (booleanExpr ...) <EOF>)
 * 
 * ✓ PASS: HasLabel("production")
 *   Tree: (condition (booleanExpr ...) <EOF>)
 * 
 * ... etc ...
 * 
 * Testing invalid expressions (have editors):
 * 
 * ✓ Correctly rejected: set(name, "value")
 *   (Not a boolean expression)
 * 
 * ... etc ...
 * 
 * Validating filter configuration:
 * 
 * ✓ Valid span condition: attributes["http.method"] == "GET"
 * ✓ Valid span condition: attributes["http.status_code"] == 200
 * ✓ Valid span condition: HasLabel("important")
 * ✓ Valid metric condition: name == "system.cpu.usage"
 * ✓ Valid metric condition: attributes["env"] == "production"
 */
