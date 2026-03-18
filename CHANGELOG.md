Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣習に従っています。

フォーマット: 年-月-日

Unreleased
----------

- なし

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージ初期リリースを追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 基本パッケージ構成
  - モジュール構成を公開 (kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring)。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 自動ロード順序: OS 環境変数 ＞ .env.local ＞ .env
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト向け）
  - .env パーサーは export KEY=val 形式、シングル/ダブルクォート、インラインコメント等に対応。
  - Settings クラスを提供:
    - 必須項目 (例): JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - KABUSYS_ENV の許容値: development / paper_trading / live
    - LOG_LEVEL の許容値: DEBUG / INFO / WARNING / ERROR / CRITICAL

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限: 120 req/min を固定間隔スロットリングで遵守（内部 RateLimiter）。
    - リトライ: 指数バックオフ（基底 2 秒）、最大 3 回、ネットワーク系および 408/429/5xx に対してリトライ。
    - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライ。
    - ページネーション対応（pagination_key を利用）。
    - API からの取得時刻（fetched_at）を UTC で記録し、Look-ahead bias のトレーサビリティを確保。
  - DuckDB への保存ユーティリティ（冪等性を考慮）
    - save_daily_quotes: raw_prices に INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials に INSERT ... ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar に INSERT ... ON CONFLICT DO UPDATE
  - 型変換ユーティリティ: _to_float / _to_int（安全に None を返すロジックを実装）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード取得と raw_news への冪等保存を実装。
    - デフォルト RSS ソースとして Yahoo Finance を登録。
    - RSS の取得・XML パースには defusedxml を使用（XML Bomb 対策）。
    - HTTP: gzip 解凍対応、Content-Length/読み取り上限（10 MB）チェック、Gzip-bomb 対策。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - リダイレクト時にスキーム・プライベートアドレスを検査するカスタムハンドラを導入
      - ホスト名の DNS 解決結果も含めてプライベート IP を検査
    - トラッキングパラメータ除去、URL 正規化、正規化 URL の SHA-256（先頭32文字）を記事 ID として採用（冪等性）
    - テキスト前処理 (URL 除去・空白正規化)
    - raw_news, news_symbols への一括挿入はチャンク化してトランザクションで実行、INSERT ... RETURNING を用いて実際に挿入された件数を返す
    - 銘柄抽出ロジック: 正規表現で 4 桁の数値を抽出し、既知銘柄セットでフィルタ（重複除去）

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw 層のテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions の定義を含む）
  - スキーマ初期化用モジュールを追加（DataSchema.md に基づく三層構造の設計）

- リサーチ／特徴量探索 (kabusys.research)
  - feature_exploration:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト: 1,5,21 営業日）に対する将来リターンを一度に取得
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算（ties は平均ランク扱い、有効レコード 3 未満は None）
    - factor_summary: カウント/平均/標準偏差/最小/最大/中央値を計算
    - rank: 同順位は平均ランク（丸めで ties の検出漏れを防ぐ）
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200 の乖離率（データ不足時は None）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率（データ不足時は None）
    - calc_value: raw_financials から最新の財務情報を結合して PER/ROE を算出
  - 設計方針:
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみ参照（外部発注 API にはアクセスしない）
    - 標準ライブラリ中心で実装（pandas 非依存）
    - 結果は (date, code) をキーとする辞書リストで返却

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security
- news_collector に SSRF 対策、XML パースの安全ライブラリ（defusedxml）、レスポンスサイズ制限を実装。
- J-Quants クライアントはトークン管理・自動リフレッシュを行い、不正なトークン状態での無限再帰を防止するガードを追加。

Performance
- API リクエストは固定間隔のスロットリングによりレート上限を厳守。
- DuckDB へのバルク挿入はチャンク化してトランザクションでまとめることでオーバーヘッドを低減。
- 各リサーチ関数は可能な限り単一 SQL クエリでまとめて計算する（例: calc_forward_returns は複数ホライズンを一度に取得）。

Notes / Known limitations
- DuckDB テーブル定義は Raw 層の一部を含む（README / DataSchema.md を参照のこと）。一部 DDL（ファイル末尾）が省略されているため、実運用前にスキーマ定義を確認してください。
- z-score 正規化ユーティリティは kabusys.data.stats に存在するとしてエクスポートしているが、当該モジュールは本リリースの一覧に依存している点に注意（実装状況を確認してください）。
- calc_forward_returns 等は「営業日」を連続レコード数として扱うため、カレンダー日によるギャップは DuckDB 内の prices_daily データに依存します。
- KABUSYS_ENV / LOG_LEVEL の指定値が不正な場合は設定取得時に ValueError を送出します。
- news_collector の extract_stock_codes は単純な 4 桁正規表現を用いるため、誤検出の可能性がある。known_codes を与える運用を推奨します。

Migration / Upgrade notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN：J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD：kabu API 用パスワード
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID：Slack 通知用
- 自動 .env ロードをテストや特殊環境で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルト DB パスは data/kabusys.duckdb、data/monitoring.db。必要に応じて環境変数で上書きしてください。

Acknowledgements
- 本リリースは DuckDB をデータ層に使用する設計で構築されています。API クライアントや RSS パーサーの設計は外部サービスとの安全な連携を重視しています。

-----