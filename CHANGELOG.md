CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

[Unreleased]
------------

追加予定 / 進行中:
- テストカバレッジの拡充（ユニットテスト、ネットワーク依存部のモック化）
- CLI / 実行エントリポイントの追加（データ取得・収集ジョブを簡単に実行可能にする）
- DB マイグレーション管理の導入（スキーマ管理の安定化）
- publish 用パッケージメタデータ・ドキュメントの整備
- 高頻度 API 取得時の並列化・効率化（現在は固定間隔のレートリミッタを使用）

[0.1.0] - 2026-03-19
-------------------

Added
- パッケージの初期リリース（kabusys v0.1.0）。
- 基本パッケージ構成:
  - パッケージエントリポイント src/kabusys/__init__.py を追加（__version__ = "0.1.0"）。
  - サブパッケージ骨組み: data, strategy, execution, monitoring（__all__ に登録）。

- 環境設定管理:
  - src/kabusys/config.py を実装。
  - .env ファイル（.env, .env.local）をプロジェクトルート（.git または pyproject.toml）から自動読み込みする機能を追加。OS環境変数を保護する挙動（.env.local は上書き、.env は未設定時のみセット）。
  - .env 行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理等）。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスで必須設定の取得とバリデーションを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）。KABUSYS_ENV / LOG_LEVEL の許容値チェック、利便性プロパティ (is_live / is_paper / is_dev) を追加。
  - デフォルト DB パス（DUCKDB_PATH / SQLITE_PATH）を設定。

- データ取得・保存（J-Quants クライアント）:
  - src/kabusys/data/jquants_client.py を実装。
  - J-Quants API への HTTP クライアントを実装（ページネーション対応）。
  - レートリミット制御（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大3回）。408/429/5xx 系のリトライ対応。429 の場合 Retry-After ヘッダを優先。
  - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回だけ再試行する処理を実装（トークンキャッシュ共有）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等性を確保。
  - 型変換ユーティリティ (_to_float, _to_int) を追加し、不正な数値入力に対する堅牢性を確保。
  - Look-ahead bias 対策として取得時刻 (fetched_at) を UTC で記録。

- ニュース収集基盤:
  - src/kabusys/data/news_collector.py を実装。
  - RSS フィードの取得 (fetch_rss)、XML 安全パーサ（defusedxml）利用、gzip 解凍、最大応答サイズチェック（MAX_RESPONSE_BYTES）など堅牢な取得処理を提供。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト先のスキーム / ホスト検証（プライベート/ループバック/リンクローカル/マルチキャストを拒否）。リダイレクト時の事前検証を行うカスタムハンドラを実装。
    - DNS 解決失敗時は安全側扱いの設計（過度なブロックを防止）。
  - 記事ID を URL 正規化後の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を担保。トラッキングパラメータ除去、フラグメント削除、クエリキーソートを実施。
  - テキスト前処理（URL 除去、空白正規化）と pubDate の堅牢なパース（UTC で正規化、失敗時に現時刻で代替）。
  - raw_news / news_symbols への保存関数（save_raw_news, save_news_symbols, _save_news_symbols_bulk）を実装。チャンク挿入、INSERT ... RETURNING による実挿入数取得、トランザクション管理（begin/commit/rollback）を行う。
  - 銘柄抽出ユーティリティ（4桁コード抽出）および既知銘柄セットによるフィルタリングを提供。
  - デフォルト RSS ソース定義（DEFAULT_RSS_SOURCES: Yahoo Finance のビジネスカテゴリ等）。
  - run_news_collection により複数ソースの収集を統合し、各ソースを独立にエラーハンドリング。

- 研究用機能（Research / Factor modules）:
  - src/kabusys/research/feature_exploration.py を実装。
    - 将来リターン計算 (calc_forward_returns)：DuckDB の prices_daily を参照し、複数ホライズンの将来リターンを一度に取得する最適化クエリを実装。ホライズンバリデーションあり。
    - IC（Information Coefficient）計算 (calc_ic)：Spearman の ρ をランク変換経由で計算。null/ties ハンドリング、3 サンプル未満は計算不能として None を返す。
    - ランク関数 (rank)：同順位は平均ランク、丸め誤差対策に round(v, 12) を利用。
    - factor_summary：各ファクター列の count/mean/std/min/max/median を計算するユーティリティ実装。
    - 標準ライブラリのみで実装し、DuckDB 接続を受けて prices_daily のみを参照する設計。

  - src/kabusys/research/factor_research.py を実装。
    - モメンタム (calc_momentum)：1M/3M/6M リターン、200日移動平均乖離率 (ma200_dev) を DuckDB ウィンドウ関数で計算。
    - ボラティリティ/流動性 (calc_volatility)：20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御に注意。
    - バリュー (calc_value)：raw_financials から target_date 以前の最新財務データを取得し PER/ROE を計算（EPS が 0 または NULL の場合は None）。
    - 各関数は prices_daily/raw_financials のみを参照し、本番発注 API 等にはアクセスしないことを明記。
    - 計算用定数（_MOMENTUM_SHORT_DAYS 等）やスキャン幅のバッファ設計を採用。

- DuckDB スキーマ定義:
  - src/kabusys/data/schema.py にて Raw/Processed/Feature/Execution 層を想定したテーブル DDL を追加（raw_prices, raw_financials, raw_news, raw_executions のスケルトン等）。主キー制約・チェック制約を多数導入してデータ整合性を担保。

Security
- XML パースに defusedxml を採用して XML Bomb 等の攻撃を軽減。
- RSS/HTTP 取得周りで SSRF 対策を実装（スキーム検査、プライベートホスト検査、リダイレクト検証）。
- レスポンスサイズ制限（最大 10MB）を導入しメモリ DoS 対策を実施。
- J-Quants クライアントは認証トークンの自動リフレッシュと再試行戦略を備え、誤動作時の情報漏洩リスクを低減。

Notes / Usage
- 環境変数の自動読み込みはパッケージ import 時に実行されます。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化してください。
- DuckDB 保存関数は ON CONFLICT / DO UPDATE を使って冪等に動作します。初回実行時のスキーマ整備（schema の CREATE 実行）が必要です。
- research モジュールは外部ライブラリに依存せず標準ライブラリと DuckDB のみで完結する設計です（本番発注・ネットワークアクセスは行いません）。

Removed
- （初期リリースのため該当なし）

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- 詳細は上記「Security」セクションを参照。

以上。リリース以降に変更が発生した場合は本ファイルを更新してください。