# CHANGELOG

このプロジェクトは Keep a Changelog のガイドラインに従って変更履歴を記録します。  
なお以下は与えられたソースコードから推測して作成した初回リリース向けの変更履歴です。

全体方針:
- 重要な変更点・追加機能をモジュール別に列挙しています。
- リリース日にはこのドキュメント作成日 (2026-03-17) を設定しています。実際のリリース日時に合わせて更新してください。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-17
初回公開リリース。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージの基本骨組みを追加。バージョンは `0.1.0`。
  - パッケージ外部公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - プロジェクトルートの検出は .git または pyproject.toml を探索して行う（CWD に依存しない実装）。
  - .env ファイルパーサを実装（コメント行、export プレフィックス、クォート、エスケープ、インラインコメント等に対応）。
  - Settings クラスを提供し、必要な環境変数をプロパティとして取得:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL（デフォルト: localhost）、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV（validation）、LOG_LEVEL（validation）など。
  - 環境変数未設定時の明確なエラーメッセージを用意。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants からのデータ取得クライアントを実装:
    - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得 API のラッパーを実装（ページネーション対応）。
  - レート制御 (固定間隔スロットリング) を実装（120 req/min に準拠）。
  - 再試行ロジック（指数バックオフ、最大 3 回、ステータスコード 408/429 および 5xx を再試行）を搭載。
  - 401 応答時はリフレッシュトークンでトークン更新して 1 回だけ自動リトライする仕組みを実装（無限再帰回避）。
  - ID トークンのモジュールレベルキャッシュを提供し、ページネーション間で共有。
  - DuckDB へ保存する save_* 関数を実装（raw_prices, raw_financials, market_calendar、ON CONFLICT DO UPDATE により冪等性を確保）。
  - レスポンスの JSON デコード失敗時の明確なエラー報告やログ出力を実装。
  - 型安全な数値変換ユーティリティ（_to_float, _to_int）を実装。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news / news_symbols に保存する収集器を実装。
  - セキュリティ対策と堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 等への対処）。
    - SSRF 対策: リダイレクトハンドラでスキームとプライベートホストを検査、事前にホストのプライベート判定を実施。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）をチェックし、gzip 解凍後も検証。
    - トラッキングパラメータ除去、URL 正規化。
  - 記事ID は正規化後 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
  - テキスト前処理関数 (URL 除去、空白正規化) を実装。
  - DuckDB への保存はトランザクション単位でバルク挿入し、INSERT ... RETURNING で挿入された ID を正確に取得する実装。
  - 銘柄コード抽出機能（4桁数字パターン + known_codes によるフィルタ）を実装。
  - run_news_collection により複数ソースの収集を一括実行（ソース単位での個別エラーハンドリング、銘柄紐付けの一括保存）。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用のスキーマ初期化モジュールを追加。
  - Raw / Processed / Feature / Execution の多層テーブル設計を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 各種 CHECK 制約、PRIMARY KEY、FOREIGN KEY を定義してデータ整合性を担保。
  - 頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成→全テーブル/インデックス作成を行い、DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL 実行結果を表す ETLResult dataclass を実装（品質検査結果やエラー集計を保持）。
  - 差分更新用ユーティリティ（テーブル存在確認、最大日付取得、営業日調整）を実装。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - run_prices_etl を実装（差分更新ロジック、バックフィル日数指定、J-Quants クライアント呼び出し、保存）。差分更新のデフォルトバックフィルは 3 日。
  - ETL は品質チェック（quality モジュール想定）と組み合わせる設計。テスト容易性のため id_token の注入を可能にしている。

### 変更 (Changed)
- （初回リリースのため過去からの変更はなし）

### 修正 (Fixed)
- （初回リリースのためなし）

### セキュリティ (Security)
- RSS パーサと HTTP クライアント周りで複数のセキュリティ対策を導入:
  - defusedxml の採用、SSRF 対策（プライベートIP/ホストのチェック、リダイレクト検査）、レスポンスサイズ上限、許可スキーム制限等を実装。

### 既知の注意点 / 今後の改善案
- pipeline.run_prices_etl の戻り値がファイルの途中で切れている（与えられたコードスニペットでは return の記述が未完の可能性）。実際のリリースでは正しい (fetched, saved) タプルを返すことを確認してください。
- settings の必須環境変数（トークンや Slack 設定など）が未設定だと起動時に ValueError が発生します。デプロイ前に .env/.env.local を整備してください。
- get_id_token は refresh token 取得に依存するため、適切なリフレッシュトークン管理とエラーハンドリング（失敗時のリトライ方針）が必要です。
- DuckDB への INSERT 文は逐次プレースホルダを文字列連結で作成しているため、非常に大きなチャンク時の SQL 長に注意（チャンクサイズは _INSERT_CHUNK_SIZE = 1000 に設定）。
- news_collector は外部ネットワークや RSS フィードに依存するため、運用時はタイムアウト・再試行・監視の設計が必要。

---

この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと照合して必要に応じて修正・追記してください。