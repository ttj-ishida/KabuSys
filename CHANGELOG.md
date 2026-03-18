Keep a Changelog 準拠の CHANGELOG.md（日本語）を以下に作成しました。

CHANGELOG.md

All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現在差分はありません）

0.1.0 - 2026-03-18
-----------------
Added
- 基本パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開情報
    - __version__ = "0.1.0"
    - パッケージ公開モジュール: data, strategy, execution, monitoring

- 設定/環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能
    - プロジェクトルートを .git または pyproject.toml から探索して自動ロード（CWD 非依存）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env 行パーサ実装
    - コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応
  - 上書き制御・保護キー機能
    - override フラグと protected キーセットにより OS 環境変数の保護が可能
  - Settings クラス
    - J-Quants / kabu API / Slack / DB パス 等のプロパティを提供
    - 必須環境変数取得時に未設定で ValueError を発生させる _require 実装
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL（DEBUG/INFO/...）の検証

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装
    - レートリミット厳守（120 req/min）を固定間隔スロットリングで制御（内部 _RateLimiter）
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対象）
    - 401 受信時のトークン自動リフレッシュ（1回のみ）とトークンキャッシュ
    - ページネーション対応の取得関数:
      - fetch_daily_quotes (株価日足)
      - fetch_financial_statements (財務データ)
      - fetch_market_calendar (JPX カレンダー)
    - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
    - 入出力変換ユーティリティ: _to_float, _to_int
    - Look-ahead bias 対策として fetched_at を UTC ISO8601 で記録

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからの記事収集機能
    - fetch_rss: RSS 取得・解析（gzip 対応、受信サイズ制限、defusedxml を使用）
    - 前処理: URL 除去、空白正規化（preprocess_text）
    - 記事ID: URL 正規化後の SHA-256 の先頭32文字を使用して冪等性を保証
    - URL 正規化: トラッキングパラメータ（utm_* 等）削除、クエリソート、フラグメント削除
    - SSRF 対策:
      - リダイレクト検査用ハンドラ (_SSRFBlockRedirectHandler)
      - 初期と最終 URL のスキーム検証（http/https のみ許可）
      - ホストがプライベート/ループバック/リンクローカルでないことを検査
    - サイズ安全対策: 最大受信バイト数（MAX_RESPONSE_BYTES = 10MB）チェック、gzip 後のサイズ検査
    - XML パース失敗は警告ログを出して空リストを返す設計
  - DB 保存・紐付け
    - save_raw_news: INSERT ... RETURNING を使い、実際に挿入された記事 ID リストを返す（チャンク・トランザクション）
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への (news_id, code) 一括保存（重複排除・トランザクション）
    - run_news_collection: 複数ソースの統合ジョブ（ソース単位で独立ハンドリング、known_codes を利用した銘柄抽出と紐付け）
  - 銘柄コード抽出ユーティリティ
    - extract_stock_codes: テキスト中の 4 桁数字候補を known_codes と照合して抽出

- DuckDB スキーマ (kabusys.data.schema)
  - Raw Layer テーブル定義（DDL）
    - raw_prices, raw_financials, raw_news, raw_executions（定義の一部掲載）
  - スキーマ初期化を目的としたモジュール骨格

- リサーチ・特徴量計算 (kabusys.research)
  - feature_exploration モジュール
    - calc_forward_returns: DuckDB の prices_daily を参照して将来リターン（horizons 指定可）を一括 SQL で計算
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算（同順位は平均ランク、データ不足時は None）
    - rank: 同順位の平均ランク処理（浮動小数丸めによる ties の検出向上）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出
  - factor_research モジュール
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）を DuckDB SQL ウィンドウ関数で計算
    - calc_volatility: atr_20（20日 ATR 平均）、atr_pct、avg_turnover、volume_ratio を計算（真の TR の NULL 伝播を注意深く扱う）
    - calc_value: latest_fin（raw_financials の target_date 以前最新）と価格を結合して PER/ROE 等を算出
  - すべてのリサーチ関数は DuckDB 接続を受け取り prices_daily/raw_financials のみ参照（外部 API へのアクセスなし）

- パッケージ公開インターフェース (kabusys.research.__init__)
  - 主要関数を __all__ で公開 (calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank)

Security
- ニュース収集での安全対策強化
  - defusedxml を利用した XML パース（XML Bomb 等の対策）
  - SSRF 対策: URL スキーム制限（http/https）、プライベートアドレス検出、リダイレクト時の事前検証
  - HTTP レスポンスサイズ上限と gzip 解凍後サイズ検査によるメモリ DoS 対策

Notes
- 必須環境変数例（Settings で _require により必須扱い）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など
- DuckDB / SQLite のデフォルトパスは Settings.duckdb_path / sqlite_path で設定可能（環境変数 DUCKDB_PATH/SQLITE_PATH）
- J-Quants API のレート制限・リトライ・トークン更新の設計は本番の長時間実行を想定
- strategy / execution / monitoring パッケージは存在するが（__init__.py がある）具体的実装は本バージョンでは未実装または外部化されている

Acknowledgements
- 本 CHANGELOG はコードベースから推測して記載しています。動作・仕様の詳細は該当モジュールの実装・ドキュメントを参照してください。