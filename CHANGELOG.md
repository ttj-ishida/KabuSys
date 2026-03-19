KEEP A CHANGELOG
全ての注目すべき変更を逆時系列で記録します。
このファイルは Keep a Changelog 準拠で書かれています。

[0.1.0] - 2026-03-19
Added
- 初回リリース。主要コンポーネントを追加。
  - パッケージ初期化
    - src/kabusys/__init__.py: パッケージメタ情報（__version__="0.1.0"）と公開モジュール一覧を定義。
  - 設定管理
    - src/kabusys/config.py:
      - .env/.env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
      - .env 行パーサ（export 形式、クォート/エスケープ、インラインコメント対応）。
      - 環境変数の必須チェック用 _require、設定値の検証（KABUSYS_ENV, LOG_LEVEL）。
      - settings オブジェクトで J-Quants トークン、kabu API パスワード、Slack 情報、DB パス等をプロパティとして提供。
      - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。
  - Data（外部データ取得・保存）
    - src/kabusys/data/jquants_client.py:
      - J-Quants API クライアント実装（取得/保存関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_daily_quotes, save_financial_statements, save_market_calendar）。
      - レート制限（_RateLimiter）と固定間隔スロットリング（120 req/min）実装。
      - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対応）と 401 時の自動トークンリフレッシュ。
      - ページネーション対応、結果の結合・保存ロジック、および冪等な INSERT ... ON CONFLICT による更新。
      - 型変換ユーティリティ（_to_float/_to_int）。
    - src/kabusys/data/news_collector.py:
      - RSS 収集/前処理/DB保存機能（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
      - URL 正規化（トラッキングパラメータ除去）、記事ID 生成（正規化 URL の SHA-256 先頭 32 文字）。
      - テキスト前処理（URL 除去、空白正規化）、RSS pubDate の安全なパース。
      - DB へのバルク挿入（チャンク化、INSERT ... RETURNING、トランザクション管理）で冪等性と性能を確保。
      - 銘柄コード抽出ユーティリティ（4 桁コードを known_codes でフィルタ）。
      - XML パーサに defusedxml を使用、受信サイズ上限検査（MAX_RESPONSE_BYTES）、gzip 解凍の安全チェックなどの DoS 対策。
    - src/kabusys/data/schema.py:
      - DuckDB 用スキーマ定義（Raw 層テーブル: raw_prices, raw_financials, raw_news, raw_executions 等の DDL を定義／初期化）。
  - Research（特徴量・ファクター計算）
    - src/kabusys/research/feature_exploration.py:
      - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=[1,5,21])（単一クエリで複数ホライズン取得、営業日→カレンダー日バッファ最適化）。
      - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（スピアマン ρ を実装、データ不足時は None）。
      - ランク変換: rank(values)（同順位は平均ランク、丸め誤差対策）。
      - ファクター統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median）。
    - src/kabusys/research/factor_research.py:
      - モメンタム: calc_momentum(conn, target_date)（mom_1m/mom_3m/mom_6m、ma200_dev、ウィンドウとカレンダーバッファの考慮）。
      - ボラティリティ/流動性: calc_volatility(conn, target_date)（atr_20, atr_pct, avg_turnover, volume_ratio）。
      - バリュー: calc_value(conn, target_date)（latest_fin の取得と price 組合せによる PER/ROE 計算）。
    - src/kabusys/research/__init__.py:
      - 主要関数群のエクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank）と zscore_normalize の再公開。
  - モジュール構成
    - 空のパッケージ初期化ファイルを用意（src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py）して拡張性を確保。

Security
- SSRF の防止（news_collector）:
  - リダイレクト前検査と _SSRFBlockRedirectHandler によるリダイレクト先スキーム/ホスト検証。
  - ホストのプライベート/ループバック判定（_is_private_host）を実装し、内部ネットワークアクセスを拒否。
  - URL スキーム検証（http/https のみ許可）。
- XML に対する安全対策:
  - defusedxml を使用して XML Bomb 等の攻撃を防止。
- ネットワーク・API 安定性対策（jquants_client）:
  - レート制限、再試行、429 の Retry-After 処理、401 の自動トークンリフレッシュ。
- 入出力サイズ制限:
  - RSS の受信バイト数上限（MAX_RESPONSE_BYTES）および gzip 解凍後サイズチェックでメモリ DoS を軽減。

Performance / Reliability
- DuckDB への挿入をチャンク化してバルク挿入（_INSERT_CHUNK_SIZE）を実装し、SQL パラメータ数制限を回避。
- save_* 関数は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を採用。
- save_raw_news/save_news_symbols は INSERT ... RETURNING を用い、実際に挿入されたレコード数/ID を正確に返す。
- calc_forward_returns / factor 計算は可能な限りウィンドウ内集計を SQL で実行し、スキャン範囲をカレンダーバッファで制限。

Internal / Developer notes
- 環境設定は settings オブジェクト経由で一元管理。デフォルト値（KABUSYS_ENV=development, LOG_LEVEL=INFO、DB パス等）を持つ。
- 設定検証により不正な env 値は早期に検出（ValueError を送出）。
- モジュールレベルで ID トークンキャッシュを保持し、ページネーション間でトークンを共有。
- 外部依存を最小化する方針（研究モジュールは標準ライブラリのみで実装を目指す旨の注記あり）。

Removed
- 特になし（初回リリース）。

Deprecated
- 特になし（初回リリース）。

Notes / Migration
- DuckDB スキーマが導入されるため、初回起動時にテーブルの初期化が必要。既存データがある場合はスキーマに合わせた移行を行ってください（DDL 定義を参照）。
- 環境変数によって挙動が変わる機能（自動 .env ロードの無効化など）に注意。CI/テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

参考（主な公開 API / 関数）
- 設定: kabusys.config.settings
- J-Quants: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_daily_quotes, save_financial_statements, save_market_calendar
- News: fetch_rss, save_raw_news, save_news_symbols, run_news_collection, extract_stock_codes
- Research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

---
この CHANGELOG はコードベースの実装内容から推測して作成しています。追加の変更履歴やリリース日付の正確な指定がある場合は、それに合わせて更新してください。