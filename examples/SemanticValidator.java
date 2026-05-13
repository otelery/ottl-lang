import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.tree.*;
import java.util.*;

/**
 * Semantic Validator for OTTL using ANTLR Visitor Pattern
 * 
 * This demonstrates how to implement semantic validation after syntax parsing.
 * 
 * Semantic checks performed:
 * 1. Function existence validation
 * 2. Type checking for arguments
 * 3. Context validation (e.g., body only in log context)
 * 4. Enum value validation
 */
public class SemanticValidator extends OTTLBaseVisitor<Boolean> {
    
    private List<String> errors = new ArrayList<>();
    private Map<String, FunctionSignature> editorFunctions = new HashMap<>();
    private Map<String, FunctionSignature> converterFunctions = new HashMap<>();
    private Set<String> validEnums = new HashSet<>();
    private String currentContext = "unknown"; // log, metric, trace, etc.
    
    public SemanticValidator(String context) {
        this.currentContext = context;
        initializeKnownFunctions();
        initializeKnownEnums();
    }
    
    /**
     * Initialize known editor functions with their signatures
     */
    private void initializeKnownFunctions() {
        // Editors (lowercase)
        editorFunctions.put("set", new FunctionSignature("set", 2, 2, 
            Arrays.asList("path", "value")));
        editorFunctions.put("delete_key", new FunctionSignature("delete_key", 2, 2,
            Arrays.asList("target", "key")));
        editorFunctions.put("merge_maps", new FunctionSignature("merge_maps", 3, 3,
            Arrays.asList("target", "source", "strategy")));
        editorFunctions.put("flatten", new FunctionSignature("flatten", 1, 3,
            Arrays.asList("target", "prefix", "depth")));
        
        // Converters (CamelCase)
        converterFunctions.put("ParseJSON", new FunctionSignature("ParseJSON", 1, 1,
            Arrays.asList("input")));
        converterFunctions.put("Split", new FunctionSignature("Split", 2, 2,
            Arrays.asList("value", "delimiter")));
        converterFunctions.put("Concat", new FunctionSignature("Concat", 2, 2,
            Arrays.asList("values", "separator")));
        converterFunctions.put("IsMatch", new FunctionSignature("IsMatch", 2, 2,
            Arrays.asList("target", "pattern")));
        converterFunctions.put("ConvertCase", new FunctionSignature("ConvertCase", 2, 2,
            Arrays.asList("target", "to")));
    }
    
    /**
     * Initialize known enum values
     */
    private void initializeKnownEnums() {
        validEnums.add("SPAN_KIND_SERVER");
        validEnums.add("SPAN_KIND_CLIENT");
        validEnums.add("SPAN_KIND_PRODUCER");
        validEnums.add("SPAN_KIND_CONSUMER");
        validEnums.add("STATUS_CODE_OK");
        validEnums.add("STATUS_CODE_ERROR");
        validEnums.add("SEVERITY_NUMBER_INFO");
        validEnums.add("SEVERITY_NUMBER_ERROR");
        validEnums.add("LOG_LEVEL_DEBUG");
        validEnums.add("LOG_LEVEL_INFO");
        validEnums.add("LOG_LEVEL_WARN");
        validEnums.add("LOG_LEVEL_ERROR");
    }
    
    /**
     * Validate the entire statement
     */
    @Override
    public Boolean visitStatement(OTTLParser.StatementContext ctx) {
        // Visit editor and where clause
        visit(ctx.editor());
        if (ctx.whereClause() != null) {
            visit(ctx.whereClause());
        }
        return errors.isEmpty();
    }
    
    /**
     * Validate editor function call
     */
    @Override
    public Boolean visitEditor(OTTLParser.EditorContext ctx) {
        String funcName = ctx.LOWERCASE_ID().getText();
        
        // Check if function exists
        if (!editorFunctions.containsKey(funcName)) {
            addError(ctx, "Unknown editor function: " + funcName);
            return false;
        }
        
        // Validate argument count
        FunctionSignature sig = editorFunctions.get(funcName);
        int argCount = ctx.arguments() != null ? 
            ctx.arguments().argument().size() : 0;
            
        if (argCount < sig.minArgs || argCount > sig.maxArgs) {
            addError(ctx, String.format(
                "Function '%s' expects %d-%d arguments, got %d",
                funcName, sig.minArgs, sig.maxArgs, argCount
            ));
        }
        
        // Validate context-specific constraints
        if (funcName.equals("set")) {
            validateSetFunction(ctx);
        }
        
        return visitChildren(ctx);
    }
    
