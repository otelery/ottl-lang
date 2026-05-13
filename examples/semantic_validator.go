package mainpackage examples


import (
	"fmt"
	"github.com/antlr/antlr4/runtime/Go/antlr/v4"
	// Import your generated parser package
	// parser "yourproject/ottl/parser"
)

/**
 * Semantic Validator for OTTL using ANTLR Visitor Pattern in Go
 * 
 * This demonstrates how to implement semantic validation after syntax parsing.
 * 
 * Semantic checks performed:
 * 1. Function existence validation
 * 2. Argument count validation
 * 3. Context validation (e.g., body only in log context)
 * 4. Enum value validation
 */

// FunctionSignature defines the signature of an OTTL function
type FunctionSignature struct {
	Name     string
	MinArgs  int
	MaxArgs  int
	ArgNames []string
}

// SemanticValidator performs semantic validation on OTTL statements
type SemanticValidator struct {
	*parser.BaseOTTLVisitor
	errors             []string
	editorFunctions    map[string]FunctionSignature
	converterFunctions map[string]FunctionSignature
	validEnums         map[string]bool
	currentContext     string // log, metric, trace, etc.
}

// NewSemanticValidator creates a new semantic validator
func NewSemanticValidator(context string) *SemanticValidator {
	v := &SemanticValidator{
		BaseOTTLVisitor:    &parser.BaseOTTLVisitor{},
		errors:             []string{},
		editorFunctions:    make(map[string]FunctionSignature),
		converterFunctions: make(map[string]FunctionSignature),
		validEnums:         make(map[string]bool),
		currentContext:     context,
	}
	v.initializeKnownFunctions()
	v.initializeKnownEnums()
	return v
}

// Initialize known editor functions with their signatures
func (v *SemanticValidator) initializeKnownFunctions() {
	// Editors (lowercase)
	v.editorFunctions["set"] = FunctionSignature{
		Name: "set", MinArgs: 2, MaxArgs: 2,
		ArgNames: []string{"path", "value"},
	}
	v.editorFunctions["delete_key"] = FunctionSignature{
		Name: "delete_key", MinArgs: 2, MaxArgs: 2,
		ArgNames: []string{"target", "key"},
	}
	v.editorFunctions["merge_maps"] = FunctionSignature{
		Name: "merge_maps", MinArgs: 3, MaxArgs: 3,
		ArgNames: []string{"target", "source", "strategy"},
	}
	v.editorFunctions["flatten"] = FunctionSignature{
		Name: "flatten", MinArgs: 1, MaxArgs: 3,
		ArgNames: []string{"target", "prefix", "depth"},
	}
	v.editorFunctions["replace_pattern"] = FunctionSignature{
		Name: "replace_pattern", MinArgs: 3, MaxArgs: 4,
		ArgNames: []string{"target", "pattern", "replacement", "function"},
	}

	// Converters (CamelCase)
	v.converterFunctions["ParseJSON"] = FunctionSignature{
		Name: "ParseJSON", MinArgs: 1, MaxArgs: 1,
		ArgNames: []string{"input"},
	}
	v.converterFunctions["Split"] = FunctionSignature{
		Name: "Split", MinArgs: 2, MaxArgs: 2,
		ArgNames: []string{"value", "delimiter"},
	}
	v.converterFunctions["Concat"] = FunctionSignature{
		Name: "Concat", MinArgs: 2, MaxArgs: 2,
		ArgNames: []string{"values", "separator"},
	}
	v.converterFunctions["IsMatch"] = FunctionSignature{
		Name: "IsMatch", MinArgs: 2, MaxArgs: 2,
		ArgNames: []string{"target", "pattern"},
	}
	v.converterFunctions["ConvertCase"] = FunctionSignature{
		Name: "ConvertCase", MinArgs: 2, MaxArgs: 2,
		ArgNames: []string{"target", "to"},
	}
	v.converterFunctions["ExtractPatterns"] = FunctionSignature{
		Name: "ExtractPatterns", MinArgs: 2, MaxArgs: 2,
		ArgNames: []string{"target", "pattern"},
	}
	v.converterFunctions["Time"] = FunctionSignature{
		Name: "Time", MinArgs: 2, MaxArgs: 2,
		ArgNames: []string{"value", "format"},
	}
	v.converterFunctions["Duration"] = FunctionSignature{
		Name: "Duration", MinArgs: 1, MaxArgs: 1,
		ArgNames: []string{"value"},
	}
	v.converterFunctions["Decode"] = FunctionSignature{
		Name: "Decode", MinArgs: 2, MaxArgs: 2,
		ArgNames: []string{"value", "encoding"},
	}
}

