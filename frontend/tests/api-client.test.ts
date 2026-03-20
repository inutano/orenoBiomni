import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Import after mocking
const api = await import("@/lib/api-client");

beforeEach(() => {
  mockFetch.mockReset();
});

describe("api-client", () => {
  describe("createSession", () => {
    it("sends POST with title", async () => {
      const session = { id: "abc-123", title: "Test", is_active: true };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: () => Promise.resolve(session),
      });

      const result = await api.createSession("Test");
      expect(mockFetch).toHaveBeenCalledWith("/api/v1/sessions", expect.objectContaining({
        method: "POST",
      }));
      expect(result).toEqual(session);
    });

    it("throws on error response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve("Internal Server Error"),
      });

      await expect(api.createSession("Fail")).rejects.toThrow();
    });
  });

  describe("listSessions", () => {
    it("fetches session list", async () => {
      const sessions = [{ id: "1" }, { id: "2" }];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(sessions),
      });

      const result = await api.listSessions();
      expect(result).toHaveLength(2);
    });
  });

  describe("deleteSession", () => {
    it("sends DELETE and handles 204", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await api.deleteSession("abc-123");
      expect(mockFetch).toHaveBeenCalledWith("/api/v1/sessions/abc-123", expect.objectContaining({
        method: "DELETE",
      }));
    });
  });

  describe("getHealth", () => {
    it("fetches health data", async () => {
      const health = { status: "ok", agent_ready: true, database: "connected" };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(health),
      });

      const result = await api.getHealth();
      expect(result.status).toBe("ok");
    });
  });
});
