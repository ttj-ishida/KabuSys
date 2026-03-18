# CHANGELOG

すべての重要な変更は Keep a Changelog の慣例に従って記載します。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]
- 今後のリリースに向けた未確定の変更や改善点をここに記載します。

## [0.1.0] - 2026-03-18
初回リリース。KabuSys のコア機能（設定管理、データ収集・保存、リサーチ用特徴量計算、ニュース収集、DuckDB スキーマなど）を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージを示す __init__ を追加（バージョン: 0.1.0）。公開モジュールに data/strategy/execution/monitoring を含める宣言。
- 設定管理 (src/kabusys/config.py)
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - 読み込み順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応）。
  - Settings クラスを実装し、J-Quants / kabuAPI / Slack / DB パスなどの環境変数をプロパティ経由で取得。値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を行う。
- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw レイヤーのテーブル DDL を定義（raw_prices, raw_financials, raw_news 等を含む）。データ型・制約（NOT NULL, CHECK, PRIMARY KEY）を明示。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - レート制限管理（固定間隔スロットリング、120 req/min）を _RateLimiter で実装。
  - リトライロジック（指数バックオフ、最大 3 回。408/429/5xx を対象）。429 の場合 Retry-After ヘッダを尊重。
  - 401 受信時にリフレッシュトークンで id_token を自動更新して 1 回リトライ（無限再帰対策あり）。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE を使用して更新を保証。
  - データ変換ヘルパー (_to_float, _to_int) を実装し、不正値や空値に安全に対応。
- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集と前処理を実装（デフォルトに Yahoo Finance の RSS を含む）。
  - セキュリティ強化:
    - defusedxml を利用した XML パース（XML ボム対策）。
    - SSRF 対応: URL スキーム検査、リダイレクト先のスキーム・ホスト検証、プライベート IP の拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
  - URL 正規化関数 (_normalize_url) と記事 ID 生成（SHA-256 の先頭 32 文字）を実装し冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）と銘柄コード抽出（4桁数字、既知銘柄セットによるフィルタ）。
  - DB 保存: save_raw_news（チャンク化、INSERT ... RETURNING により実際に挿入された id を返す）、news_symbols 紐付けの一括保存機能を実装。
  - 全ソース処理の統合ジョブ run_news_collection を実装。個々のソースは独立して失敗をハンドリング。
- Research モジュール (src/kabusys/research/)
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（horizons 検証、単一クエリで LEAD を利用して取得）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関、None 値・finite 判定、最小レコード数検査）。
    - ランキング変換 rank（同順位は平均ランク、丸め処理により ties の検出を安定化）。
    - ファクター統計 summary（count/mean/std/min/max/median を計算）。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB を利用する設計。
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum, Volatility, Value（および Liquidity 構想）の計算関数（calc_momentum, calc_volatility, calc_value）を実装。
    - 各関数は DuckDB の prices_daily / raw_financials を参照し、ウィンドウ集約（LAG, AVG, COUNT, ウィンドウ関数）で計算。データ不足時は None を返す扱い。
    - 定数（窓長、スキャンバッファ等）を明確化し、パフォーマンスを考慮したカレンダーバッファを採用。
- パッケージ公開 (src/kabusys/research/__init__.py)
  - 研究用ユーティリティをまとめてエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector にて SSRF 緩和策（リダイレクトハンドラ、プライベート IP チェック）、defusedxml による安全な XML パース、レスポンスサイズ検査を実装。
- J-Quants クライアントでトークンリフレッシュ時に無限再帰が起こらないよう allow_refresh フラグを使用。

### 既知の注意点 / 制限 (Known Issues / Notes)
- research モジュールは標準ライブラリのみで実装する設計であり、高機能な統計処理には pandas 等の外部ライブラリを使った別実装が想定される。
- news_collector は RSS の標準外レイアウトに一定のフォールバックを行うが、全フィードに対して完全互換を保証するものではない。
- schema.py に記載されるテーブルは Raw レイヤーを中心に示しており、Processed / Feature / Execution レイヤーの完全な DDL は今後追加予定。
- src/kabusys/execution と src/kabusys/strategy はパッケージとして存在するが（__init__.py が空）具体的な実装は今後追加予定。

### 互換性 (Breaking Changes)
- 初回リリースのため互換性破壊はなし。

---

上記はコードベースから推測した初期リリース向けのリリースノートです。必要に応じて項目の追加・修正を行います。