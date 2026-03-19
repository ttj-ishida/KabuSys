# Changelog

すべての変更はコードベースから推測して記載しています。実際のコミット履歴ではなく、提供されたソースコードの機能・設計意図をもとにまとめたリリースノートです。

All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-19

初回公開リリース（コードベースから推測）。以下の主要機能と設計上のポイントを実装しています。

### Added
- パッケージ初期化
  - kabusys パッケージのエントリポイントを定義（src/kabusys/__init__.py）。
  - バージョン `0.1.0` を設定。

- 環境設定 / ロード
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機構を実装（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env の行パーサはコメント、export プレフィックス、クォート／エスケープ、インラインコメント等に対応。
  - Settings クラスを提供し、必須値のチェック（例: JQUANTS_REFRESH_TOKEN、SLACK_BOT_TOKEN 等）、環境値の検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）、パスの展開（duckdb/sqlite）などのアクセサを用意。

- データ取得・永続化（J-Quants API クライアント）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - 固定間隔スロットリングによるレート制御（120 req/min）を実装する RateLimiter。
    - HTTP リクエストの共通処理（_request）で、指数バックオフ、最大リトライ、429 の Retry-After 優先、ネットワーク/HTTP エラーに対するリトライ処理を実装。
    - 401 受信時にリフレッシュトークンでトークン更新を自動実行（1 回だけリトライ）。
    - ページネーション対応のデータフェッチ（fetch_daily_quotes, fetch_financial_statements）および市場カレンダー取得。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。冪等化のためON CONFLICT DO UPDATE を使用。
    - 型変換ユーティリティ（_to_float, _to_int）を提供し、入力データの堅牢なパースを実現。
    - fetched_at を UTC ISO 形式で記録し Look-ahead Bias のトレースをサポート。

- ニュース収集（RSS）
  - RSS フィード収集・整形・DB 保存の一連処理を実装（src/kabusys/data/news_collector.py）。
    - RSS の取得 (fetch_rss)、XML パース（defusedxml を使用）と記事ノーマライズ（URL除去・空白正規化）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と、正規化 URL からの SHA-256 ベース記事 ID 生成（先頭32文字）による冪等性確保。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルでないかチェック、リダイレクト時にも検証するカスタムハンドラ（_SSRFBlockRedirectHandler）を導入。
    - レスポンスサイズ制限（最大 10MB）や gzip 解凍後のサイズチェック（Gzip bomb 対策）を実装。
    - DB 保存はチャンク化とトランザクションで処理し、INSERT ... RETURNING を使って実際に挿入された ID を返却（save_raw_news、save_news_symbols、内部バルク保存関数）。
    - 日本株銘柄コード（4桁）抽出ロジック（正規表現）と known_codes によるフィルタリング。
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。

- リサーチ（特徴量・ファクター計算）
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）：DuckDB の prices_daily を参照して各銘柄の fwd_1d / fwd_5d / fwd_21d 等を一度のクエリで取得。
    - IC（Information Coefficient）計算（calc_ic）：ファクターと将来リターンのスピアマンランク相関を計算（ties の平均ランク対応、3 銘柄未満は None を返す）。
    - ランク付けユーティリティ（rank）とファクター統計サマリー（factor_summary）。
    - 標準ライブラリのみで依存を最小化。
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum（mom_1m, mom_3m, mom_6m）および MA200 乖離率（ma200_dev）の計算（prices_daily を参照）。
    - Volatility / Liquidity（atr_20, atr_pct, avg_turnover, volume_ratio）の計算（ATR の NULL 伝播制御、窓サイズチェック）。
    - Value ファクター（PER, ROE）の計算（raw_financials から target_date 以前の最新財務を取得して prices_daily と結合）。
    - 計算のためのスキャン範囲最適化（カレンダーバッファ）や欠測時の None ハンドリング。
  - research パッケージの __all__ に主要ユーティリティを公開。

- DuckDB スキーマ定義
  - DuckDB 用のスキーマ定義・初期化モジュール（src/kabusys/data/schema.py）の一部を実装。
    - raw_prices、raw_financials、raw_news、raw_executions 等の DDL を定義（PRIMARY KEY、チェック制約を含む）。
    - DataLayer の三層（Raw / Processed / Feature / Execution）設計に基づく構成（ファイル冒頭の設計説明）。

- ロギングと設計ドキュメント的コメント
  - 各モジュールに詳細な docstring と設計方針、例外ケースの説明、ログ出力（logger）を充実させている。

### Security
- ニュース収集における SSRF 対策を導入:
  - URL スキーム制限（http/https のみ）
  - ホストがプライベート/ループバック等でないかの検査（DNS 解決を行い A/AAAA をチェック）
  - リダイレクト時にも同様の検査を行う custom redirect handler を利用
  - defusedxml を使った XML パース（XML-based 攻撃に対する保護）
  - レスポンスサイズ制限と Gzip 解凍後の上限チェック（DoS / Bomb 対策）
- J-Quants クライアントでのトークン自動リフレッシュは再帰を避ける設計（allow_refresh フラグ）により無限再試行を防止。

### Reliability / Robustness
- J-Quants API クライアントでの堅牢なリトライ／バックオフ（429 の Retry-After 尊重、指数バックオフ、最大試行回数）。
- DuckDB への保存は冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING を活用）。
- RSS 解析で欠損要素や非標準フォーマットに対するフォールバックを用意（channel/item の代替探索）。
- .env パーサはクォートやエスケープを考慮しており、実環境での柔軟性を確保。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Limitations (既知の想定/制約)
- research モジュールは DuckDB の prices_daily / raw_financials テーブルのみを参照する想定で、本番口座や発注 API へアクセスしない設計。
- 一部モジュール（execution, strategy 等）は __init__ のみ定義されており、具体的な実装はこのバージョンでは未提供。
- DuckDB スキーマ定義はファイルの一部のみが提示されている（raw_executions の DDL が途中で終わっているため、完全なスキーマは実装ソース全体に依存）。
- news_collector の HTTP クライアントは urllib を使用しており、ユニットテストで _urlopen をモックして差し替え可能な設計。

---

（以上は提供されたソースコードの内容に基づく推測的な CHANGELOG です。実際のリリースノートやコミットログとは差異がある可能性があります。）