# Changelog

すべての重要な変更は Keep a Changelog の仕様に従って記載します。  
このファイルは、コードベースの現状（提供されたソース）から推測して作成した変更履歴です。

## [Unreleased]
- 既知の未完了・注意点
  - ETL パイプライン（kabusys.data.pipeline）の run_prices_etl の末尾が途中で切れているため、戻り値の組み立てやさらに続く ETL 処理（financials / calendar の ETL 呼び出しや品質チェック集約など）が未完了に見えます。実運用前に該当関数の実装完了・テストを推奨します。

---

## [0.1.0] - 2026-03-17
初回公開リリース。日本株自動売買システム「KabuSys」のコア基盤を実装。

### Added
- パッケージ基礎
  - パッケージエントリポイント（src/kabusys/__init__.py）を追加し、バージョンを `0.1.0` に設定。
  - モジュール構成として data, strategy, execution, monitoring を公開。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサ（export 形式、クォート処理、インラインコメント処理に対応）を実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、J-Quants / kabu ステーション / Slack / DB パス / 実行環境（development/paper_trading/live）等の取得・検証プロパティを提供。
  - 一部設定値に検証ロジック（許容値チェック、デフォルト値、Path 変換）を実装。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API クライアントを実装。株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数を提供。
  - レート制限対策（固定間隔スロットリング）を実装（120 req/min）。
  - リトライ戦略（指数バックオフ、最大3回）を実装。HTTP 429 の Retry-After ヘッダ優先対応、408/429/5xx を再試行対象に。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装。トークンはモジュールレベルでキャッシュ。
  - get_id_token 関数（リフレッシュトークンから id_token を取得）を実装。
  - DuckDB へ保存する save_* 関数を実装（raw_prices / raw_financials / market_calendar）。ON CONFLICT DO UPDATE により冪等保存を実現。
  - データ整形ユーティリティ（数値変換の安全処理 _to_float / _to_int）を実装。
  - 取得時刻 fetched_at を UTC ISO8601 形式で記録し、Look-ahead Bias トレーサビリティに配慮。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事収集を行う fetch_rss / run_news_collection を実装。
  - セキュリティ対策:
    - defusedxml を利用した XML パースで XML Bomb 等を防止。
    - SSRF 対策としてリダイレクト時にスキーム検査・ホストがプライベートアドレスかどうか検査する専用ハンドラを実装。
    - URL スキームは http/https のみ許可。プライベート IP / ループバック等へのアクセスを拒否。
    - レスポンス受信に上限（MAX_RESPONSE_BYTES=10MB）を設け、受信超過や gzip 解凍後のサイズ超過を検出。
  - URL 正規化・トラッキングパラメータ除去（utm_* 等）を実装し、正規化 URL から SHA-256 の先頭32文字を記事IDとして生成（冪等性確保）。
  - テキスト前処理（URL除去、空白正規化）を実装。
  - DuckDB への保存:
    - raw_news テーブルへのチャンク単位のトランザクション挿入（INSERT ... ON CONFLICT DO NOTHING RETURNING id）で新規挿入IDを正確に取得。
    - news_symbols（記事と銘柄の紐付け）への一括挿入関数を実装（トランザクション、ON CONFLICT DO NOTHING、INSERT ... RETURNING を使用）。
  - 銘柄コード抽出ロジック（4桁数字候補を known_codes と照合して抽出）を実装。
  - デフォルト RSS ソース（Yahoo Finance ビジネスカテゴリの RSS）を定義。

- データスキーマ（src/kabusys/data/schema.py）
  - DuckDB 用スキーマを定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブルと、prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed テーブルを実装。
  - features / ai_scores 等 Feature 層テーブルを定義。
  - signals / signal_queue / orders / trades / positions / portfolio_performance など Execution 層のスキーマを実装。
  - 代表的クエリ向けのインデックス群を作成。
  - init_schema(db_path) によりディレクトリ作成→全DDL実行→接続を返すユーティリティを実装。get_connection() で既存DB接続を返す。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL の設計に基づくユーティリティ群を実装。
  - ETLResult dataclass を実装（処理概要・品質問題・エラーの集約、辞書化ユーティリティあり）。
  - 差分更新のためのヘルパー（テーブル存在確認、最終取得日の取得、営業日調整）を実装。
  - run_prices_etl を実装（差分取得ロジック、バックフィル日数の指定、J-Quants クライアント呼び出し、保存）。※（注）ファイル末尾の断片的な記述から、続きのロジックが未完に見えるため要確認。

### Changed
- 初回リリースのため過去バージョンからの変更履歴はなし。

### Fixed
- 初回リリースのため過去バージョンからの修正はなし。

### Security
- ニュース収集モジュールで SSRF 対策を実装（リダイレクト先検査、プライベートIPブロック、スキーム検査）。
- XML のパースに defusedxml を使用し安全対策を強化。
- .env 読み込みで OS 環境変数を保護する protected キーを扱い、上書き制御を実装。
- HTTP レスポンスサイズ制限および gzip 解凍後サイズチェックで DoS 向けリスクを低減。
- J-Quants API クライアントでトークン管理とリフレッシュのループ回避（allow_refresh フラグ）を実装。

---

脚注・補足
- この CHANGELOG は提供されたソースコードの内容から推測して作成した報告です。実際のリリースノートや運用ノートはプロジェクトのリリースプロセスに従って調整してください。
- 現在のソースの一部（特に pipeline の末尾）が途中で切れているように見えるため、ETL の最終的なフローやエラーハンドリングの完全性は実運用前に確認してください。