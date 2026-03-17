Keep a Changelog に準拠した CHANGELOG.md（日本語）

すべての注目に値する変更はこのファイルに記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/ に準拠しています。

Unreleased
----------

（次のリリースに向けた変更があればここに記載してください。）

[0.1.0] - 2026-03-17
-------------------

Added
- 基本パッケージ初期リリース: kabusys v0.1.0
  - src/kabusys/__init__.py にてパッケージ定義とバージョン設定を追加。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git / pyproject.toml により探索）。
    - 自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数に対応（テストでの差し替えに便利）。
    - .env 解析ロジックを実装（コメント、export 形式、シングル/ダブルクォートのエスケープ対応、インラインコメント処理等）。
    - OS 環境変数を保護する protected パラメータを用いた上書き制御。
    - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / データベースパス / 環境種別 / ログレベル等のプロパティ経由で安全に取得可能。
    - KABUSYS_ENV と LOG_LEVEL のバリデーションを実施（許容値チェック）。
    - デフォルトの DB パス（DuckDB / SQLite）は設定可能。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得用クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
    - リトライ戦略（指数バックオフ、最大3回、HTTP 408/429/5xx 対象）を実装。
    - 401 レスポンス時の自動トークンリフレッシュ（1回のみ）を実装。モジュールレベルで ID トークンをキャッシュしページネーション間で共有。
    - ページネーション対応 fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存、fetched_at を UTC で記録。
    - データ型変換ユーティリティ（_to_float / _to_int）により不正値を安全に扱う。特に float 文字列の int 変換では小数部がある場合は None を返す安全設計。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードからのニュース収集フローを実装（取得 → 前処理 → DB 保存 → 銘柄紐付け）。
    - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を定義。
    - defusedxml を用いた XML パースで XML-Bomb 等の攻撃対策を実装。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - ホスト/IP のプライベートチェック（直接 IP および DNS 解決結果の検査）。
      - リダイレクト時に事前検証する _SSRFBlockRedirectHandler を用意。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）チェックと gzip 解凍後のサイズ検証（Gzip Bomb 対策）。
    - トラッキングパラメータ除去や URL 正規化（_normalize_url）、正規化 URL からの記事ID生成（SHA-256 の先頭32文字）を実装して冪等性を確保。
    - HTML 部分テキストの前処理（URL 除去・空白正規化）を行う preprocess_text を提供。
    - DB 保存:
      - save_raw_news: チャンク化された INSERT ... ON CONFLICT DO NOTHING RETURNING を使い、トランザクション内で新規挿入 ID を正確に取得。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを重複除去・チャンク化で効率良く保存。
    - 銘柄コード抽出ロジック（extract_stock_codes）を実装。4桁数字の候補から known_codes に含まれるものだけを抽出。
    - run_news_collection により、複数ソースを独立して処理（ソース単位でエラーハンドリング）、新規保存数の集計と銘柄紐付け一括保存をサポート。
    - _urlopen を抽象化してテスト時にモック差し替え可能。

- DuckDB スキーマ定義
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution の 3 層 + 実行レイヤーをカバーするテーブル群を定義。
    - 各テーブルに適切な制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）を付与。
    - 頻出クエリに対応するインデックスを定義。
    - init_schema(db_path) により親ディレクトリの自動作成、DDL を順序に従って冪等的に実行して初期化する API を提供。
    - get_connection(db_path) を提供（初期化不要で既存 DB に接続可能）。

- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py
    - ETL の設計方針に基づくユーティリティとジョブを実装。
    - ETLResult dataclass により ETL 実行報告（取得数・保存数・品質問題・エラー）を構造化して返却。
    - 差分更新用ヘルパー（テーブル存在確認、最大日付取得等）を提供。
    - 市場カレンダーを使った非営業日調整ロジック（_adjust_to_trading_day）。
    - run_prices_etl: 差分更新ロジック（最終取得日から backfill_days 日前から再取得）、fetch/save の組合せを実装。backfill_days のデフォルトは 3。
    - 定数:
      - 最古データ開始日 _MIN_DATA_DATE = 2017-01-01
      - カレンダー先読み _CALENDAR_LOOKAHEAD_DAYS = 90
    - 品質チェックのためのフック（quality モジュールを利用）を想定した設計。

Security
- news_collector と jquants_client においてネットワーク周り・XML パース・トークン管理・DB 保存の安全対策を実装（SSRF 防止、XML の安全パース、TLS/HTTP ヘッダ検証、トークン自動更新の再帰防止、DB のトランザクション保護）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Notes / Implementation details
- 日時は UTC で記録（fetched_at 等は ISO8601 Z 表記、RSS の pubDate は UTC naive に正規化して保存）。
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）を採用。
- 一部のヘルパーはテスト容易性を考慮して差し替え可能（例: news_collector._urlopen）。
- jquants_client のリトライでは 429 の Retry-After ヘッダを優先して待機する実装。

Breaking Changes
- なし（初回公開）。

Acknowledgements / References
- この CHANGELOG はソースコードからの推測に基づいて作成しています。実装方針や設計意図はコード内の docstring・コメントに準拠しています。

--- End of CHANGELOG ---