// Initialize known enum values
func (v *SemanticValidator) initializeKnownEnums() {
	// Span kinds
	v.validEnums["SPAN_KIND_SERVER"] = true
	v.validEnums["SPAN_KIND_CLIENT"] = true
	v.validEnums["SPAN_KIND_PRODUCER"] = true
	v.validEnums["SPAN_KIND_CONSUMER"] = true
	v.validEnums["SPAN_KIND_INTERNAL"] = true

	// Status codes
	v.validEnums["STATUS_CODE_OK"] = true
	v.validEnums["STATUS_CODE_ERROR"] = true
	v.validEnums["STATUS_CODE_UNSET"] = true

	// Severity numbers
	v.validEnums["SEVERITY_NUMBER_UNSPECIFIED"] = true
	v.validEnums["SEVERITY_NUMBER_TRACE"] = true
	v.validEnums["SEVERITY_NUMBER_DEBUG"] = true
	v.validEnums["SEVERITY_NUMBER_INFO"] = true
	v.validEnums["SEVERITY_NUMBER_WARN"] = true
	v.validEnums["SEVERITY_NUMBER_ERROR"] = true
	v.validEnums["SEVERITY_NUMBER_FATAL"] = true

	// Log levels
	v.validEnums["LOG_LEVEL_DEBUG"] = true
	v.validEnums["LOG_LEVEL_INFO"] = true
	v.validEnums["LOG_LEVEL_WARN"] = true
	v.validEnums["LOG_LEVEL_ERROR"] = true
}

// VisitEditor validates editor function calls
func (v *SemanticValidator) VisitEditor(ctx *parser.EditorContext) interface{} {
	funcName := ctx.LOWERCASE_ID().GetText()

	// Check if function exists
	sig, exists := v.editorFunctions[funcName]
	if !exists {
		v.addError(ctx, fmt.Sprintf("Unknown editor function: %s", funcName))
		return false
	}

	// Validate argument count
	argCount := 0
	if ctx.Arguments() != nil {
		argCount = len(ctx.Arguments().AllArgument())
	}

	if argCount < sig.MinArgs || argCount > sig.MaxArgs {
		v.addError(ctx, fmt.Sprintf(
			"Function '%s' expects %d-%d arguments, got %d",
			funcName, sig.MinArgs, sig.MaxArgs, argCount,
		))
	}

	return v.VisitChildren(ctx)
}

// VisitConverter validates converter function calls
func (v *SemanticValidator) VisitConverter(ctx *parser.ConverterContext) interface{} {
	funcName := ctx.UPPERCASE_ID().GetText()

	// Check if function exists
	sig, exists := v.converterFunctions[funcName]
	if !exists {
		v.addError(ctx, fmt.Sprintf("Unknown converter function: %s", funcName))
		return false
	}

	// Validate argument count
	argCount := 0
	if ctx.Arguments() != nil {
		argCount = len(ctx.Arguments().AllArgument())
	}

	if argCount < sig.MinArgs || argCount > sig.MaxArgs {
		v.addError(ctx, fmt.Sprintf(
			"Converter '%s' expects %d-%d arguments, got %d",
			funcName, sig.MinArgs, sig.MaxArgs, argCount,
		))
	}

	return v.VisitChildren(ctx)
}

// VisitEnumValue validates enum values
func (v *SemanticValidator) VisitEnumValue(ctx *parser.EnumValueContext) interface{} {
	enumName := ctx.UPPERCASE_ID().GetText()

	if !v.validEnums[enumName] {
		v.addError(ctx, fmt.Sprintf(
			"Unknown enum value: %s. Did you mean to use a converter function?",
			enumName,
		))
	}

	return true
}

