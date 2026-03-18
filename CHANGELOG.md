# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
重大な互換性のある変更は MAJOR.MINOR.PATCH の規約に従って記載します。

## [Unreleased]
（現状のコードベースからはリリース済みの 0.1.0 を想定しています。今後の変更はここに追記してください）

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装したバージョンです。以下の主要機能・設計方針・安全対策を含みます。

### Added
- パッケージ基盤
  - パッケージ情報（src/kabusys/__init__.py）を追加。バージョンは 0.1.0。
  - モジュール分割: data, strategy, execution, monitoring を公開（それぞれのサブモジュール群を参照可能に設定）。

- 環境設定 / ロード機構（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - テスト等で自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）によりカレントディレクトリに依存しないよう実装。
  - .env パーサを実装:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、無効行スキップ等に対応。
  - Settings クラスで必須変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）の取得を提供。
  - DUCKDB_PATH / SQLITE_PATH 等のデフォルトや Path 変換、KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）を実装。 is_live / is_paper / is_dev のヘルパーも追加。

- データ取得クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（株価日足、財務データ、取引カレンダー取得）。
  - レート制御: 固定間隔スロットリング（120 req/min）を実装した RateLimiter。
  - 再試行（Retry）ロジック: 指数バックオフ、最大試行回数（3 回）、408/429/5xx に対するリトライ処理、Retry-After ヘッダ優先処理。
  - 認証トークン処理:
    - リフレッシュトークンから ID トークンを取得する get_id_token を実装。
    - モジュールレベルの ID トークンキャッシュを保持し、401 受信時の自動リフレッシュ＆1回のみの再試行をサポート。
  - ページネーション対応の取得関数を実装（fetch_daily_quotes, fetch_financial_statements）。
  - DuckDB への保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。いずれも冪等（ON CONFLICT DO UPDATE）を採用。
  - データ型変換ユーティリティ (_to_float, _to_int) を実装し、入力の堅牢なパースを行う。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース収集機能を実装（fetch_rss, run_news_collection）。
  - セキュリティ / 安全性:
    - defusedxml を使用した XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト時スキーム検証・プライベートアドレスブロック・初回ホスト事前検証（_is_private_host、_SSRFBlockRedirectHandler）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - 不正な Content-Length を適切に扱い超過時はスキップ。
  - RSS パース/整形:
    - タイトル / 本文の前処理（URL 除去・空白正規化）。
    - content:encoded と description の優先処理。
    - pubDate のパースと UTC 変換（パース失敗時は現在時刻で代替）。
  - 記事ID は URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除等）した上で SHA-256 の先頭 32 文字を採用し冪等性を確保。
  - DB 保存:
    - raw_news へのバルク挿入（チャンク分割、INSERT ... ON CONFLICT DO NOTHING RETURNING）で挿入された ID を正確に取得する実装（save_raw_news）。
    - news_symbols の銘柄紐付け保存（save_news_symbols, _save_news_symbols_bulk）を実装。トランザクションでまとめて安全に保存。
  - 銘柄抽出ユーティリティ（4 桁コード抽出）を実装（extract_stock_codes）。
  - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。

- 研究用ファクター計算（src/kabusys/research/*）
  - feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）：DuckDB の prices_daily を参照して複数ホライズンの将来リターンを一度のクエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: ファクターと将来リターンのスピアマンランク相関を実装。データ不足時の None 返却等の堅牢性あり。
    - ランキング（rank）ユーティリティ: 同順位は平均ランクに丸める実装（丸め誤差対策で round(v, 12) を使用）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算するユーティリティ。
  - factor_research.py:
    - モメンタム（calc_momentum）: 約1ヶ月/3ヶ月/6ヶ月リターン、200 日移動平均乖離率（ma200_dev）を計算。
    - ボラティリティ/流動性（calc_volatility）: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。TRUE RANGE の計算における NULL 伝播を厳密に扱う。
    - バリュー（calc_value）: raw_financials から直近財務データを結合して PER / ROE を計算（EPS が 0 または NULL の場合は None）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し、本番発注 API にはアクセスしない設計。
  - research パッケージの __init__ にて主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize 等）。

- スキーマ初期化（src/kabusys/data/schema.py）
  - DuckDB 用の DDL 定義（Raw Layer: raw_prices, raw_financials, raw_news, raw_executions の一部定義）を追加。データレイヤー構造（Raw / Processed / Feature / Execution）を想定したスキーマ設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）  
  - 実装段階での注意点として、.env のパースや API エラーハンドリング等に細かな堅牢性対策を組み込んでいる。

### Security
- 外部入力（RSS, HTTP リダイレクト, URL）に対して多層の防御（スキーム検証、プライベート IP ブロック、defusedxml、レスポンスサイズ制限）を実装。
- API クライアントでの認証トークン管理と 401 発生時の安全なリフレッシュ処理を実装。

### Notes / Design decisions
- DuckDB を中心としたオンディスクデータ管理を前提に設計（冪等保存、ON CONFLICT ハンドリング、INSERT RETURNING による正確な挿入結果取得）。
- 研究系モジュールは本番 API に依存しないことを明確化（検証可能なローカル DB のみ参照）。
- 外部依存を最小化する方針（研究モジュールは標準ライブラリのみで実装する旨のコメントあり）。
- 一部モジュール（strategy, execution, monitoring）はパッケージ存在のみで詳細実装は別途。

---

今後のリリースでは、strategy / execution の発注実装、モニタリング・Slack 通知連携、Processed/Feature レイヤーの DDL 完全実装、より充実したテスト・CI 設定などを想定しています。必要であればこの CHANGELOG を時系列で展開し、コミットや変更点を細かく追記します。