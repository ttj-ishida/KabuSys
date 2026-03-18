KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-18
初期公開リリース。

### 追加
- 全体
  - KabuSys パッケージを初期実装。パッケージバージョンは 0.1.0 に設定。
  - パッケージ公開 API (__all__) に data, strategy, execution, monitoring を定義（strategy、execution は空パッケージのスケルトンを含む）。

- 設定 / 環境変数 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルート検出: __file__ を基点に .git または pyproject.toml を探索してルートを特定（配布後の動作を考慮）。
    - 読み込み順: OS 環境変数 > .env.local > .env。OS 環境変数は既定で保護され、.env による上書きを防止。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化に対応（テスト用）。
  - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート中のエスケープ、インラインコメントの扱い等に対応）。
  - Settings クラスを提供し、プロパティ経由で設定値へアクセス:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID を必須変数として取得（未設定時は ValueError）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値/Path 変換を実装。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の値検証と convenience プロパティ（is_live/is_paper/is_dev）。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - API レート制限 (120 req/min) を守る固定間隔スロットリング（RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx、429 の場合は Retry-After を尊重）。
    - 401 Unauthorized 受信時にリフレッシュトークンから id_token を自動更新して 1 回リトライ（無限再帰防止のため allow_refresh フラグ）。
    - ページネーション対応（pagination_key を用いたループ）、ページ間での id_token キャッシュ共有。
  - データ取得関数を提供:
    - fetch_daily_quotes（株価日足、OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB へ冪等(ON CONFLICT DO UPDATE)に保存する save_* 関数を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - fetched_at を UTC (Z 表記) で記録
    - PK 欠損行はスキップして警告ログ出力
  - 型安全な数値変換ユーティリティ (_to_float, _to_int) を実装。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news/raw_news_symbols に保存するモジュールを実装。
  - セキュリティ・堅牢性:
    - defusedxml を使った XML パース（XML Bomb 等対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、プライベート/ループバック/リンクローカル/マルチキャストアドレス検出によるブロック、リダイレクト時の検査ハンドラを導入。
    - レスポンスサイズ上限チェック（最大 10 MB、gzip 解凍後も検査）でメモリ DoS を防止。
  - 記事 ID は URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）後の SHA-256 ハッシュ先頭 32 文字で生成し冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）、記事内の銘柄コード抽出（4 桁数字、既知銘柄セットとの照合）を実装。
  - DB 保存はチャンク/トランザクションで行い、INSERT ... RETURNING を用いて実際に挿入されたレコード数／ID を正確に取得:
    - save_raw_news（チャンク化して raw_news に保存し、挿入された記事IDのリストを返す）
    - save_news_symbols / _save_news_symbols_bulk（news_symbols への紐付けをバulk 保存）
  - run_news_collection で複数ソースを独立して処理し、1 ソースの失敗で他を継続する設計。

- スキーマ管理 (kabusys.data.schema)
  - DuckDB 用のスキーマを定義（Raw / Processed / Feature / Execution の多層構造）。
  - 各テーブルの DDL、インデックスを定義。
  - init_schema(db_path) で親ディレクトリ作成→DDL 実行→接続を返す（冪等）。
  - get_connection(db_path) を提供（既存 DB へ接続、初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の骨格を実装:
    - ETLResult dataclass（取得数、保存数、品質チェック結果、エラーなどの集計）
    - 差分更新のヘルパー（テーブル存在チェック、最終日取得、営業日に調整）
    - run_prices_etl の実装（差分計算、backfill_days を考慮した再取得、jquants_client との連携で取得→保存）
  - 設計方針として品質チェック（quality モジュール）との連携を想定（重大度を無視せず結果を返す形）。

### セキュリティ
- news_collector において defusedxml、SSRF 防止ロジック、レスポンスサイズ制限を導入。
- config の .env 読み込みでは OS 環境変数を保護（既定で上書きしない）する仕組みを採用。

### 依存（実装からの推定）
- duckdb（データ格納・クエリ）
- defusedxml（RSS XML パースの安全化）
- 標準ライブラリの urllib, gzip, hashlib, ipaddress, socket などを多用

### 既知の制約・注意点
- 初期実装のため、ETL パイプライン周り（例: 品質チェックの実行タイミング・詳細なハンドリング）は今後拡張予定。
- RSS 収集では既知銘柄セットを外部から渡す必要がある（run_news_collection の known_codes 引数）。既知銘柄の入手元は別途準備が必要。
- （開発注記）pipeline 内の処理やログは設計仕様に従った骨格実装です。運用時はスケジューリング、監視、リトライ/障害対応ポリシーの追加を推奨。

### 変更なし（破壊的変更／削除等）
- 初回リリースのため該当なし。

---

今後の予定（例）
- ETL の品質チェックルールの追加と自動アラート化
- strategy / execution モジュールの実装（発注ロジック・kabuステーション連携）
- 単体テスト・統合テストの充実と CI パイプラインの整備

（必要があれば、各モジュール毎により詳細な変更内容・使用例・マイグレーション手順を追記します。）