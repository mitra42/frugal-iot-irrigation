import app.freerouting.core.*;
import app.freerouting.interactive.*;
import app.freerouting.board.*;
import app.freerouting.settings.*;
import app.freerouting.autoroute.*;
import java.io.*;
import java.util.*;
import java.lang.reflect.*;

/** Headless Freerouting driver with a real pass limit and a save after every improvement.
 *  java -cp freerouting.jar:. Route in.dsn out.ses maxPasses */
public class Route {
  static class T extends StoppableThread { protected void thread_action() {} }
  public static void main(String[] a) throws Exception {
    String in = a[0], out = a[1]; int maxp = Integer.parseInt(a[2]);
    RoutingJob job = new RoutingJob();
    HeadlessBoardManager bm = new HeadlessBoardManager(Locale.US, job);
    bm.loadFromSpecctraDsn(new FileInputStream(in), new BoardObserverAdaptor(), new ItemIdentificationNumberGenerator());
    RoutingBoard board = bm.get_routing_board();
    RouterSettings rs = new RouterSettings(board);
    job.routerSettings = rs; job.board = board; job.thread = new T();
    BatchAutorouter ar = new BatchAutorouter(job);
    Method pass = BatchAutorouter.class.getDeclaredMethod("autoroute_pass", int.class);
    pass.setAccessible(true);
    int best = Integer.MAX_VALUE;
    for (int p = 1; p <= maxp; p++) {
      boolean more = (boolean) pass.invoke(ar, p);
      int inc = new RatsNest(board).incomplete_count();
      System.out.println("pass " + p + " incomplete " + inc + (more ? "" : " (router done)"));
      if (inc < best) {
        best = inc;
        try (FileOutputStream f = new FileOutputStream(out)) { bm.saveAsSpecctraSessionSes(f, "board"); }
        System.out.println("  saved " + out + " with " + inc + " incomplete");
      }
      if (!more || inc == 0) break;
    }
    System.exit(0);
  }
}
