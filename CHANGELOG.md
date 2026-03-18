# Changelog

すべての変更点は Keep a Changelog の形式に従って記載しています。重要な設計方針や既知の注意点も併記しています。

## [Unreleased]

## [0.1.0] - 2026-03-18
最初の公開リリース。本リリースでは日本株自動売買システムの土台となる以下の主要機能群を追加しました。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化（バージョン 0.1.0、公開モジュール: data, strategy, execution, monitoring）。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード実装。
    - プロジェクトルート特定: __file__ を起点に .git または pyproject.toml を探索。
    - OS 環境変数の優先度: OS > .env.local > .env。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装（export 構文、クォート、インラインコメント、トラッキング処理などに対応）。
  - Settings クラスを提供し、必須環境変数の取得や検証をサポート:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック。
    - パス設定 (duckdb/sqlite) を Path として返すユーティリティ。
    - KABUSYS_ENV の値検証 (development / paper_trading / live) と is_live/is_paper/is_dev ヘルパー。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

- データ取得 / 保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを実装:
    - 固定間隔スロットリング (_RateLimiter) によるレート制限遵守（デフォルト 120 req/min）。
    - 冪等的なページネーション処理。
    - リトライ・指数バックオフ (最大 3 回)、HTTP 408/429/5xx に対するリトライ処理。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
    - JSON デコード時のエラーハンドリング。
  - 認証ヘルパー get_id_token を実装（settings.jquants_refresh_token を既定で使用）。
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装（ページネーション対応）。
  - DuckDB へ冪等保存する保存関数を実装:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
  - 型変換ユーティリティ _to_float / _to_int を追加（安全なパースと不正値の扱い）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news / news_symbols に保存する一連処理を実装。
  - セキュリティ対策:
    - defusedxml を利用して XML 関連の脅威を緩和。
    - SSRF 対策: リダイレクト時にスキーム/ホスト検証、初回ホスト検証、プライベート IP 判定。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - トラッキングパラメータ除去（utm_ 等）による URL 正規化と記事ID（SHA-256 先頭32文字）生成で冪等性を担保。
    - 不正なリンクや不正スキームのログ警告とスキップ。
  - フィード取得(fetch_rss) の堅牢化:
    - HTTP ヘッダで gzip を受け付け、gzip 解凍処理を行う。
    - XML パース失敗時は warning を出力して空リストを返す。
    - content:encoded の優先利用、pubDate の RFC パースと UTC への正規化。
  - DB 保存関数:
    - save_raw_news: INSERT ... RETURNING id を使い、実際に挿入された記事IDのリストを返却。チャンク化・1トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンク化して挿入。INSERT ... RETURNING を用いて実挿入数を取得。
  - テキスト前処理および銘柄コード抽出:
    - preprocess_text: URL 除去・空白正規化・前後トリム。
    - extract_stock_codes: 正規表現で 4 桁銘柄コード抽出、known_codes によるフィルタリングと重複除去。

- 研究 (Research) モジュール (src/kabusys/research/*.py)
  - 特徴量探索 (feature_exploration.py):
    - calc_forward_returns: 指定日から将来リターン（デフォルト [1,5,21]）をまとめて DuckDB で取得。
    - calc_ic: Spearman（ランク相関）による IC 計算、データ不足時は None を返却。
    - rank: 同順位を平均ランクとして扱うランク化ユーティリティ（丸めで ties を安定検出）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - すべて標準ライブラリのみで実装（pandas 未使用）し、prices_daily テーブルのみ参照する設計。
  - ファクター計算 (factor_research.py):
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200 日移動平均乖離率 (ma200_dev) を計算。データ不足は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金 (avg_turnover)、出来高比 (volume_ratio) を計算。
    - calc_value: raw_financials から最新の財務指標を取得して PER/ROE を計算（EPS0/欠損時は None）。
    - DuckDB を SQL とウィンドウ関数で活用する実装。prices_daily/raw_financials のみ参照。
  - research パッケージの __all__ を整理して主要関数を公開。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw レイヤーの DDL を追加:
    - raw_prices, raw_financials, raw_news, raw_executions（raw_executions の定義はファイル末尾で続きあり）。
  - テーブルの CHECK 制約や PRIMARY KEY を設定し、データ整合性を向上。

### 修正 (Changed)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### セキュリティ (Security)
- news_collector にて複数の SSRF 対策を実装（リダイレクト検査、プライベートIP判定、スキーム検証）。
- XML パースに defusedxml を利用し XML 関連の攻撃を低減。
- 外部 API への呼び出しはレートリミットとリトライ制御を導入。

### 既知の制約・注意点 (Known issues / Notes)
- DuckDB のスキーマ（prices_daily, raw_prices, raw_financials, market_calendar, raw_news, news_symbols 等）が事前に存在することが前提です。schema モジュールを利用して初期化してください。
- research モジュールは外部ライブラリ（pandas, numpy 等）に依存しない実装を行っていますが、大規模データに対するパフォーマンス評価は今後の課題です。
- jquants_client の _request は urllib を用いた同期的実装です。高頻度並列取得を行う場合は設計見直し（非同期化や共有 RateLimiter の考慮）が必要です。
- news_collector のホストプライベート判定は DNS 解決失敗時に安全側（非プライベート）として扱います。セキュリティ要件によってはより厳格な設定を検討してください。
- raw_executions テーブル定義は file 内容の末尾で切れているため、完全なスキーマ確認が必要です。

### マイグレーション / 設定例 (Migration / Configuration)
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env ロード: プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env を読み込みます。CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能。
- DuckDB のデフォルトパス: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可能）。
- sqlite のデフォルトパス: data/monitoring.db（環境変数 SQLITE_PATH で上書き可能）。

---

貢献者や将来的な追加予定（例: 発注実行ロジック、監視/モニタリングの実装、戦略モジュールの詳細実装）は今後のリリースで追記します。必要であればリリースノートの文言をより詳細に調整します。