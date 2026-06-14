package gov.burtonmi.explore;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.widget.RemoteViews;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

/**
 * Home-screen widget (#65): shows the current city alert and the next council
 * meeting. Data is fetched natively (no WebView/JS) from the same public sources
 * the app uses -- alerts.json on the origin and the CivicClerk Events API -- so
 * there is no CORS constraint. Everything is best-effort: any failure leaves a
 * calm fallback string, never a crash. Taps reuse the #55 deep-link handler.
 */
public class ExploreWidgetProvider extends AppWidgetProvider {

    private static final String ORIGIN = "https://explore.burtonmi.gov";
    private static final String ALERTS_URL = ORIGIN + "/alerts.json";
    private static final String CIVICCLERK = "https://burtonmi.api.civicclerk.com/v1/Events";

    @Override
    public void onUpdate(Context context, AppWidgetManager mgr, int[] ids) {
        // goAsync() keeps the broadcast alive (~10s) while a background thread does
        // the network; without it the process could be killed mid-fetch.
        final PendingResult pending = goAsync();
        final Context appContext = context.getApplicationContext();
        new Thread(() -> {
            try {
                String alert = fetchActiveAlert();
                String meeting = fetchNextMeeting();
                AppWidgetManager m = AppWidgetManager.getInstance(appContext);
                int[] live = m.getAppWidgetIds(new ComponentName(appContext, ExploreWidgetProvider.class));
                for (int id : live) render(appContext, m, id, alert, meeting);
            } catch (Throwable ignored) {
                // never let a widget update crash the host launcher
            } finally {
                pending.finish();
            }
        }).start();
    }

    private void render(Context ctx, AppWidgetManager mgr, int id, String alert, String meeting) {
        RemoteViews views = new RemoteViews(ctx.getPackageName(), R.layout.widget_explore);
        views.setTextViewText(R.id.widget_alert, alert);
        views.setTextViewText(R.id.widget_meeting, meeting);
        // Whole card -> open the app; meeting line -> open the meetings guide section.
        views.setOnClickPendingIntent(R.id.widget_root, openAppIntent(ctx, ORIGIN + "/"));
        views.setOnClickPendingIntent(R.id.widget_meeting, openAppIntent(ctx, ORIGIN + "/#guide/meetings"));
        mgr.updateAppWidget(id, views);
    }

    private PendingIntent openAppIntent(Context ctx, String url) {
        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
        intent.setClassName(ctx.getPackageName(), "gov.burtonmi.explore.MainActivity");
        int flags = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE;
        // distinct request codes so the two targets get distinct PendingIntents
        return PendingIntent.getActivity(ctx, url.hashCode(), intent, flags);
    }

    /** First alert active today (start <= today <= end), or a calm fallback. */
    private String fetchActiveAlert() {
        try {
            JSONObject root = new JSONObject(httpGet(ALERTS_URL));
            JSONArray alerts = root.optJSONArray("alerts");
            if (alerts == null) return "No active alerts";
            String today = isoToday();
            for (int i = 0; i < alerts.length(); i++) {
                JSONObject a = alerts.optJSONObject(i);
                if (a == null) continue;
                String start = a.optString("start", "");
                String end = a.optString("end", "");
                if (!start.isEmpty() && !end.isEmpty()
                        && start.compareTo(today) <= 0 && today.compareTo(end) <= 0) {
                    String title = a.optString("title", "City alert");
                    return "\u26a0 " + title; // U+26A0 warning sign (escaped for source-encoding safety)
                }
            }
            return "No active alerts";
        } catch (Throwable t) {
            return "Alerts unavailable";
        }
    }

    /** Next upcoming CivicClerk meeting as "Next meeting: <date>", or a fallback. */
    private String fetchNextMeeting() {
        try {
            String nowIso = isoNowUtc();
            String url = CIVICCLERK + "?"
                    + "$top=1"
                    + "&$orderby=" + enc("startDateTime asc")
                    + "&$filter=" + enc("startDateTime ge " + nowIso);
            JSONObject root = new JSONObject(httpGet(url));
            JSONArray value = root.optJSONArray("value");
            if (value == null || value.length() == 0) return "No upcoming meetings";
            JSONObject ev = value.optJSONObject(0);
            String start = ev.optString("startDateTime", "");
            String when = formatMeeting(start);
            return when.isEmpty() ? "Next meeting scheduled" : "Next meeting: " + when;
        } catch (Throwable t) {
            return "Meetings unavailable";
        }
    }

    // --- helpers -------------------------------------------------------------

    private static String enc(String s) throws Exception {
        return URLEncoder.encode(s, "UTF-8");
    }

    /** Local-clock today as YYYY-MM-DD (matches the app's alert active-date rule). */
    private static String isoToday() {
        return new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date());
    }

    private static String isoNowUtc() {
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US);
        f.setTimeZone(TimeZone.getTimeZone("UTC"));
        return f.format(new Date());
    }

    /** CivicClerk stores local wall-clock with a Z suffix; render in UTC to avoid a
     *  timezone shift (same approach as the in-app meetings widget). */
    private static String formatMeeting(String iso) {
        if (iso == null || iso.isEmpty()) return "";
        try {
            SimpleDateFormat in = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US);
            in.setTimeZone(TimeZone.getTimeZone("UTC"));
            // trim fractional seconds / trailing Z if present
            String trimmed = iso.length() >= 19 ? iso.substring(0, 19) : iso;
            Date d = in.parse(trimmed);
            if (d == null) return "";
            SimpleDateFormat out = new SimpleDateFormat("EEE, MMM d \u00b7 h:mm a", Locale.US);
            out.setTimeZone(TimeZone.getTimeZone("UTC"));
            return out.format(d);
        } catch (Throwable t) {
            return "";
        }
    }

    private static String httpGet(String urlStr) throws Exception {
        HttpURLConnection conn = null;
        try {
            URL url = new URL(urlStr);
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(7000);
            conn.setReadTimeout(7000);
            conn.setRequestProperty("Accept", "application/json");
            int code = conn.getResponseCode();
            if (code != 200) throw new Exception("HTTP " + code);
            StringBuilder sb = new StringBuilder();
            try (BufferedReader r = new BufferedReader(new InputStreamReader(conn.getInputStream(), "UTF-8"))) {
                String line;
                while ((line = r.readLine()) != null) sb.append(line);
            }
            return sb.toString();
        } finally {
            if (conn != null) conn.disconnect();
        }
    }
}
