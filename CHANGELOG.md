# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

全ての公開バージョンはセマンティックバージョニングに準拠します。

## [0.1.0] - 2026-03-17

### Added
- 初期リリース。パッケージ名: `kabusys`。日本株自動売買システムの基盤的コンポーネントを実装。
- パッケージ初期化:
  - src/kabusys/__init__.py にてバージョン `0.1.0` と公開サブパッケージ（data, strategy, execution, monitoring）を定義。
- 環境設定管理（src/kabusys/config.py）:
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用フック）。
  - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、インラインコメント等を考慮）。
  - 必須設定取得ヘルパ `_require()` と Settings クラスを提供。J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルの検証を行うプロパティを実装。
- J-Quants クライアント（src/kabusys/data/jquants_client.py）:
  - J-Quants API からのデータ取得機能を実装（株価日足 / 財務（四半期）/ マーケットカレンダー）。
  - レート制限対応（固定間隔スロットリング、デフォルト 120 req/min）。
  - 冪等性を考慮した DuckDB 保存関数（ON CONFLICT DO UPDATE）を提供（save_daily_quotes, save_financial_statements, save_market_calendar）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx のリトライ）や 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装。
  - ページネーション対応（pagination_key を利用）とモジュールレベルの ID トークンキャッシュ。
  - データ取得時の fetched_at（UTC）記録により look-ahead bias を追跡可能に設計。
  - 型変換ユーティリティ（_to_float, _to_int）を追加（空文字や不正値への寛容性を確保）。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）:
  - RSS フィードからの記事収集機能を実装（デフォルト: Yahoo Finance のビジネス RSS）。
  - 記事IDは正規化した URL の SHA-256（先頭32文字）を使用し冪等性を保証。
  - URL 正規化でトラッキングパラメータ（utm_* 等）を除去、クエリのソート、フラグメント削除を実施。
  - XML パースに defusedxml を利用し、XML-based 攻撃対策を実装。
  - SSRF 対策:
    - fetch 時にスキーム検証（http/https のみ許可）。
    - 初回リクエスト前とリダイレクト先のホストがプライベートアドレスでないか検証（DNS で A/AAAA を確認）。
    - リダイレクト時にスキーム/ホスト検査を行うカスタムリダイレクトハンドラを導入。
  - レスポンスサイズ制限（最大 10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - テキスト前処理（URL 除去、空白正規化）と銘柄コード抽出（4桁数字、既知コードフィルタ）。
  - DB 保存関数:
    - raw_news に対するチャンク分割バルク INSERT（ON CONFLICT DO NOTHING）および INSERT ... RETURNING による新規挿入IDの取得。
    - news_symbols（記事と銘柄紐付け）を 1 トランザクションでバルク保存する内部機能を実装。
  - テスト用設計:
    - _urlopen をオーバーライド/モックできる設計によりテスト容易性を確保。
- データベーススキーマ（src/kabusys/data/schema.py）:
  - DuckDB 用スキーマ定義を追加（Raw / Processed / Feature / Execution 層に対応）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを定義。
  - features, ai_scores といった Feature 層、signals, signal_queue, orders, trades, positions 等の Execution 層を定義。
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与。
  - パフォーマンスを考慮したインデックスを複数定義。
  - init_schema(db_path) でディレクトリ作成からテーブル作成まで一括初期化する関数、get_connection() を提供。
- ETL パイプライン（src/kabusys/data/pipeline.py）:
  - ETL 実行結果を表す ETLResult dataclass を実装（品質問題・エラーの集約、シリアライズ用 to_dict）。
  - DB の最終取得日を取得するユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 営業日判定補助（_adjust_to_trading_day）を実装。
  - run_prices_etl の骨子を追加（差分更新・バックフィル機能、id_token 注入対応）。※このリリースでは関数末尾が未完（戻り値の組み立て部分に切れているファイル断片あり）。
- その他:
  - 空のパッケージ初期化ファイルを各サブパッケージに追加（execution, strategy, data の __init__.py）。

### Security
- ニュース収集時の SSRF 対策を実装（スキーム検証、プライベートIPブロック、リダイレクト先検査）。
- XML 処理に defusedxml を使用して XML Bomb や外部エンティティ攻撃を防止。
- HTTP レスポンスの最大読み取りサイズを 10MB に制限し、メモリ DoS / Gzip bomb を軽減。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Notes / Known limitations
- run_prices_etl のソース末尾にて戻り値のタプル組み立てが途中で切れている箇所が確認されます（コード断片のため、実際の戻り値の最終整形や他 ETL ジョブ実装は今後の課題）。
- ETL の品質チェック（quality モジュール参照）は別モジュールに依存しており、本リリースでは pipeline 側からの品質チェック結果の取り扱いのみ実装。
- strategy や execution、monitoring の具体的な実装はこのリリースでは未提供。これらの拡張は今後のリリースで追加予定。

---

今後のリリースで予定している改善例:
- run_prices_etl の完結・その他 ETL ジョブ（financials, calendar）の統合。
- strategy 層の具体的なシグナル生成ロジックの実装。
- execution 層の kabuAPI 連携（発注/約定処理）実装。
- モニタリング・アラート（Slack 経由）機能の追加。
- 単体テスト・統合テストの充実と CI 設定。

もし changelog に追加してほしい観点（例えば詳細な設計の追記やコード片ごとの差分表記）があれば教えてください。