/*
 * GameTestServer.cs - Unity Editor HTTP 接口
 * 
 * 用法：
 *   1. 将此脚本放入 Unity 项目的 Assets/Editor/ 目录下
 *   2. 在 Unity 菜单栏点击 Tools > GameTestServer > Start
 *   3. Python 脚本通过 http://127.0.0.1:8765 调用
 * 
 * 接口：
 *   POST /ping        → {"ok": true}
 *   POST /screenshot   → {"ok": true, "image": "<base64 png>", "width": 640, "height": 1440}
 *   POST /tap          → {"x": 100, "y": 200}  → {"ok": true}
 *   POST /swipe        → {"x1": 100, "y1": 200, "x2": 300, "y2": 400, "duration": 500}  → {"ok": true}
 *   POST /touch_down   → {"x": 100, "y": 200}  → {"ok": true}
 *   POST /touch_up     → {}  → {"ok": true}
 *   POST /stop_server  → {}  → {"ok": true}
 */

#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using System;
using System.IO;
using System.Net;
using System.Threading;
using System.Text;
using System.Collections.Generic;

public class GameTestServer : MonoBehaviour
{
    private HttpListener listener;
    private Thread listenerThread;
    private bool running = false;
    private int port = 8765;

    // 线程安全的命令队列
    private static readonly Queue<Action> mainThreadActions = new Queue<Action>();
    private static readonly object queueLock = new object();

    // 模拟触摸状态
    private static bool isHolding = false;
    private static Vector2 holdPosition;

    [MenuItem("Tools/GameTestServer/Start")]
    public static void StartServer()
    {
        var go = GameObject.Find("__GameTestServer__");
        if (go != null) DestroyImmediate(go);
        go = new GameObject("__GameTestServer__");
        go.hideFlags = HideFlags.HideAndDontSave;
        var server = go.AddComponent<GameTestServer>();
        server.StartListening();
    }

    [MenuItem("Tools/GameTestServer/Stop")]
    public static void StopServer()
    {
        var go = GameObject.Find("__GameTestServer__");
        if (go != null)
        {
            var server = go.GetComponent<GameTestServer>();
            if (server != null) server.StopListening();
            DestroyImmediate(go);
        }
    }

    void StartListening()
    {
        try
        {
            listener = new HttpListener();
            listener.Prefixes.Add($"http://127.0.0.1:{port}/");
            listener.Start();
            running = true;

            listenerThread = new Thread(ListenLoop) { IsBackground = true };
            listenerThread.Start();

            Debug.Log($"[GameTestServer] 已启动: http://127.0.0.1:{port}/");
        }
        catch (Exception e)
        {
            Debug.LogError($"[GameTestServer] 启动失败: {e.Message}");
        }
    }

    void StopListening()
    {
        running = false;
        listener?.Stop();
        Debug.Log("[GameTestServer] 已停止");
    }

    void OnDestroy()
    {
        StopListening();
    }

    void ListenLoop()
    {
        while (running)
        {
            try
            {
                var context = listener.GetContext();
                var request = context.Request;
                var response = context.Response;

                string body = "";
                using (var reader = new StreamReader(request.InputStream, Encoding.UTF8))
                {
                    body = reader.ReadToEnd();
                }

                string result = HandleRequest(request.Url.AbsolutePath, body);

                byte[] buffer = Encoding.UTF8.GetBytes(result);
                response.ContentType = "application/json";
                response.ContentLength64 = buffer.Length;
                response.OutputStream.Write(buffer, 0, buffer.Length);
                response.OutputStream.Close();
            }
            catch (HttpListenerException)
            {
                break; // listener stopped
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[GameTestServer] 请求处理错误: {e.Message}");
            }
        }
    }

    string HandleRequest(string path, string body)
    {
        switch (path)
        {
            case "/ping":
                return JsonOk();

            case "/screenshot":
                return HandleScreenshot();

            case "/tap":
                return HandleTap(body);

            case "/swipe":
                return HandleSwipe(body);

            case "/touch_down":
                return HandleTouchDown(body);

            case "/touch_up":
                return HandleTouchUp();

            case "/stop_server":
                EnqueueAction(() => StopServer());
                return JsonOk();

            default:
                return JsonError("未知接口: " + path);
        }
    }

    string HandleScreenshot()
    {
        // 在主线程截图
        string result = null;
        ManualResetEvent done = new ManualResetEvent(false);

        EnqueueAction(() =>
        {
            try
            {
                // 等待渲染完成
                // 使用 GameView 尺寸截图
                int w = (int)Handles.GetMainGameViewSize().x;
                int h = (int)Handles.GetMainGameViewSize().y;
                if (w <= 0) w = 640;
                if (h <= 0) h = 1440;

                var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
                tex.Apply();

                byte[] png = tex.EncodeToPNG();
                DestroyImmediate(tex);

                string b64 = Convert.ToBase64String(png);
                result = $"{{\"ok\":true,\"image\":\"{b64}\",\"width\":{w},\"height\":{h}}}";
            }
            catch (Exception e)
            {
                result = JsonError(e.Message);
            }
            finally
            {
                done.Set();
            }
        });

        done.WaitOne(5000);
        return result ?? JsonError("截图超时");
    }