// VisitPath validates path expressions
func (v *SemanticValidator) VisitPath(ctx *parser.PathContext) interface{} {
	var firstToken string
	if ctx.LOWERCASE_ID() != nil {
		firstToken = ctx.LOWERCASE_ID().GetText()
	} else {
		firstToken = ctx.AllField()[0].LOWERCASE_ID().GetText()
	}

	// Validate context-specific paths
	switch firstToken {
	case "body":
		if v.currentContext != "log" {
			v.addError(ctx, "Field 'body' is only available in log context")
		}
	case "name", "description", "unit":
		if v.currentContext != "metric" {
			v.addError(ctx, "Metric fields are only available in metric context")
		}
	case "trace_id", "span_id", "parent_span_id":
		if v.currentContext != "trace" {
			v.addError(ctx, "Trace fields are only available in trace context")
		}
	}

	return v.VisitChildren(ctx)
}

// addError adds a validation error with context information
func (v *SemanticValidator) addError(ctx antlr.ParserRuleContext, message string) {
	line := ctx.GetStart().GetLine()
	col := ctx.GetStart().GetColumn()
	v.errors = append(v.errors, fmt.Sprintf("Line %d:%d - %s", line, col, message))
}

// GetErrors returns all validation errors
func (v *SemanticValidator) GetErrors() []string {
	return v.errors
}

// IsValid returns true if no validation errors occurred
func (v *SemanticValidator) IsValid() bool {
	return len(v.errors) == 0
}

// Example usage
func main() {
	// Example 1: Valid OTTL statement
	input1 := `set(attributes["test"], ParseJSON(body)) where name == "http"`
	validateStatement(input1, "log")

	// Example 2: Invalid - unknown function
	input2 := `unknown_func(attributes["test"], "value")`
	validateStatement(input2, "log")

	// Example 3: Invalid - wrong argument count
	input3 := `set(attributes["test"])`
	validateStatement(input3, "log")

	// Example 4: Invalid - enum typo
	input4 := `set(attributes["kind"], true) where kind == SPAN_KIND_SERVERS`
	validateStatement(input4, "trace")

	// Example 5: Invalid - body in wrong context
	input5 := `set(attributes["data"], body)`
	validateStatement(input5, "metric")
}

func validateStatement(input string, context string) {
	fmt.Printf("\n--- Validating: %s (context: %s) ---\n", input, context)

	// Step 1: Parse with ANTLR
	is := antlr.NewInputStream(input)
	lexer := parser.NewOTTLLexer(is)
	stream := antlr.NewCommonTokenStream(lexer, antlr.TokenDefaultChannel)
	p := parser.NewOTTLParser(stream)

	// Remove default error listeners and add custom one
	p.RemoveErrorListeners()
	errorListener := &CustomErrorListener{}
	p.AddErrorListener(errorListener)

	// Step 2: Generate parse tree
	tree := p.Statement()

	// Check for syntax errors first
	if len(errorListener.errors) > 0 {
		fmt.Println("✗ Syntax errors:")
		for _, err := range errorListener.errors {
			fmt.Printf("  %s\n", err)
		}
		return
	}

	// Step 3: Semantic validation
	validator := NewSemanticValidator(context)
	validator.Visit(tree)

	// Step 4: Report results
	if validator.IsValid() {
		fmt.Println("✓ Validation passed!")
	} else {
		fmt.Println("✗ Semantic validation failed:")
		for _, err := range validator.GetErrors() {
			fmt.Printf("  %s\n", err)
		}
	}
}

// CustomErrorListener for capturing parse errors
type CustomErrorListener struct {
	*antlr.DefaultErrorListener
	errors []string
}

func (c *CustomErrorListener) SyntaxError(recognizer antlr.Recognizer, offendingSymbol interface{}, line, column int, msg string, e antlr.RecognitionException) {
	c.errors = append(c.errors, fmt.Sprintf("Line %d:%d - %s", line, column, msg))
}
