# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（このスナップショットはリリース準備中の状態をコードベースから推測して生成しています。実際のリリース時にはここに今後の変更を記載してください。）

---

## [0.1.0] - 2026-03-17

初回リリース（推定） — KabuSys の基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0
  - メインモジュール群: data, strategy, execution, monitoring（strategy/execution/monitoring は初期プレースホルダとして存在）

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml を基準）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env パースの堅牢化:
    - export プレフィックス対応
    - シングル/ダブルクォート内のエスケープ処理
    - コメントの扱い（インラインコメントの考慮）
  - OS 環境変数を保護する protected オプション（.env.local による上書き制御）
  - Settings クラスによる設定取得 API:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（Path に展開）
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API レート制御（_RateLimiter）: 120 req/min の固定間隔スロットリングを実装
  - リクエストの共通処理:
    - 再試行ロジック（指数バックオフ、最大3回）
    - 408/429/5xx に対するリトライ
    - 429 の Retry-After ヘッダ尊重
    - JSON デコードエラーハンドリング
  - トークン処理:
    - get_id_token: リフレッシュトークン → idToken 取得（POST）
    - トークンキャッシュと 401 での自動リフレッシュ（1回のみ再試行）
  - データ取得関数:
    - fetch_daily_quotes（ページネーション対応）
    - fetch_financial_statements（ページネーション対応）
    - fetch_market_calendar
    - 取得したレコード数のログ出力
  - DuckDB 保存関数（冪等性確保）:
    - save_daily_quotes: raw_prices に INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials に INSERT ... ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar に INSERT ... ON CONFLICT DO UPDATE
    - PK 欠損行のスキップと警告ログ
  - ユーティリティ変換:
    - _to_float / _to_int（変換ルールを厳密に定義）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集フロー:
    - RSS 取得 → テキスト前処理（URL 除去・空白正規化）→ raw_news に冪等保存 → 銘柄紐付け
  - セキュリティ / 安全性対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - ホストのプライベートアドレス検査（IP/DNS 解決を用いて private/loopback/link-local/multicast を拒否）
      - リダイレクト時にも検査を行うカスタム RedirectHandler 実装
    - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）
    - gzip 解凍後のサイズ検査（Gzip bomb 対策）
  - URL 正規化:
    - トラッキングパラメータ（utm_, fbclid, gclid, ref_, _ga 等）除去、クエリキーソート、フラグメント削除
    - その後 SHA-256 の先頭32文字を記事IDに利用して冪等性を保証
  - RSS パースの堅牢化:
    - content:encoded の名前空間考慮、fallback ロジック、pubDate のパース（UTC へ正規化）
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id（チャンク分割、1トランザクション）
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへ一括挿入（重複除去、RETURNING で実挿入数を取得）
  - 銘柄抽出:
    - 4桁数字正規表現による候補抽出と known_codes フィルタリング（重複排除）
  - run_news_collection: 複数ソースの収集を行い、ソース単位で障害を隔離して継続処理

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Data Platform 設計に基づく多層スキーマ:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対する型・チェック制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY 等）を定義
  - 代表的なインデックスを作成（頻出クエリに備えたインデックス）
  - init_schema(db_path): ディレクトリ自動作成、DDL の冪等実行でスキーマ初期化
  - get_connection(db_path): 既存 DB への接続取得（スキーマ初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計方針を実装:
    - 差分更新（DB最終取得日を元に date_from を自動算出）
    - backfill_days による後出し修正吸収
    - 品質チェック（quality モジュールとの連携を想定）
  - ETLResult データクラス:
    - 実行メタ情報（取得数、保存数、品質問題、エラーリスト）を格納
    - has_errors / has_quality_errors 等のプロパティ、辞書化機能（監査ログ用）
  - DB ユーティリティ:
    - _table_exists / _get_max_date / get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _adjust_to_trading_day: 非営業日調整（market_calendar を参照）
  - run_prices_etl の骨子:
    - date_from 自動算出（最小日付 _MIN_DATA_DATE = 2017-01-01 を考慮）
    - jq.fetch_daily_quotes → jq.save_daily_quotes を用いた差分取得と保存

### Security
- RSS パーサに defusedxml を利用して XML 関連の脆弱性に対処
- ニュース収集で SSRF 対策を実装（スキーム検証、プライベートアドレス検出、リダイレクト検査）
- レスポンスの最大バイト数制限でメモリ DoS を軽減
- .env 読み込みにおいて OS 環境変数を保護（.env.local による上書き制御）

### Notes / Known issues（コードから推測される注意点）
- strategy / execution / monitoring モジュールはパッケージ内に存在するが、実装が空またはプレースホルダの状態です。発注ロジックや戦略の具現化は未実装の可能性が高いです。
- pipeline.run_prices_etl は差分取得の実装方針を有しますが、（提供されたコードスニペットの末尾が不完全な形になっており）戻り値や後続処理の最終整備が必要な箇所が見受けられます。実運用前に完全な戻り値・エラーハンドリング・品質チェック連携の確認を推奨します。
- テスト用に環境変数ロードを抑止するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）が用意されていますが、本番デプロイ時の取り扱いポリシー（シークレット管理）については別途整備が必要です。
- J-Quants API 周りはネットワーク／認証まわりを多重に扱っているため、実際の API レート制限やエラーレスポンスに即した運用・監視が必要です。

---

過去の変更履歴や詳細はリポジトリのコミットログや設計ドキュメント（DataPlatform.md, DataSchema.md 等）を参照してください。必要であれば上記の各項目を更に分割して詳細なリリースノート（例: 小さな修正ごとのセクション）に展開します。