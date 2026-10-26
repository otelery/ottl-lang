// Differential-test oracle: parses inputs with the real upstream Participle parser.
// Copied into pkg/ottl by tests/differential/run.py; it must live in package ottl
// because parseStatement/parseCondition/parseValueExpression are unexported.
//
// Input lines (DIFF_IN):  <mode>\t<base64(input)>   mode = statement | condition | value
// Output lines (DIFF_OUT): OK | ERR\t<base64(first line of error)>
package ottl

import (
	"bufio"
	"encoding/base64"
	"os"
	"strings"
	"testing"
)

func TestZZDifferential(t *testing.T) {
	in, out := os.Getenv("DIFF_IN"), os.Getenv("DIFF_OUT")
	if in == "" || out == "" {
		t.Skip("DIFF_IN/DIFF_OUT not set")
	}
	fin, err := os.Open(in)
	if err != nil {
		t.Fatal(err)
	}
	defer fin.Close()
	fout, err := os.Create(out)
	if err != nil {
		t.Fatal(err)
	}
	defer fout.Close()
	w := bufio.NewWriter(fout)
	defer w.Flush()

	sc := bufio.NewScanner(fin)
	sc.Buffer(make([]byte, 1<<20), 1<<24)
	for sc.Scan() {
		mode, enc, _ := strings.Cut(sc.Text(), "\t")
		raw, err := base64.StdEncoding.DecodeString(enc)
		if err != nil {
			t.Fatalf("bad base64: %v", err)
		}
		var perr error
		func() {
			defer func() {
				if r := recover(); r != nil {
					perr = &panicErr{r}
				}
			}()
			switch mode {
			case "statement":
				_, perr = parseStatement(string(raw))
			case "condition":
				_, perr = parseCondition(string(raw))
			case "value":
				_, perr = parseValueExpression(string(raw))
			default:
				t.Fatalf("unknown mode %q", mode)
			}
		}()
		if perr == nil {
			w.WriteString("OK\n")
			continue
		}
		msg := strings.ReplaceAll(perr.Error(), "\n", " ")
		w.WriteString("ERR\t" + base64.StdEncoding.EncodeToString([]byte(msg)) + "\n")
	}
}

type panicErr struct{ v any }

func (p *panicErr) Error() string { return "PANIC" }
