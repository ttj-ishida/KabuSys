# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録します。  
このファイルはリリースノートとして、ユーザー・開発者向けに主要な追加機能、修正、セキュリティ関連の注意点をまとめたものです。

※以下はリポジトリ内のソースコードから推測して作成した初期リリースの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-17

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境設定モジュール (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート探索（.git または pyproject.toml を基準）により CWD に依存せず .env を検出。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサを実装（export プレフィックス、シングル／ダブルクォート対応、コメント処理、エスケープシーケンス処理）。
  - 必須設定取得用ヘルパー `_require` と Settings クラスを提供。主な設定項目:
    - J-Quants: JQUANTS_REFRESH_TOKEN
    - kabuステーション: KABU_API_PASSWORD, KABU_API_BASE_URL
    - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス: DUCKDB_PATH, SQLITE_PATH
    - 実行環境判定: KABUSYS_ENV（development / paper_trading / live）
    - ログレベル: LOG_LEVEL（検証済み）

- J-Quants API クライアント (kabusys.data.jquants_client)
  - OHLCV（日足）、四半期財務データ、JPX マーケットカレンダー取得機能を実装。
  - レート制限遵守のための固定間隔スロットリング実装（120 req/min）。
  - 再試行（指数バックオフ）ロジックを実装（最大 3 回、408/429/5xx をリトライ対象）。
  - 401 受信時はリフレッシュトークンから自動で id_token を更新して1回リトライ。
  - ページネーション対応（pagination_key の取り扱い）。
  - データ取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を回避可能に設計。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等性を確保（ON CONFLICT DO UPDATE）。
  - 型変換ユーティリティ（_to_float / _to_int）を実装して不正値を安全に扱う。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news テーブルへ保存する ETL 機能を実装。
  - セキュリティ対策と堅牢性:
    - defusedxml による XML パース（XML Bomb 等を防止）。
    - リダイレクト先のスキーム検証およびプライベートIP拒否（SSRF 対策）。
    - 最終応答サイズチェックおよび MAX_RESPONSE_BYTES 制限（10MB）。gzip 解凍後もサイズ検査（Gzip bomb 対策）。
    - 許可スキームは http/https のみ。
  - 記事IDは正規化された URL の SHA-256（先頭32文字）で生成し冪等性を担保。トラッキングパラメータ（utm_* 等）を除去して正規化。
  - テキスト前処理（URL 除去、空白正規化）。
  - DuckDB へはトランザクションでチャンク挿入し、INSERT ... RETURNING により実際に挿入された ID を返す（save_raw_news、save_news_symbols、_save_news_symbols_bulk）。
  - 銘柄コード抽出ユーティリティ（4桁数字パターン + known_codes フィルタ）。
  - 統合収集ジョブ run_news_collection を提供（ソースごとに個別エラーハンドリング、銘柄紐付けの一括挿入）。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）および Execution レイヤの DDL を実装。
  - 主なテーブル：
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature 層: features, ai_scores
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種チェック制約（NOT NULL / CHECK）や外部キーを付与。
  - よく使われるクエリ向けにインデックスを定義。
  - init_schema(db_path) でディレクトリ作成→スキーマ作成→接続を返す。get_connection で既存 DB に接続可能。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新を行う ETL 設計に基づくモジュールを実装。
  - ETLResult データクラスにより ETL の結果（取得数、保存数、品質問題、エラー）を構造化して返却可能。
  - 市場カレンダーの先読みや差分更新ロジック（最終取得日を基に date_from を計算、デフォルトバックフィル日数 = 3）を実装。
  - テーブル存在チェック、最大日付取得ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 個別 ETL ジョブの骨格（例: run_prices_etl）を実装。差分取得・保存を行うフローを提供。

- パッケージ構成（placeholder）
  - モジュール群のエクスポート: data, strategy, execution, monitoring（strategy と execution の __init__ はプレースホルダとして存在）。

Security
- ニュース収集における SSRF 対策、XML インジェクション対策、レスポンスサイズ制限などセキュリティ観点の実装を導入。

Notes / Implementation details
- J-Quants クライアントは API レート・エラー耐性・トークン再発行を考慮しており、実運用を想定した堅牢性を重視している。
- DuckDB を永続ストレージとして使う設計で、ETL は冪等操作（ON CONFLICT）を前提にしているため再実行耐性がある。
- NewsCollector は記事の重複防止（ID による）・銘柄抽出・トランザクションによる一貫性を意識している。
- 環境変数ロードは OS 環境変数を保護（.env.local による上書き挙動も制御）するため、テスト時や CI での利用を想定した設計がなされている。

Fixed
- 初期リリースのため該当なし。

Changed
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- RSS/HTTP フェッチ周りでの SSRF・Gzip Bomb・XML Attack への対策を導入（defusedxml、プライベートIP拒否、サイズ上限、リダイレクト前検査など）。

---

この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートとして運用する際は、コミット履歴やリリース方針に合わせて追記・修正してください。