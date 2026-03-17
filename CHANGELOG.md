CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

（なし）

0.1.0 - 2026-03-17
------------------

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

Added
- パッケージの初期化
  - src/kabusys/__init__.py にてパッケージ名とバージョン（0.1.0）、公開サブパッケージ（data, strategy, execution, monitoring）を定義。

- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local および環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - export KEY=val 形式・クォート・コメントの扱いなどを考慮した .env パーサ実装。
  - 必須値取得（_require）、環境変数検証（KABUSYS_ENV の有効値、LOG_LEVEL の検証）を提供。
  - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを定義。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、四半期財務、マーケットカレンダー取得用 API 呼び出しを実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - 認証トークン取得（get_id_token）とモジュールレベルのトークンキャッシュ。
  - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx をリトライ対象）と 429 の Retry-After 優先。
  - 401 受信時は自動でトークンをリフレッシュして 1 回リトライ（再帰防止の仕組みあり）。
  - 取得データを DuckDB に冪等に保存する save_* 関数（ON CONFLICT DO UPDATE）を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
  - fetched_at に UTC 時刻を保持して Look-ahead Bias の追跡を可能に。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS からのニュース収集・前処理・DuckDB への保存ワークフローを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
  - defusedxml を利用した XML パース（XML Bomb 防御）。
  - SSRF 対策: リダイレクト検査、スキーマ検証（http/https のみ）、ホストのプライベートアドレス検出でブロック。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - トラッキングパラメータ（utm_* 等）の除去、URL/空白正規化などの前処理。
  - 一括挿入時のチャンク化（_INSERT_CHUNK_SIZE）と INSERT ... RETURNING を用いた実挿入数の把握。
  - テキストからの銘柄コード抽出（4桁数字に限定し known_codes に照合）機能。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層に対応したテーブル定義を提供（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions 等）。
  - 各テーブルの制約（PRIMARY KEY、CHECK、外部キー）を定義。
  - 頻出クエリ向けインデックスを作成（idx_*）。
  - init_schema(db_path) によるディレクトリ作成を含む初期化処理と get_connection を提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL の設計方針・差分更新ロジックを実装（最終取得日の追跡、backfill_days による再取得）。
  - ETL 結果を表す ETLResult データクラス（品質問題・エラー収集、辞書化ユーティリティ）を追加。
  - テーブル存在チェック、最大日付取得ヘルパー、取引日調整ロジックを実装。
  - run_prices_etl の骨組みを実装（差分算出 → jq.fetch_daily_quotes → jq.save_daily_quotes の呼び出し）。

- その他
  - データ層のパッケージ初期化ファイルを追加（src/kabusys/data/__init__.py）。
  - strategy と execution サブパッケージのプレースホルダ __init__.py を追加（今後の拡張用）。

Security
- ニュース収集で SSRF 対策、XML パースに defusedxml を採用、レスポンスサイズ制限を導入。
- RSS 内の不正スキーム（mailto:, file:, javascript: 等）を排除。

Performance / Reliability
- API レート制御（固定間隔）とリトライ（指数バックオフ）により外部 API 呼出しの安定性を向上。
- DuckDB へのバルク挿入はチャンク処理・トランザクションでまとめて行いオーバーヘッドを低減。
- save_* 系は冪等性を担保（ON CONFLICT）して複数回実行可能。

Known issues / Notes
- pipeline.run_prices_etl の実装は骨組みまで完成していますが、ソース提供分の最後が途中で切れているため（返却タプル等）実装の最終確認・ユニットテストが推奨されます。
- strategy および execution パッケージは現状プレースホルダであり、戦略ロジック・発注実行ロジックは未実装です。
- schema にていくつかの制約・外部キーを設定していますが、実運用時にパフォーマンスやリファレンス動作を確認してください（DuckDB の外部キー挙動など）。
- J-Quants API のレート／認証周りは設計上考慮済みですが、運用環境に合わせた監視・ログ設定を行ってください。

Breaking Changes
- 初回リリースのため該当なし。

参考
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に合わせています。