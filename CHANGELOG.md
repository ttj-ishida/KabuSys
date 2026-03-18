CHANGELOG
=========

すべての重要な変更は Keep a Changelog 準拠で記録します。
このファイルは日本語で記載しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-18
-------------------

初期リリース。以下の主要コンポーネントと機能を実装しています。

Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - public API として data, strategy, execution, monitoring を公開。

- 環境設定（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
  - .env パーサーの強化:
    - コメント行 / export KEY=val 形式に対応。
    - シングル/ダブルクォート、バックスラッシュエスケープ対応の値パース。
    - インラインコメント判定の細かなルールを実装。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能：
    - 必須の環境変数取得で未設定時は ValueError を投げる（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID など）。
    - デフォルト値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH 等）。
    - KABUSYS_ENV, LOG_LEVEL の値検証（許容値チェック）。
    - is_live / is_paper / is_dev のヘルパープロパティ。

- データ収集（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - 再試行（指数バックオフ、最大3回）とステータスベースのリトライ制御（408/429/5xx）。
    - 401 Unauthorized 受信時のトークン自動リフレッシュ（1 回のみ）とトークンキャッシュ。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes (株価日足)
      - fetch_financial_statements (四半期財務)
      - fetch_market_calendar (JPX カレンダー)
    - DuckDB へ冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE / DO NOTHING を活用）:
      - save_daily_quotes -> raw_prices
      - save_financial_statements -> raw_financials
      - save_market_calendar -> market_calendar
    - fetched_at に UTC タイムスタンプを記録し、Look-ahead バイアス追跡を可能に。
    - HTTP ユーティリティの実装は urllib を使用し JSON デコードエラー等に対する明確なエラーメッセージを提供。
    - 値変換ユーティリティ (_to_float, _to_int) を用意し、不正値を安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を取得・正規化・保存するモジュールを実装。
    - デフォルトソース: Yahoo Finance のビジネスカテゴリ RSS。
    - 安全対策:
      - defusedxml を用いた XML パース（XML Bomb 等の防御）。
      - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバックでないことの検査、リダイレクト時にも検証する専用ハンドラを実装。
      - 受信バイト数上限（MAX_RESPONSE_BYTES=10MB）を超えるレスポンスは拒否。
      - gzip 圧縮応答の解凍と解凍後サイズ検査（Gzip bomb 防止）。
      - トラッキングパラメータ（utm_ など）を削除して URL 正規化、SHA-256（先頭32文字）ベースの記事ID生成で冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）。
    - RSS の pubDate 解析と UTC 正規化（解析失敗時は現在時刻で代替し WARN ログ）。
    - raw_news への一括挿入（チャンク化、トランザクション、INSERT ... RETURNING を利用して実際に挿入された記事IDを返す）。
    - news_symbols への銘柄紐付け機能（extract_stock_codes による 4 桁コード抽出、チャンク挿入、重複除去）。
    - run_news_collection で複数ソースを順次処理し、ソース単位での障害を隔離して継続。

- リサーチ／特徴量（kabusys.research）
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日に対する複数ホライズンの将来リターンを一度のクエリで取得（LEAD を活用）。ホライズンの検証（正の整数≤252）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。NaN/None/非有限値を除外し、有効レコード数が3未満なら None を返す。
    - rank: 同順位は平均ランクで処理（丸め誤差対策に round(..., 12) を使用）。
    - factor_summary: count/mean/std/min/max/median を計算（None と非有限値を除外）。
    - 設計方針: DuckDB の prices_daily のみ参照、本番 API には接続しない。標準ライブラリのみで実装。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m、および 200 日移動平均乖離率(ma200_dev) を計算。ウィンドウ不足時は None。
    - calc_volatility: 20 日 ATR、ATR 比率(atr_pct)、20 日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。true_range 計算で NULL 伝播を正しく扱う。
    - calc_value: raw_financials から target_date 以前の最新財務情報を取得し PER/EPS, ROE を計算（EPS が 0 または欠損時は None）。
    - 設計方針: prices_daily/raw_financials のみ参照。戦略実行系や発注 API へのアクセスは行わない。

- スキーマ（kabusys.data.schema）
  - DuckDB の DDL を定義（Raw Layer の主要テーブルを作成する SQL 定義を提供）:
    - raw_prices, raw_financials, raw_news, raw_executions (実装途中を含む) 等のテーブル定義（NOT NULL / チェック制約 / PRIMARY KEY を含む）。
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature / Execution）構想をコメントで明記。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集での SSRF 対策、defusedxml による XML パース、レスポンスサイズ制限、URL 正規化など安全性強化を実施。
- API クライアントでトークン管理・自動リフレッシュ処理を実装し、資格情報の安全な運用を支援。

Notes / Migration
- 必須の環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - .env.example を参考に .env をプロジェクトルートに配置してください。
- 自動 .env ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（主にテスト用途）。
- DuckDB スキーマ初期化およびテーブル作成は kabusys.data.schema の DDL を使用して行ってください。
- news_collector の extract_stock_codes は known_codes セットを与えることで誤検出を低減できます（このセットは既知の銘柄コード一覧を用意してください）。

Acknowledgements / Design decisions
- Research モジュールは外部ライブラリに依存せず標準ライブラリで実装されています（軽量で移植性高く設計）。
- データ保存は冪等性を重視（ON CONFLICT、INSERT ... RETURNING、トランザクション）し再実行に耐える設計。

今後の計画（短期）
- schema の残り定義（Execution/Feature 層）の完成。
- Strategy / Execution モジュールの実装（現状は __init__.py のみ存在）。
- テストカバレッジ拡充と CI の導入。
- パフォーマンスチューニング（DuckDB クエリの最適化、バルク処理の改善）。

References
- 本 CHANGELOG はコードベースの実装内容から推測して作成しました。実際のリリースノート作成時には、コミット履歴・PR コメントを参照して更新してください。