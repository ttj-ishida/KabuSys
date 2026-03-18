# Changelog

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [Unreleased]
- 現時点の開発中の変更点はここに記載してください。

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買システムの骨格となる各種モジュールを実装しました。主にデータ取得・保存・ETLの基盤機能と設定管理、ニュース収集の安全対策を提供します。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの基本構造を追加（__version__ = 0.1.0、公開モジュール指定）。
- 設定管理 (kabusys.config)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする機能を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ実装：コメント、export 形式、クォート内のエスケープ処理、行中コメントの扱いに対応。
  - Settings クラスを提供：J-Quants, kabuAPI, Slack, データベースパス、環境（development/paper_trading/live）やログレベルのバリデーションを実装。
  - 必須環境変数未設定時に明確なエラーメッセージを送出する _require() を実装。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - get_id_token によるリフレッシュトークンからの ID トークン取得（POST）。
  - レート制限 (120 req/min) を守る固定間隔スロットリング実装 (_RateLimiter)。
  - リトライロジック（指数バックオフ、最大3回）。408/429/5xx にリトライ。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時はトークンを自動で再取得して 1 回だけリトライする仕組みを実装。
  - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT DO UPDATE を使用）。
  - データ型変換ユーティリティ (_to_float, _to_int) を追加。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を取得し raw_news に保存する処理を実装（fetch_rss, save_raw_news, save_news_symbols 等）。
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
  - URL 正規化で utm_* 等トラッキングパラメータ除去、クエリソート、フラグメント除去を実施。
  - SSRF 対策：取得前にホストのプライベート/ループバック/リンクローカル判定を行い、リダイレクト時にも検証するカスタムハンドラを実装。
  - defusedxml を用いた XML パース（XML Bomb 等への対策）。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）や gzip 解凍後のサイズ検査を実装（メモリDoS 対策）。
  - コンテンツ前処理（URL除去、空白正規化）と、記事中の 4 桁銘柄コード抽出機能を実装（extract_stock_codes）。
  - DB への挿入はチャンク化してトランザクションで実行、INSERT ... RETURNING を利用して実際に挿入された件数/ID を正確に取得。
  - デフォルト RSS ソース（yahoo_finance）を追加。
  - _urlopen を関数化してテスト時にモック可能に設計。
- DuckDB スキーマ管理 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層のテーブル定義を追加（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義し、整合性を強化。
  - 頻出クエリ用のインデックス定義を追加。
  - init_schema(db_path) によりディレクトリ自動作成と DDL 実行でスキーマ初期化、get_connection() で既存 DB へ接続可能。
- ETL パイプライン基盤 (kabusys.data.pipeline)
  - 差分更新のためのヘルパ関数（最終取得日の取得, テーブル存在チェック）を実装。
  - 市場カレンダーを考慮した営業日調整関数を実装。
  - run_prices_etl 等の個別 ETL ジョブを開始（差分取得、backfill の考慮、jquants_client の保存関数利用）。
  - ETLResult dataclass を導入し、取得件数・保存件数・品質問題・エラーの集約と to_dict 出力をサポート。
- 空のパッケージ初期化ファイルを追加
  - kabusys.data, kabusys.strategy, kabusys.execution の __init__.py を追加（将来の拡張点）。

### セキュリティ (Security)
- RSS パーサで defusedxml を採用し、XML 攻撃（XML Bomb 等）への対策を実装。
- RSS フェッチで SSRF 防止:
  - ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合は接続を拒否。
  - リダイレクト先のスキームとホストもチェックするカスタム HTTPRedirectHandler 実装。
  - URL スキーム検証で http/https 以外を拒否。
- .env 読み込みの警告や保護（OS 環境変数を protected として上書きを防止）を実装。

### 品質・堅牢性 (Quality)
- J-Quants クライアントで厳格なエラーハンドリングとリトライ/バックオフ戦略を実装。
- DuckDB への保存は可能な限り冪等化（ON CONFLICT）して多重実行耐性を向上。
- ニュース収集でレスポンスサイズ制限、gzip 解凍後の確認、XML パースエラーの安全な扱いを実装。
- ETL レイヤでバックフィル設定（デフォルト3日）により API の後出し修正に対処。

### パフォーマンス (Performance)
- API 呼び出しで固定間隔のレートリミットを実装しレート超過によるエラーを防止。
- news_collector の DB 挿入をチャンク化してオーバーヘッドを削減。

### 既知の問題 (Known issues)
- run_prices_etl 実装は途中（コードベースの抜粋により最後の戻り値/挙動が未完）であり、ETL の統合実行（全体の run_* ワークフローや品質チェックの呼び出し/報告部分）は今後の実装・整備が必要です。
- strategy / execution パッケージは初期プレースホルダ（空 __init__）のみで、実際の売買戦略や発注ロジックは未実装。
- テストカバレッジについてはユニットテスト実装が含まれていないため、モジュール毎の単体テストを追加することを推奨します。

### 変更点に対する注意
- 環境変数名・必須設定（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は Settings によって強制されます。デプロイ時は .env を準備してください（.env.example に従う想定）。
- DuckDB スキーマは init_schema() 実行で作成されます。既存データの移行等が必要な場合は注意してください。

---

（補足）本 CHANGELOG はリポジトリ内の現行ソースコードから機能・設計意図を推測して作成しています。実際の変更履歴（コミット単位・日付・著者）とは異なります。必要に応じてリリースごとの正確な変更履歴に更新してください。