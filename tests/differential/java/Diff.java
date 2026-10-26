// Differential-test ANTLR driver: batch-parses inputs with the generated OTTL parser.
// Input lines:  <mode>\t<base64(input)>   mode = statement | condition | value
// Output lines: OK | ERR\t<base64(first error)>
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import org.antlr.v4.runtime.*;

public class Diff {
    static class Collect extends BaseErrorListener {
        String first;
        @Override
        public void syntaxError(Recognizer<?, ?> r, Object o, int line, int col, String msg, RecognitionException e) {
            if (first == null) first = line + ":" + col + " " + msg;
        }
    }

    public static void main(String[] args) throws Exception {
        BufferedReader in = new BufferedReader(new InputStreamReader(new FileInputStream(args[0]), StandardCharsets.UTF_8));
        PrintWriter out = new PrintWriter(new BufferedWriter(new OutputStreamWriter(new FileOutputStream(args[1]), StandardCharsets.UTF_8)));
        String line;
        while ((line = in.readLine()) != null) {
            int tab = line.indexOf('\t');
            String mode = line.substring(0, tab);
            String src = new String(Base64.getDecoder().decode(line.substring(tab + 1)), StandardCharsets.UTF_8);
            Collect c = new Collect();
            try {
                OTTLLexer lx = new OTTLLexer(CharStreams.fromString(src));
                lx.removeErrorListeners();
                lx.addErrorListener(c);
                OTTLParser p = new OTTLParser(new CommonTokenStream(lx));
                p.removeErrorListeners();
                p.addErrorListener(c);
                switch (mode) {
                    case "statement": p.statement(); break;
                    case "condition": p.condition(); break;
                    case "value": p.valueEntry(); break;
                    default: throw new IllegalArgumentException(mode);
                }
            } catch (Exception e) {
                if (c.first == null) c.first = "EXC " + e;
            }
            if (c.first == null) out.println("OK");
            else out.println("ERR\t" + Base64.getEncoder().encodeToString(c.first.getBytes(StandardCharsets.UTF_8)));
        }
        out.flush();
    }
}
