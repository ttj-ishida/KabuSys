CHANGELOG
=========
（このファイルは Keep a Changelog のガイドラインに準拠しています）
詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開情報:
    - __version__ = "0.1.0"
    - パブリック API: data, strategy, execution, monitoring を __all__ で公開

- 環境設定/ロード機能 (kabusys.config)
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読み込み
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能
  - .env パーサ実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理と適切なトリム処理
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として検証
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH の既定値
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の値検証
    - is_live / is_paper / is_dev のユーティリティプロパティ

- Data レイヤー (kabusys.data)
  - J-Quants API クライアント (kabusys.data.jquants_client)
    - 固定間隔スロットリングによるレート制限対応（120 req/min）
    - 再試行ロジック（指数バックオフ、最大 3 回）、HTTP 408/429/5xx をリトライ対象
    - 401 受信時は自動トークンリフレッシュを行い 1 回だけリトライ
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements）
    - JPX カレンダー取得 (fetch_market_calendar)
    - DuckDB へ冪等に保存する save_* 関数（raw_prices / raw_financials / market_calendar）
      - ON CONFLICT DO UPDATE による上書き・重複排除
    - モジュールレベルの ID トークンキャッシュを実装し、ページネーション間で使い回し
    - 入出力変換ユーティリティ (_to_float, _to_int) の実装（堅牢な型変換）

  - RSS ニュース収集 (kabusys.data.news_collector)
    - RSS フィードの取得、XML パース、記事前処理、DuckDB への保存を一貫実装
    - セキュリティ強化:
      - defusedxml を利用した XML パース（XML BOM 等の対策）
      - SSRF 対策: リクエスト前後のホスト検証、リダイレクト検査用ハンドラ
      - URL スキーム検証 (http/https のみ許可)
      - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）
      - トラッキングパラメータ除去による URL 正規化
    - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成し冪等性を確保
    - raw_news へのバルク挿入はチャンク化し INSERT ... RETURNING を利用して実際に挿入された ID を取得
    - 銘柄コード抽出ロジック（4桁数字）と news_symbols への紐付け機能を実装
    - run_news_collection による全ソース収集ジョブを提供（各ソース独立でエラーハンドリング）

  - DuckDB スキーマ初期化 (kabusys.data.schema)
    - Raw / Processed / Feature / Execution レイヤーのテーブル定義を提供
    - raw_prices, raw_financials, raw_news, raw_executions などの DDL を定義
    - スキーマは CREATE TABLE IF NOT EXISTS で安全に初期化可能

- Research レイヤー (kabusys.research)
  - 特徴量計算・探索ユーティリティを提供
    - calc_momentum: mom_1m/mom_3m/mom_6m, MA200 乖離率を計算（prices_daily 使用）
      - 欠損データやウィンドウ不足時には None を返す
    - calc_volatility: 20日 ATR, 相対 ATR (atr_pct), 20日平均売買代金, 出来高比率を計算
      - true_range の NULL 伝播を適切に制御
    - calc_value: raw_financials の最新財務を結合して PER / ROE を算出（prices_daily と組み合わせ）
    - feature_exploration: calc_forward_returns（将来リターン算出）、calc_ic（スピアマン IC）、factor_summary（統計サマリー）、rank（同順位は平均ランク）
  - 設計方針: DuckDB 接続のみを参照し本番発注 API にはアクセスしない（Research 安全性）

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Security
- RSS 取得における SSRF 対策、XML パースの安全化、レスポンスサイズ制限、URL 正規化など多数の安全対策を実装
- J-Quants クライアントにおけるトークンの自動更新とリトライ制御で堅牢性を向上

Notes / Migration
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト DB パス:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
- research モジュールは prices_daily / raw_financials テーブルを前提としているため、事前に該当テーブルのデータが必要です
- jquants_client のレート制限/再試行はデフォルト設定（120 req/min, 3 retries）で動作します。大量データ取得時は配慮してください。

Acknowledgements
- 本リリースは初版実装に基づく推定 CHANGELOG です。将来的なリリースではより詳細な変更点・著者情報・コミット参照を付記してください。