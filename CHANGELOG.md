CHANGELOG
=========

すべての変更は Keep a Changelog 規約に従って記載しています。
このプロジェクトはまだ初回リリース (0.1.0) の段階と推測されるため、主に追加された機能群と設計上の意図・既知の注意点をまとめています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ骨組みを追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring

- 環境・設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装
    - ロード順: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）
  - .env パーサ（export プレフィックス、シングル／ダブルクォート、インラインコメント対応）
  - Settings クラスを提供し、下記設定プロパティを環境変数から取得／検証
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV 検証（development / paper_trading / live のみ）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 基本機能: 日次株価（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得関数を実装
  - 認証: リフレッシュトークンから id_token を取得する get_id_token を実装
  - レート制御: 固定間隔スロットリングによる RateLimiter 実装（120 req/min を想定）
  - リトライ: 指数バックオフを用いたリトライロジック（最大3回、408/429/5xx のリトライ扱い）
    - 429 時は Retry-After ヘッダを優先
    - 401 受信時は id_token を自動リフレッシュして1回再試行
  - ページネーション対応（pagination_key を用いた取得ループ）
  - DuckDB への保存 API（冪等性を考慮した ON CONFLICT DO UPDATE を使用）
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ品質のため取得時刻(fetched_at)を UTC で記録
  - 型変換ユーティリティ (_to_float, _to_int)

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する処理を実装
  - 設計上の重要点:
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成（utm_* 等のトラッキングパラメータを除去）
    - defusedxml を使った XML パース（XML Bomb 等への対策）
    - SSRF 対策:
      - リダイレクト先スキーム検証とプライベートアドレス検査（_SSRFBlockRedirectHandler / _is_private_host）
      - 初回 URL および最終 URL 両方を検証
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と Gzip 解凍後の再チェック（Gzip bomb 対策）
    - 不正スキーム（mailto:, file:, javascript: など）の URL を除外
    - テキスト前処理（URL 除去、空白正規化）
    - DB 挿入はチャンク化して1トランザクションで実行、INSERT ... RETURNING を使い新規挿入 ID を取得
    - 銘柄コード抽出ロジック（4桁数字、known_codes によるフィルタリング）
  - デフォルト RSS ソース: Yahoo Finance のビジネスカテゴリ（DEFAULT_RSS_SOURCES）

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - 3 層データ設計に基づくテーブル群を定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な CHECK 制約・PRIMARY KEY・FOREIGN KEY を定義
  - 検索頻度の高いカラムに対するインデックスを定義
  - init_schema(db_path) でディレクトリ作成（必要時）とテーブル／インデックス作成を行い接続を返す
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult dataclass により ETL 実行結果（取得件数、保存件数、品質問題、エラー一覧）を構造化
  - 差分更新のためのユーティリティ:
    - テーブルの最終取得日取得関数 (get_last_price_date, get_last_financial_date, get_last_calendar_date)
    - 非営業日の調整ヘルパー (_adjust_to_trading_day)
  - run_prices_etl 実装（差分取得・backfill 機能・jquants_client 経由の保存）
    - デフォルト backfill_days = 3 （最終取得日の数日前から再取得して API の後出し修正を吸収）
  - ETL 設計の方針文書（差分更新、品質チェックは Fail-Fast にならない等）に準拠した実装

Security
- RSS パーサで defusedxml を使用し XML 関連の脆弱性を緩和
- ニュース収集で SSRF 対策を実装（スキーム検証、プライベートアドレスブロッキング、リダイレクト時の再検証）
- 外部リクエストに対してレスポンスサイズ制限と Gzip 解凍後検証を実施（DoS / Bomb 対策）

Performance & Reliability
- J-Quants API クライアントでレート制御とリトライ（指数バックオフ）を導入
- DuckDB 側の挿入を一括・チャンク化してトランザクションでまとめることで I/O オーバーヘッドを削減
- raw_news / news_symbols の挿入で ON CONFLICT を活用し冪等性を確保

Testing / Extensibility
- 設計上、テスト容易性に配慮:
  - news_collector._urlopen をモックで差し替え可能
  - jquants_client の関数は id_token を注入してテスト可能
  - KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト環境で自動 .env ロードを無効化可能

Known issues / Notes
- run_prices_etl の戻り値が実装末尾において不完全（現状のコードでは "return len(records), " のようにタプルが片方欠けている可能性がある）。実動作時に呼び出し側で期待される (fetched, saved) の形式になっているか確認・修正が必要です。
- 初期バージョンとして多くの機能が実装されているが、運用環境（特に live モード）で利用する前に十分なテストと安全性レビュー（API エラーパス、DB マイグレーション、Slack/実注文周りの安全策など）を推奨します。

Upgrade Notes
- 0.1.0 は初期リリース相当のため、将来的にスキーマ変更や API の振る舞い変更が入る可能性があります。
- DuckDB スキーマを変更する場合は既存データのマイグレーションを検討してください（init_schema は既存テーブルを上書きしませんが、列追加や制約変更が必要なケースがあるため）。

連絡・貢献
- 不具合や改善提案があれば Issue を作成してください。特に ETL の完全性（戻り値や品質チェックの扱い）と execution / strategy 周りの実装（実注文処理）は重要です。

--- 

（注: 本 CHANGELOG は提示されたソースコードの内容から推測して作成したものであり、実際のコミット履歴や開発ノートに基づくものではありません。）