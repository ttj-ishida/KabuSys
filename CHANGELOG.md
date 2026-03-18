# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトではセマンティックバージョニングを採用します。

## [Unreleased]

(現在のリリースは 0.1.0 のみ。今後の変更をここに記載します。)

---

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買 / データ基盤用の基本ライブラリ群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。モジュール群（data, strategy, execution, monitoring）の公開を設定。

- 環境設定
  - 環境変数読み込みモジュール（kabusys.config）を実装。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml による検出）から自動読み込み（優先順: OS > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を追加。
    - .env 行パーサ（export 形式、シングル/ダブルクォートのエスケープ、インラインコメント処理等）を実装。
    - override / protected 機能により OS 環境変数を保護して .env.local で上書き可能に。
    - Settings クラスを提供し、必須変数取得（_require）、パス展開（duckdb/sqlite）のユーティリティ、KABUSYS_ENV / LOG_LEVEL の検証、is_live/is_paper/is_dev のヘルパーを提供。

- データ取得クライアント
  - J-Quants API クライアント（kabusys.data.jquants_client）を実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - リトライロジック（指数バックオフ、最大 3 回。408/429/5xx を対象）を実装。
    - 401 受信時は自動でリフレッシュトークンから id_token を再取得して 1 回リトライする仕組みを実装（無限再帰防止）。
    - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を抑制。
    - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT による冪等性を確保。

- ニュース収集
  - RSS ニュース収集モジュール（kabusys.data.news_collector）を実装。
    - RSS フィード取得（fetch_rss）、記事整形（preprocess_text）、URL 正規化（_normalize_url）、記事 ID 生成（正規化 URL の SHA-256 の先頭 32 文字）を実装。
    - defusedxml を用いた安全な XML パース、gzip 対応、レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）チェック、Gzip-bomb 対策を実装。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト時のスキーム/ホスト検証用ハンドラ、プライベート IP 検出（DNS 解決を含む）を実装。
    - raw_news への冪等保存（INSERT ... ON CONFLICT DO NOTHING RETURNING id）をチャンク化してトランザクションで処理する save_raw_news を実装。
    - 銘柄紐付け処理（extract_stock_codes, save_news_symbols, _save_news_symbols_bulk）、run_news_collection による統合ジョブを実装。
    - デフォルト RSS ソース（DEFAULT_RSS_SOURCES）に Yahoo Finance カテゴリ RSS を登録。

- DuckDB スキーマ
  - kabusys.data.schema にて Raw / Processed / Feature / Execution 層の基礎テーブル DDL を実装（raw_prices, raw_financials, raw_news, raw_executions 等の定義を含む）。
  - 初期化用 DDL を用意し、データ層の構造を定義。

- リサーチ（特徴量・ファクター）
  - kabusys.research パッケージと主要関数を実装（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみを参照し、外部 API にアクセスしない設計。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。データ不足時は None を返却。
    - calc_volatility: 20 日 ATR / ATR 比率、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御により誤計算を防止。
    - calc_value: raw_financials から直近財務を参照し PER / ROE を計算（EPS が 0 または NULL の場合は per を None に）。
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト 1,5,21 日）への将来リターンを一括クエリで取得。
    - calc_ic: スピアマンのランク相関（IC）を実装（rank ユーティリティは同順位を平均ランクで扱う、丸め処理により浮動小数の ties 判定漏れを軽減）。
    - factor_summary: count / mean / std / min / max / median を計算する統計サマリーを実装。
    - 研究用ユーティリティは標準ライブラリのみで実装（pandas 等には依存しない）。

- 汎用ユーティリティ
  - データパース系の補助関数（_to_float, _to_int、.env パーサ等）を実装し、入力値の堅牢性を高める。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- ニュース収集において以下のセキュリティ対策を導入:
  - defusedxml による XML パース（XML bomb 等の緩和）。
  - SSRF 対策（スキーム検証、プライベート IP 検出、リダイレクト先検証）。
  - レスポンスサイズ上限と gzip 解凍後のサイズチェック（メモリ DoS 対策）。

### Notes / Migration
- DuckDB スキーマを変更・追加する場合、既存データとの互換性を確認してください。初期リリースでは raw_* 系テーブルの DDL を定義しています。
- J-Quants クライアントは API レート制限やリトライ挙動に依存します。運用環境では settings.jquants_refresh_token を正しく設定してください。
- .env の自動ロードはプロジェクトルート検出に依存します（.git か pyproject.toml をルートとみなす）。パッケージ配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を用いて自動読み込みを無効化できます。

---

開発チームへのお願い:
- 変更を加える際はこの CHANGELOG を更新してください（Unreleased → 新バージョンへの移動、および該当セクションの更新）。