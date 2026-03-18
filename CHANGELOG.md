CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記載します。
このプロジェクトは Keep a Changelog の形式に従っています。
次の形式でバージョン履歴を管理します: Added / Changed / Fixed / Security / etc.

[Unreleased]
------------

- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-18
-------------------

Added
- 初回リリース。
- パッケージ基盤
  - kabusys パッケージを追加（バージョン 0.1.0）。
  - パッケージ公開用 __all__ に data, strategy, execution, monitoring を定義。
- 設定管理
  - 環境変数管理モジュールを追加（kabusys.config）。
  - .env/.env.local の自動読み込み（優先順: OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - .env 行パーサの実装（export プレフィックス、シングル/ダブルクォート、行末コメントの取り扱いなど）。
  - 必須環境変数取得ヘルパ _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等のプロパティを含む）。
  - 環境（KABUSYS_ENV）の検査（development / paper_trading / live）およびログレベル検証。
- データ取得・永続化（J-Quants）
  - J-Quants API クライアントを実装（kabusys.data.jquants_client）。
  - API 呼び出しでの固定間隔レートリミッタ実装（120 req/min を想定）。
  - 再試行ロジック（指数バックオフ、最大試行回数、408/429/5xx の扱い）、および 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を追加。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT を用いた冪等保存、fetched_at に UTC 時刻を記録。
  - 型変換ユーティリティ (_to_float / _to_int) を実装（不正値は None を返す等の安全な変換）。
- ニュース収集（RSS）
  - RSS ベースのニュース収集モジュールを追加（kabusys.data.news_collector）。
  - RSS フェッチ + XML パース（defusedxml 利用を想定）による記事抽出機能を実装。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
  - URL 正規化でトラッキングパラメータ除去、スキーム・ホスト小文字化、フラグメント除去、クエリソート等を実施。
  - HTTP レスポンスサイズ制限（デフォルト 10 MB）、gzip 解凍後のサイズチェック、gzip 解凍失敗時の安全なハンドリングを実装（Gzip bomb 対策）。
  - SSRF 対策: リダイレクト時のスキーム／ホスト検証、事前ホスト検査、プライベートIP検出（DNS 解決して A/AAAA を検査）を実装。
  - XML パース失敗や不正なレスポンスは安全に扱い、ログ出力の上スキップする挙動。
  - raw_news テーブルへの冪等保存（INSERT ... ON CONFLICT DO NOTHING RETURNING）と news_symbols（記事と銘柄の紐付け）保存機能、チャンク処理、トランザクション管理を実装。
  - extract_stock_codes により本文/タイトルから 4 桁銘柄コードを抽出（既知コードフィルタ付き）。
  - run_news_collection により複数 RSS ソースを横断して収集・保存・紐付けを行うジョブを実装（ソースごとに独立してエラーハンドリング）。
- リサーチ / 特徴量
  - ファクター計算・探索モジュールを追加（kabusys.research）。
  - calc_momentum：1M/3M/6M リターン、MA200 乖離率を計算する関数を実装。prices_daily テーブル参照。過少データは None を返す。
  - calc_volatility：20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算する関数を実装。prices_daily テーブル参照。true_range の NULL 伝播を厳密に制御。
  - calc_value：raw_financials の最新財務データと当日の株価を組み合わせて PER / ROE（EPS が 0/欠損なら PER は None）を計算。
  - calc_forward_returns：指定日の終値から複数ホライズン（デフォルト 1/5/21 営業日）先のリターンを一括クエリで取得。
  - calc_ic：ファクター値と将来リターンのスピアマンランク相関（IC）を計算。欠損や非有限値を適切に除外し、有効レコードが 3 未満なら None を返す。
  - rank / factor_summary：ランク付け（同順位は平均ランク）および基本統計量（count/mean/std/min/max/median）取得ユーティリティを実装。
  - 研究用関数群は外部ライブラリに依存せず標準ライブラリと DuckDB を用いて実装（Look-ahead/外部 API へのアクセスはしない設計方針）。
  - パッケージの __init__（kabusys.research）で主要関数をエクスポート（calc_momentum 等、および data.stats.zscore_normalize を再エクスポート）。
- スキーマ
  - DuckDB 用スキーマ定義モジュールを追加（kabusys.data.schema）。
  - raw_prices / raw_financials / raw_news / raw_executions 等の DDL を定義（NOT NULL / CHECK / PRIMARY KEY などの制約を含む）。
- ロギング
  - 各モジュールで詳細なログ出力を追加（info/warning/debug レベル）して運用観測性を向上。

Security
- defusedxml の使用想定や XML パースエラーの安全な扱いを取り入れ、XML ベース攻撃の被害を低減。
- RSS フェッチにおける SSRF 対策を導入（スキーム検証、プライベートアドレス検出、リダイレクト検査）。
- 外部 API（J-Quants）呼び出し時のレートリミット遵守と堅牢な再試行ロジックを実装。
- .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を実装。

Known issues / Notes
- strategy および execution パッケージの __init__.py は存在するが内部実装は空（今後の実装予定）。
- schema ファイルは複数の層を定義しているが、実運用での追加カラムやインデックス設計は今後調整が必要。
- research モジュールは DuckDB 内の prices_daily / raw_financials テーブルを前提としており、事前のデータ整備が必要。

References
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - オプション: KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_DISABLE_AUTO_ENV_LOAD
- J-Quants API のレート上限は設計上 120 req/min を想定（_MIN_INTERVAL_SEC 等で制御）。

--- 
（この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時はコミット履歴／リリース方針に基づき調整してください。）