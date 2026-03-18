CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

Unreleased
----------

- なし

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - src/kabusys パッケージを追加。パッケージメタ情報として __version__ = "0.1.0" を設定。
  - __all__ に data, strategy, execution, monitoring を公開候補として定義（strategy/execution は現状ほぼ空のパッケージ用意）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダ実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - .env/.env.local の優先順制御、既存 OS 環境変数を保護する protected ロジックを実装。
  - export KEY=val 形式やクォート／エスケープ、行末コメントなどを考慮した細かなパーサ実装。
  - 設定アクセス用 Settings クラスを実装（J-Quants / kabu API / Slack / DB パス / 環境名・ログレベル検証など）。
  - テスト等で自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務諸表、マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - 認証: refresh_token から id_token を取得する get_id_token を提供。ID トークンのモジュールローカルキャッシュを実装。
  - HTTP の堅牢化:
    - 固定間隔スロットリングによるレート制限遵守（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx のリトライ対象）。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）を実装。
    - JSON デコード失敗時の明確なエラー報告。
  - DuckDB への保存用 save_* 関数（raw_prices, raw_financials, market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性を保証。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、失敗時は None を返す堅牢な設計。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得と raw_news / news_symbols への保存機能を実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - 設計上の特徴:
    - defusedxml を使った XML パースで XML Bomb 等への防御。
    - SSRF 対策: URL スキーム検証、リダイレクト先のスキーム・ホスト検証、プライベートIP 判定によるブロック。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - URL 正規化とトラッキングパラメータ除去、SHA-256(先頭32文字) を用いた記事ID生成で冪等性を確保。
    - テキスト前処理（URL 除去・空白正規化）。
    - DuckDB へのバルク INSERT はチャンク化してトランザクション内で実行し、INSERT ... RETURNING によって実際に挿入された件数を正確に取得。
    - 銘柄コード抽出ロジック（4桁数字＋既知コードフィルタ）を実装。
- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層をカバーするテーブル群をDDLで定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義し、頻出クエリ向けのインデックスも用意。
  - init_schema(db_path) によりディレクトリ自動作成→テーブル＆インデックス作成を行う実装。
  - get_connection(db_path) による既存 DB への接続サポート（初期化は行わない旨明記）。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計に基づく差分更新ロジックを実装開始。
  - ETLResult データクラスで実行結果（取得数・保存数・品質問題・エラー等）を表現。
  - 差分取得支援: 最終取得日の取得ヘルパ、market_calendar による取引日補正、最小データ日付・backfill_days 設定など。
  - run_prices_etl の骨格を実装（取得範囲計算、fetch_daily_quotes 呼び出し、保存およびログ）。
- パッケージ構成
  - src/kabusys/data 以下に複数モジュール（jquants_client, news_collector, schema, pipeline, __init__）を用意。
  - strategy, execution パッケージのプレースホルダを追加（将来的な戦略・発注ロジックの配置場所）。

Security
- ニュース収集における SSRF 対策を実装（スキーム検証、リダイレクト時検査、プライベートIP判定、受信サイズ制限）。
- RSS XML パースに defusedxml を採用し、外部攻撃に対する耐性を強化。
- .env パーサはファイル読み込み失敗時に warnings.warn を発行し、無視することで致命的失敗を避ける設計。

Changed
- 初期リリースのため該当なし（新規実装中心）。

Fixed
- 初期リリースのため該当なし。

Known issues / Notes
- run_prices_etl の戻り値
  - 現状の実装末尾が不完全で、run_prices_etl が (len(records), ) のようにタプルが途中で切れている可能性があります（コードの切り取りに伴う不足か、戻り値の最終化漏れ）。呼び出し側は (fetched, saved) の 2 要素を期待する設計のため、修正が必要です。
- strategy / execution / monitoring
  - パッケージは配置済みだが具体的な実装は未提供。今後の拡張ポイント。
- schema の外部キー
  - news_symbols に FOREIGN KEY がある一方で news_articles の整合性や既存データ移行ポリシーは初期化時に考慮する必要あり。
- テスト
  - ネットワークや外部 API を利用するため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD の利用や _urlopen のモック置換を推奨。

開発者向けメモ / マイグレーション
- DB 初期化
  - 初回は init_schema(path) を呼んでテーブルを作成してください。以降は get_connection(path) を使って接続のみ取得できます。
- 環境変数
  - 必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は Settings からアクセスする際にチェックされ、未設定時に ValueError を送出します。.env.example を参考に .env を用意してください。
- ニュース収集
  - デフォルトの RSS ソースは DEFAULT_RSS_SOURCES で定義されています。追加ソースは run_news_collection にて sources 引数で上書き可能です。
- API レート制御
  - jquants_client は内部で 120 req/min のレート制限を守る設計ですが、複数プロセス・複数ノードで稼働させる場合は外部での調整が必要です。

------------------------------------------------------------
このリリースは初期実装をまとめたものです。今後、戦略ロジック、発注実装、品質チェックモジュール（quality）やテストケースの拡充、不足している戻り値の修正などを行っていく予定です。必要であれば、これらの修正・追加項目を個別の CHANGELOG エントリとして作成します。