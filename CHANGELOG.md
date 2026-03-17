# CHANGELOG

すべての重要な変更は Keep a Changelog の形式で記載しています。  
このファイルはコードベースの現状（初期リリース相当）から推測して作成した変更履歴です。

なお、バージョン番号はパッケージの __version__ (src/kabusys/__init__.py) に合わせて 0.1.0 としています。

## [0.1.0] - 2026-03-17

### 追加 (Added)
- 初期公開: KabuSys 日本株自動売買システムの基本モジュール群を実装。
  - パッケージ構成:
    - kabusys.config: 環境変数・設定管理
    - kabusys.data: データ取得・保存・スキーマ定義・ETL パイプライン
    - kabusys.data.jquants_client: J-Quants API クライアント（価格・財務・カレンダー取得 + DuckDB 保存）
    - kabusys.data.news_collector: RSS ベースのニュース収集器（前処理・ID生成・DB保存・銘柄紐付け）
    - kabusys.data.schema: DuckDB スキーマ定義と初期化ユーティリティ
    - kabusys.data.pipeline: 差分ETL（差分取得・保存・品質チェックの統合）
    - kabusys.execution, kabusys.strategy, kabusys.monitoring: パッケージエクスポート用プレースホルダ

- 設定管理（kabusys.config.Settings）
  - .env ファイル（プロジェクトルート：.git または pyproject.toml を基準）および環境変数から設定を自動読込。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env 解析の強化:
    - export KEY=val 形式対応
    - クォート中のバックスラッシュエスケープ処理
    - コメント取り扱いルール（クォート有無での違い）
  - 必須設定取得時のバリデーション（未設定時は ValueError）
  - KABUSYS_ENV 値チェック（development/paper_trading/live）
  - LOG_LEVEL 値チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 取得対象:
    - 日次株価（OHLCV）
    - 財務（四半期 BS/PL）
    - JPX マーケットカレンダー
  - 設計上の特徴:
    - レート制限遵守（固定間隔スロットリング、120 req/min）
    - リトライロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx、429 の場合は Retry-After 優先）
    - 401 受信時にリフレッシュトークンで自動リフレッシュして1回リトライ（無限再帰防止）
    - モジュールレベルで id_token キャッシュ（ページネーション間で共有）
    - 取得時の fetched_at を UTC で記録（Look-ahead bias 対策）
    - DuckDB への保存は冪等（INSERT ... ON CONFLICT DO UPDATE）
  - 公開関数:
    - get_id_token(refresh_token=None)
    - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
    - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得から raw_news への冪等保存・銘柄紐付けを実装。
  - セキュリティ・堅牢性の考慮:
    - defusedxml を使用して XML Bomb 等を防止
    - SSRF 対策:
      - リダイレクト時にスキーム・ホストを検査するカスタム HTTPRedirectHandler を導入
      - 初回 URL および最終 URL のホストがプライベート/ループバック/リンクローカルでないことを検査
    - URL スキームは http/https のみ許可
    - レスポンス最大サイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）
    - トラッキングパラメータ（utm_*, fbclid 等）の除去と URL 正規化
  - データ処理:
    - 記事IDは正規化URLの SHA-256（先頭32文字）で生成して冪等性を確保
    - テキスト前処理（URL除去、空白正規化）
    - raw_news へのバルク INSERT（チャンクサイズ制御、INSERT ... RETURNING で新規挿入IDを取得）
    - news_symbols（記事⇔銘柄コード）を一括保存する内部ユーティリティ
    - 銘柄コード抽出: 4桁数字パターンを検出し、既知銘柄集合でフィルタ（重複除去）
  - 公開関数:
    - fetch_rss(url, source, timeout=30)
    - save_raw_news(conn, articles) -> 新規挿入した記事IDリスト
    - save_news_symbols(conn, news_id, codes)
    - run_news_collection(conn, sources=None, known_codes=None, timeout=30) -> sourceごとの新規保存数

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の各レイヤに対応するテーブルを CREATE TABLE IF NOT EXISTS で定義:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な型チェック制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を設定
  - よく使われるクエリ向けインデックスを作成（コード×日付等）
  - init_schema(db_path) によりディレクトリ自動作成・全DDL実行で初期化（冪等）
  - get_connection(db_path) で接続取得（スキーマ初期化は行わない）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新戦略:
    - DB の最終取得日を参照して差分のみ取得
    - デフォルトバックフィル: 最終取得日の数日前から再取得して API の後出し修正を吸収（デフォルト backfill_days=3）
    - 日付範囲や最小データ開始日（_MIN_DATA_DATE = 2017-01-01）を考慮
  - 市場カレンダー先読み: _CALENDAR_LOOKAHEAD_DAYS = 90
  - 品質チェック連携の設計（quality モジュールと連携、重大度があっても収集を続行）
  - ETL 実行結果を表す ETLResult dataclass を導入（品質結果やエラーの集約、has_errors / has_quality_errors プロパティ）
  - DB 存在チェック、最大日付取得ユーティリティを実装

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector において下記のセキュリティ対策を導入:
  - defusedxml を用いた XML パース
  - SSRF 対策（リダイレクト検査・プライベートIP検査）
  - レスポンスサイズ上限の実装（DoS/Gzip bomb 防止）
  - URL スキーム制限（http/https のみ）

### 既知の制限・注意点 (Notes / Known limitations)
- ETL パイプラインは品質チェックの呼び出しを想定しているが、quality モジュールの実装詳細によっては動作が異なる可能性がある（quality.QualityIssue 型との整合性に依存）。
- news_collector の DNS 解決失敗時は保守的に「非プライベート」とみなして進める設計のため、稀に内部向けのホスト判定が通ってしまう可能性がある（安全側のトレードオフ）。
- 現在の ID トークンキャッシュはプロセス/モジュール内キャッシュであり、マルチプロセス環境や分散実行時の共有は行わない。
- 一部のモジュール（execution, strategy, monitoring）はプレースホルダとして存在し、実装が必要。

### 互換性・ブレイキングチェンジ (Breaking Changes)
- 初期リリースのため該当なし。

---

（作成: ソースコード解析に基づく推測による CHANGELOG。必要に応じて実際のコミット履歴やリリース日付を反映してください。）