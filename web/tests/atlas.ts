import { expect, type APIRequestContext } from "@playwright/test";

// Browser reads retry a disconnected tunnel. Setup requests need the same
// bounded tolerance, while assertions about record contents remain unchanged.
export async function atlasJSON(request: APIRequestContext, path: string) {
  let data: any;
  await expect
    .poll(
      async () => {
        const response = await request.get(path);
        if (response.ok()) {
          data = await response.json();
          return true;
        }
        expect([502, 503]).toContain(response.status());
        return false;
      },
      { timeout: 20000, intervals: [250, 1000, 2000] },
    )
    .toBe(true);
  return data;
}

export async function atlasTopics(request: APIRequestContext) {
  const dossiers: any[] = [];
  let release = "";
  for (let offset = 0; ; offset += 100) {
    const page = await atlasJSON(
      request,
      `/api/dossiers?summary=true&limit=100&offset=${offset}&release=${release}`,
    );
    release = page.release_id;
    dossiers.push(...page.dossiers);
    if (dossiers.length >= page.total) return { ...page, dossiers };
  }
}
