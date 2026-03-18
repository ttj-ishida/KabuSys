KEEP A CHANGELOG
=================

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトはセマンティック バージョニングに従います。

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期公開: kabusys v0.1.0
  - src/kabusys/__init__.py にてパッケージ名とバージョンを定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルや環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートを .git または pyproject.toml から探索し、CWD に依存しない自動ロードを実現。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーを実装:
    - export KEY=VAL 形式対応、コメント行・空行無視、シングル/ダブルクォート内のバックスラッシュエスケープを考慮。
    - クォート無し値のインラインコメント判定ロジックを搭載。
  - Settings クラスを提供し、アプリケーションで利用する主要設定値をプロパティとして公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等。
    - データベースパス設定 (DUCKDB_PATH, SQLITE_PATH) と env/log レベル検証 (KABUSYS_ENV, LOG_LEVEL)。
    - is_live / is_paper / is_dev の補助プロパティ。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限 (120 req/min) を固定間隔スロットリングで制御する RateLimiter を実装。
    - 再試行ロジック（指数バックオフ、最大3回）および 401 時のトークン自動リフレッシュを実装。
    - ページネーション対応のフェッチ関数:
      - fetch_daily_quotes: 日足（OHLCV）取得（pagination_key を使用して全件取得）。
      - fetch_financial_statements: 財務諸表のページネーション取得。
      - fetch_market_calendar: JPX マーケットカレンダー取得。
    - DuckDB への保存関数（冪等）を実装:
      - save_daily_quotes: raw_prices テーブルに ON CONFLICT DO UPDATE で保存。
      - save_financial_statements: raw_financials テーブルに冪等保存。
      - save_market_calendar: market_calendar テーブルに冪等保存。
    - レスポンス→数値変換ユーティリティ _to_float / _to_int を実装（堅牢なパースと空値処理）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集モジュールを実装。
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。
    - URL 正規化（utm_* 等のトラッキングパラメータ除去、クエリソート、フラグメント除去）と記事ID生成（正規化 URL の SHA-256 の先頭 32 文字）。
    - RSS 受信時の安全対策:
      - defusedxml による XML パース（XML Bomb 等への対策）。
      - SSRF 対策: リダイレクト時のスキーム/ホスト検査、プライベートアドレス検出、許可スキーム制限 (http/https)。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）および gzip 解凍後の再検査。
    - テキスト前処理ユーティリティ（URL 除去、空白正規化）。
    - DB 保存:
      - save_raw_news: INSERT ... RETURNING を用いたチャンク挿入（トランザクションでまとめる）により新規挿入ID一覧を返す。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols への記事⇆銘柄紐付けを一括挿入（ON CONFLICT DO NOTHING、INSERT ... RETURNING 利用）。
    - 銘柄コード抽出: 4桁数字パターンに基づき known_codes でフィルタ（重複除去）。
    - run_news_collection: 複数フィードの収集→保存→銘柄紐付けをまとめた統合ジョブ（ソース単位で個別エラーハンドリング）。

- 研究用機能 (kabusys.research)
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から将来リターン（複数ホライズン）を DuckDB の prices_daily テーブルから一括で計算。
      - horizons の検証（正の整数かつ <= 252）。
      - 1 クエリで複数ホライズンを取得しパフォーマンス配慮。
    - calc_ic: Spearman ランク相関（Information Coefficient）計算。結合・None除外・3件未満判定。
    - rank: 同順位は平均ランクを与えるランク関数（丸めによる ties 漏れを防ぐため round(v,12) を使用）。
    - factor_summary: 各ファクター列について count/mean/std/min/max/median を標準ライブラリのみで計算。
    - これらは pandas 等の外部ライブラリに依存せず実装。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）を prices_daily から計算。
      - データスキャン範囲のバッファ設定や不足時の None 処理。
    - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio を計算（ATR の NULL 伝播を慎重に扱う）。
    - calc_value: raw_financials の最新財務データと prices_daily を組み合わせて PER / ROE を算出（EPS が 0/欠損時は None）。
  - research パッケージ __init__ で主要関数群をエクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank）と併せて kabusys.data.stats の zscore_normalize を参照している。

- DB スキーマ初期化 (kabusys.data.schema)
  - DuckDB 用 DDL を実装（Raw レイヤーのテーブル定義例を含む）。
    - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義（NOT NULL / CHECK / PRIMARY KEY 等の制約を含む）。
  - スキーマ定義は DataSchema.md に準拠する設計思想を反映。

- その他
  - strategy / execution パッケージの初期プレースホルダ (__init__.py を追加)。

Changed
- 初版リリースに際して、研究用コードは外部依存を極力排し標準ライブラリと DuckDB のみで動作するよう設計。

Fixed
- N/A（初版のため既知の修正履歴なし）

Security
- RSS / HTTP 関連で複数のセキュリティ対策を導入:
  - defusedxml による安全な XML パース。
  - SSRF 対策: リダイレクト先のスキーム/ホスト検証とプライベートアドレス拒否。
  - レスポンスサイズと gzip 解凍後サイズの上限チェック（DoS・Gzip bomb 対策）。
  - RSS 内の外部リンクを削除してテキスト正規化。
- J-Quants クライアントで 401 時のトークン自動リフレッシュは一度のみ行い、無限再帰を防止。

Notes / 注意事項
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等が Settings で必須とされているため、無い場合は ValueError が発生します。.env.example を参照して設定してください。
- research パッケージは kabusys.data.stats.zscore_normalize を使用しています。提供される環境では当該ユーティリティ（kabusys.data.stats）が存在することを前提としています。
- DuckDB スキーマ定義はコード内 DDL ベースで提供されていますが、運用環境でのマイグレーション・初期化処理は別途呼び出しが必要です（schema 初期化関数等は本スナップショットに明示的に含まれていない可能性があります）。
- raw_executions テーブル定義のスニペットが途中で切れているため、発注/約定関連のスキーマは完全実装を要確認。

Deprecated
- なし

Security Vulnerabilities
- なし（既知の脆弱性は記載されていませんが、外部 API 認証情報の管理には注意してください）。

今後の予定 (短期)
- strategy / execution 層の実装強化（発注ロジック、kabu API 統合）。
- スキーマ初期化関数のエントリーポイント追加（自動マイグレーション）。
- テストと CI の充実（特に network/SSRF 周りと J-Quants リトライ挙動）。
- パフォーマンス検証（DuckDB クエリや news_collector の大量データ処理）。