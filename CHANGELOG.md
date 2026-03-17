# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

注: 下記は提供されたコードベースの内容から推測して作成した初期リリースの変更履歴です。

## [0.1.0] - 2026-03-17

### 追加 (Added)
- パッケージの初期リリース。基本モジュールを実装。
  - パッケージメタ情報:
    - `kabusys.__version__ = "0.1.0"`
    - パッケージ公開 API: `data`, `strategy`, `execution`, `monitoring`（strategy/execution は初期スタブ）

- 環境・設定管理 (`kabusys.config`)
  - プロジェクトルート自動検出: `.git` または `pyproject.toml` を基準にパッケージ内からプロジェクトルートを特定。
  - .env 自動読み込み: OS環境変数 > `.env.local` > `.env` の優先順で自動ロード（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
  - .env パーサの強化:
    - `export KEY=val` 形式に対応
    - シングル/ダブルクォートの内部エスケープ処理、インラインコメント処理
    - コメント扱いの判定（# の前が空白/タブの場合のみ）
  - 環境値取得ラッパ (Settings):
    - J-Quants / kabu API / Slack / DB パスなどのプロパティを提供 (`jquants_refresh_token`, `kabu_api_password`, `slack_bot_token`, `slack_channel_id`, `duckdb_path`, `sqlite_path` 等)
    - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーション（許可値を限定）
    - `is_live`, `is_paper`, `is_dev` のユーティリティプロパティ

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API 呼び出しユーティリティ `_request` 実装:
    - レート制御（固定間隔スロットリング）: 120 req/min 制限を守る `_RateLimiter`
    - リトライ機構（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）
    - 401 応答時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有（ページネーション間での共有）
    - JSON デコード失敗の扱いを明示
  - 認証補助関数 `get_id_token`（リフレッシュトークンから idToken を取得）
  - データ取得関数（ページネーション対応）:
    - `fetch_daily_quotes`（株価日足 OHLCV）
    - `fetch_financial_statements`（四半期 BS/PL）
    - `fetch_market_calendar`（JPX カレンダー）
  - DuckDB への保存関数（冪等性を考慮した実装）:
    - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`
    - 各関数は `ON CONFLICT DO UPDATE` により重複/更新を安全に処理
    - レコード保存時に UTC の `fetched_at` を記録し Look-ahead bias を抑止
  - 型変換ユーティリティ `_to_float`, `_to_int`（安全な変換・不正値は `None`）

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィード取得および記事保存機能を実装:
    - デフォルトソース `yahoo_finance` を定義
    - `fetch_rss` による RSS 取得と記事解析（defusedxml を使用した XML パース）
    - 記事前処理: URL 除去、空白正規化 (`preprocess_text`)
    - URL 正規化とトラッキングパラメータ除去 (`_normalize_url`) と SHA-256 ベースの記事 ID 生成（先頭32文字）
  - セキュリティ対策:
    - SSRF 対策: URL スキーム検証（http/https のみ）およびホストがプライベート/ループバック/リンクローカル/マルチキャストでないことを検証（`_is_private_host`）
    - リダイレクト時も検証するカスタムハンドラ `_SSRFBlockRedirectHandler`
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ確認（Gzip bomb 対策）
    - defusedxml による XML 攻撃対策
  - DB 保存機構:
    - `save_raw_news`: チャンク化したバルク `INSERT ... ON CONFLICT DO NOTHING RETURNING id` を用い、実際に挿入された記事IDリストを返す（トランザクションでまとめて処理）
    - `save_news_symbols` / `_save_news_symbols_bulk`: 記事と銘柄コードの紐付けを冪等に保存（ON CONFLICT を使用）
    - チャンクサイズ制御により SQL 長・パラメータ数を制限
  - 銘柄コード抽出:
    - 正規表現で 4 桁数字候補を抽出、与えられた known_codes セットでフィルタリングする `extract_stock_codes`
  - 統合収集ジョブ `run_news_collection`:
    - 複数フィードの独立処理、各ソースのエラーハンドリング（1 ソース失敗でも他は継続）
    - 新規挿入記事に対して銘柄紐付けを一括登録

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - Data Platform の 3 層（Raw / Processed / Feature）＋ Execution レイヤーを想定したテーブル定義を実装
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY, CHECK）を含む DDL を定義
  - 性能考慮のインデックス群を作成
  - `init_schema(db_path)` により DB ファイルの親ディレクトリ作成からテーブル/インデックス作成までを冪等に実行
  - `get_connection(db_path)` で既存 DB への接続を取得（初期化は行わない）

- ETL パイプライン基盤 (`kabusys.data.pipeline`)
  - ETL の設計方針実装の骨子:
    - 差分更新の考え方（最終取得日からの差分取得、backfill による後出し修正吸収）
    - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）
    - ETL 結果を表す `ETLResult` dataclass（品質チェック結果やエラーを含む）
    - DB 存在確認や最大日付取得ユーティリティ
    - 非営業日の調整 `_adjust_to_trading_day`
    - raw_prices / raw_financials / market_calendar の最終取得日取得ヘルパー
    - 差分 ETL の個別ジョブ `run_prices_etl`（date_from の自動算出、バックフィル対応、jquants_client の fetch/save 呼び出し）
  - テストと注入のしやすさを考慮して id_token 注入可能な設計

### セキュリティ (Security)
- RSS/外部 URL 関連で以下のセキュリティ対策を導入:
  - SSRF 対策（スキーム制限、プライベート IP チェック、リダイレクト時の検証）
  - defusedxml による XML 攻撃防止
  - レスポンス最大バイト数制限（メモリ DoS 防止）
  - Gzip 解凍後のサイズ検査（Gzip bomb 対策）

### パフォーマンス (Performance)
- API 呼び出しでレート制御と適切なリトライ/backoff を実装（レートリミット厳守）
- ニュース保存でチャンク化・バルク INSERT を使用し DB オーバーヘッドを削減
- DuckDB スキーマに検索パターンに基づくインデックスを追加

### 信頼性・運用 (Reliability / Operational)
- jquants_client の id_token キャッシュを実装しページネーションや複数呼び出しに対応
- DuckDB への保存は冪等（ON CONFLICT）、公開タイムスタンプで監査性を確保
- ETL の品質チェックフック（quality モジュール参照）を組み込み、問題検出情報を ETLResult に収集
- 設定関連で環境変数不足時に明確なエラーメッセージを出す `_require`

### テスト支援 (Testing)
- `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動 .env ロードを抑止しテスト環境を容易にする機構を提供
- `_urlopen` 等をモック可能に実装してネットワーク依存部の差し替えを容易化
- ETL / API 呼び出しで id_token 注入可能にしてユニットテストを容易化

### 既知の制約・注意点 (Known limitations / Notes)
- quality モジュール参照あり（品質チェックの実体は別実装を想定）。品質チェック結果は ETLResult に格納されるが、quality の具象実装はこのコードスニペットに含まれていない。
- strategy / execution パッケージは初期スタブで、本リリースでは主要なアルゴリズムや発注ロジックは未実装。
- pipeline.run_prices_etl のソースは途中まで提供されている（切れ目がある）；完全なジョブワークフロー実装は今後のリリースで補完予定。

---

今後のリリースでは以下を検討するとよい項目:
- strategy（売買戦略）と execution（発注/約定管理）の実装
- 監視・アラート（monitoring）実装の拡充（Slack 通知など）
- quality モジュールの実装と ETL の自動修復/アラート連携
- より詳細なログ出力・メトリクス（Prometheus 等）連携

---------------------------------------------------------------------
参照: Keep a Changelog (https://keepachangelog.com/ja/)。