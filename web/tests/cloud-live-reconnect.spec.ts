import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

// Explicit opt-in: terminate only this installed preview's owned processes.
// No public service or unrelated SSH session is stopped.
const enabled = process.env.PRINCIPIA_TEST_RECONNECT_LIVE === "1";
function readerPid() {
  const pid = Number(
    execFileSync("lsof", ["-tiTCP:8767", "-sTCP:LISTEN"], {
      encoding: "utf8",
    }).trim(),
  );
  const command = execFileSync("ps", ["-p", String(pid), "-o", "command="], {
    encoding: "utf8",
  });
  if (!command.includes("/Principia-Legacy Preview/start-cloud.py"))
    throw new Error("Refusing to stop an unrelated process");
  return pid;
}
function sshPid(parent: number) {
  const rows = execFileSync("ps", ["-axo", "pid,ppid,command"], {
    encoding: "utf8",
  }).split("\n");
  const children = rows.filter((row) => {
    const fields = row.trim().split(/\s+/);
    return (
      Number(fields[1]) === parent &&
      fields[2] === "ssh" &&
      row.includes(":127.0.0.1:18765") &&
      row.endsWith(" principia-hk")
    );
  });
  if (children.length !== 1)
    throw new Error("Expected exactly one owned SSH child");
  return Number(children[0].trim().split(/\s+/)[0]);
}
for (const interruption of ["ssh", "reader"] as const) {
  test(`live ${interruption} interruption recovers in the same browser page`, async ({
    page,
  }, info) => {
    test.skip(
      !enabled || info.project.name !== "desktop",
      "Opt-in test of installed Mac login service",
    );
    test.setTimeout(60000);
    await page.goto("/");
    await expect(page.locator(".flagship-card")).toHaveCount(5);
    const parent = readerPid();
    const child = sshPid(parent);
    const started = Date.now();
    process.kill(interruption === "ssh" ? child : parent, "SIGTERM");
    const query = interruption === "ssh" ? "neuronal state space" : "Einstein";
    await page.getByRole("textbox", { name: "Search the atlas" }).fill(query);
    if (interruption === "ssh") {
      await expect(
        page.getByRole("heading", {
          name: "Dimensionality reduction for large-scale neural recordings",
        }),
      ).toBeVisible({ timeout: 40000 });
    } else {
      await expect(
        page.locator(".person-card").filter({ hasText: "Albert Einstein" }),
      ).toBeVisible({ timeout: 40000 });
    }
    await expect(page.locator(".connection-notice")).toHaveCount(0);
    await expect(page.locator(".error")).toHaveCount(0);
    await expect(
      page.getByRole("textbox", { name: "Search the atlas" }),
    ).toHaveValue(query);
    const newParent = readerPid();
    const newChild = sshPid(newParent);
    expect(newChild).not.toBe(child);
    if (interruption === "ssh") expect(newParent).toBe(parent);
    else expect(newParent).not.toBe(parent);
    writeFileSync(
      fileURLToPath(
        new URL(
          `../../reports/cloud-live-${interruption}-review5-20261028.json`,
          import.meta.url,
        ),
      ),
      JSON.stringify(
        {
          interruption,
          elapsed_ms: Date.now() - started,
          query_preserved: true,
          recovered_without_reload: true,
          exactly_one_ssh_child: true,
          reader_pid_changed: newParent !== parent,
          snapshot: "1.5.0-review5",
        },
        null,
        2,
      ) + "\n",
    );
  });
}