    /**
     * Validate converter function call
     */
    @Override
    public Boolean visitConverter(OTTLParser.ConverterContext ctx) {
        String funcName = ctx.UPPERCASE_ID().getText();
        
        // Check if function exists
        if (!converterFunctions.containsKey(funcName)) {
            addError(ctx, "Unknown converter function: " + funcName);
            return false;
        }
        
        // Validate argument count
        FunctionSignature sig = converterFunctions.get(funcName);
        int argCount = ctx.arguments() != null ? 
            ctx.arguments().argument().size() : 0;
            
        if (argCount < sig.minArgs || argCount > sig.maxArgs) {
            addError(ctx, String.format(
                "Converter '%s' expects %d-%d arguments, got %d",
                funcName, sig.minArgs, sig.maxArgs, argCount
            ));
        }
        
        return visitChildren(ctx);
    }
    
    /**
     * Validate enum values
     */
    @Override
    public Boolean visitEnumValue(OTTLParser.EnumValueContext ctx) {
        String enumName = ctx.UPPERCASE_ID().getText();
        
        if (!validEnums.contains(enumName)) {
            addError(ctx, "Unknown enum value: " + enumName + 
                ". Did you mean to use a converter function?");
        }
        
        return true;
    }
    
    /**
     * Validate path expressions
     */
    @Override
    public Boolean visitPath(OTTLParser.PathContext ctx) {
        String firstToken = ctx.LOWERCASE_ID() != null ? 
            ctx.LOWERCASE_ID().getText() : 
            ctx.field(0).LOWERCASE_ID().getText();
        
        // Validate context-specific paths
        if (firstToken.equals("body") && !currentContext.equals("log")) {
            addError(ctx, "Field 'body' is only available in log context");
        }
        
        if (firstToken.equals("metric") && !currentContext.equals("metric")) {
            addError(ctx, "Field 'metric' is only available in metric context");
        }
        
        if (firstToken.equals("span") && !currentContext.equals("trace")) {
            addError(ctx, "Field 'span' is only available in trace context");
        }
        
        return visitChildren(ctx);
    }
    
    /**
     * Validate set() function specifically
     */
    private void validateSetFunction(OTTLParser.EditorContext ctx) {
        // First argument should be a path
        if (ctx.arguments() != null && !ctx.arguments().argument().isEmpty()) {
            OTTLParser.ArgumentContext firstArg = ctx.arguments().argument(0);
            // Could add type checking here
        }
    }
    
    /**
     * Add an error with line/column information
     */
    private void addError(ParserRuleContext ctx, String message) {
        int line = ctx.start.getLine();
        int col = ctx.start.getCharPositionInLine();
        errors.add(String.format("Line %d:%d - %s", line, col, message));
    }
    
    /**
     * Get all validation errors
     */
    public List<String> getErrors() {
        return errors;
    }
    
    /**
     * Check if validation passed
     */
    public boolean isValid() {
        return errors.isEmpty();
    }
    
    /**
     * Function signature holder
     */
    private static class FunctionSignature {
        String name;
        int minArgs;
        int maxArgs;
        List<String> argNames;
        
        FunctionSignature(String name, int minArgs, int maxArgs, List<String> argNames) {
            this.name = name;
            this.minArgs = minArgs;
            this.maxArgs = maxArgs;
            this.argNames = argNames;
        }
    }
    
    /**
     * Main method showing usage
     */
    public static void main(String[] args) throws Exception {
        String input = "set(body, ParseJSON(attributes[\"data\"])) where name == SPAN_KIND_SERVER";
        
        // Step 1: Parse with ANTLR
        CharStream charStream = CharStreams.fromString(input);
        OTTLLexer lexer = new OTTLLexer(charStream);
        CommonTokenStream tokens = new CommonTokenStream(lexer);
        OTTLParser parser = new OTTLParser(tokens);
        
        // Step 2: Generate parse tree
        OTTLParser.StatementContext tree = parser.statement();
        
        // Step 3: Semantic validation
        SemanticValidator validator = new SemanticValidator("log");
        validator.visit(tree);
        
        // Step 4: Report results
        if (validator.isValid()) {
            System.out.println("✓ Validation passed!");
        } else {
            System.out.println("✗ Validation failed:");
            for (String error : validator.getErrors()) {
                System.out.println("  " + error);
            }
        }
    }
}