    string HandleTap(string body)
    {
        var data = ParseJson(body);
        int x = GetInt(data, "x");
        int y = GetInt(data, "y");

        EnqueueAction(() =>
        {
            // 模拟鼠标点击
            SimulateClick(x, y);
        });

        return JsonOk();
    }

    string HandleSwipe(string body)
    {
        var data = ParseJson(body);
        int x1 = GetInt(data, "x1");
        int y1 = GetInt(data, "y1");
        int x2 = GetInt(data, "x2");
        int y2 = GetInt(data, "y2");
        int duration = GetInt(data, "duration", 300);

        EnqueueAction(() =>
        {
            SimulateSwipe(x1, y1, x2, y2, duration);
        });

        return JsonOk();
    }

    string HandleTouchDown(string body)
    {
        var data = ParseJson(body);
        int x = GetInt(data, "x");
        int y = GetInt(data, "y");

        EnqueueAction(() =>
        {
            isHolding = true;
            holdPosition = new Vector2(x, y);
            Debug.Log($"[GameTestServer] TouchDown: ({x}, {y})");
        });

        return JsonOk();
    }

    string HandleTouchUp()
    {
        EnqueueAction(() =>
        {
            isHolding = false;
            Debug.Log("[GameTestServer] TouchUp");
        });

        return JsonOk();
    }

    void SimulateClick(int x, int y)
    {
        // 通过 EditorWindow 向 GameView 发送事件
        var gameView = GetGameView();
        if (gameView != null)
        {
            var evt = new Event();
            evt.type = EventType.MouseDown;
            evt.mousePosition = new Vector2(x, y);
            evt.button = 0;
            gameView.SendEvent(evt);

            evt.type = EventType.MouseUp;
            gameView.SendEvent(evt);
        }
    }

    void SimulateSwipe(int x1, int y1, int x2, int y2, int durationMs)
    {
        var gameView = GetGameView();
        if (gameView == null) return;

        int steps = Math.Max(10, durationMs / 16); // ~60fps
        float dt = durationMs / 1000f / steps;

        // MouseDown
        var downEvt = new Event();
        downEvt.type = EventType.MouseDown;
        downEvt.mousePosition = new Vector2(x1, y1);
        downEvt.button = 0;
        gameView.SendEvent(downEvt);

        for (int i = 1; i <= steps; i++)
        {
            float t = (float)i / steps;
            float cx = Mathf.Lerp(x1, x2, t);
            float cy = Mathf.Lerp(y1, y2, t);

            var dragEvt = new Event();
            dragEvt.type = EventType.MouseDrag;
            dragEvt.mousePosition = new Vector2(cx, cy);
            dragEvt.button = 0;
            gameView.SendEvent(dragEvt);

            Thread.Sleep((int)(dt * 1000));
        }

        // MouseUp
        var upEvt = new Event();
        upEvt.type = EventType.MouseUp;
        upEvt.mousePosition = new Vector2(x2, y2);
        upEvt.button = 0;
        gameView.SendEvent(upEvt);
    }

    EditorWindow GetGameView()
    {
        // 获取 GameView 窗口
        var type = typeof(EditorWindow).Assembly.GetType("UnityEditor.GameView");
        if (type != null)
        {
            return EditorWindow.GetWindow(type);
        }
        return null;
    }

    // === 工具方法 ===

    static void EnqueueAction(Action action)
    {
        lock (queueLock)
        {
            mainThreadActions.Enqueue(action);
        }
    }

    void Update()
    {
        lock (queueLock)
        {
            while (mainThreadActions.Count > 0)
            {
                var action = mainThreadActions.Dequeue();
                try { action(); }
                catch (Exception e) { Debug.LogError(e); }
            }
        }
    }

    static Dictionary<string, string> ParseJson(string json)
    {
        var result = new Dictionary<string, string>();
        if (string.IsNullOrEmpty(json)) return result;

        json = json.Trim().TrimStart('{').TrimEnd('}');
        foreach (var pair in json.Split(','))
        {
            var parts = pair.Split(':');
            if (parts.Length >= 2)
            {
                string key = parts[0].Trim().Trim('"');
                string value = string.Join(":", parts, 1, parts.Length - 1).Trim().Trim('"');
                result[key] = value;
            }
        }
        return result;
    }

    static int GetInt(Dictionary<string, string> data, string key, int defaultVal = 0)
    {
        if (data.ContainsKey(key) && int.TryParse(data[key], out int val))
            return val;
        return defaultVal;
    }

    static string JsonOk()
    {
        return "{\"ok\":true}";
    }

    static string JsonError(string msg)
    {
        return $"{{\"ok\":false,\"error\":\"{msg}\"}}";
    }
}
#endif
