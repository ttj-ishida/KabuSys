# Changelog

すべての重要な変更履歴をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回公開リリース。日本株自動売買プラットフォームの基盤機能をまとめて追加。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0、主要サブパッケージをエクスポート）。
- 設定/環境変数管理（kabusys.config）
  - .env / .env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 複雑な .env 行のパース対応（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境・ログレベルの検証プロパティを含む）。
  - KABUSYS_ENV と LOG_LEVEL の妥当性チェック、および is_live/is_paper/is_dev の補助プロパティ。
- データ取得・保存: J-Quants クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ（_request）を実装。ページネーション対応の fetch_* 関数（daily_quotes / financial_statements / market_calendar）。
  - レート制限管理（_RateLimiter、120 req/min 固定間隔スロットリング）。
  - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx をリトライ対象）、429 に対して Retry-After ヘッダ優先処理。
  - 401 発生時の ID トークン自動リフレッシュ（1 回まで）とモジュールレベルのトークンキャッシュ。
  - DuckDB へ冪等に保存する save_* 関数（raw_prices / raw_financials / market_calendar へ ON CONFLICT DO UPDATE）。
  - fetched_at を UTC ISO8601 で記録することで Look-ahead Bias のトレースを可能に。
  - データ型変換ユーティリティ (_to_float, _to_int) の堅牢化。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理・DB 保存の統合機能（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）、SHA-256 による記事 ID 生成。
  - XML パースに defusedxml を採用し XML Bomb 等の攻撃緩和。
  - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト時のスキーム/ホスト検査（_SSRFBlockRedirectHandler）、プライベート/ループバック/リンクローカル判定（_is_private_host）。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後サイズチェック（Gzip bomb 対策）。
  - コンテンツ前処理（URL 除去、余分な空白正規化）、pubDate の堅牢なパース（失敗時は現在時刻で代替）。
  - raw_news / news_symbols へのバルク挿入をチャンク化し、INSERT ... RETURNING で実際に挿入された件数を取得。トランザクション管理（commit/rollback）。
  - 記事本文からの銘柄コード抽出機能（4桁数字パターン + known_codes フィルタ）。
- 研究（Research）モジュール（kabusys.research）
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Spearman ρ）計算（calc_ic）、ランク関数(rank)、ファクター統計サマリ(factor_summary) を実装。
  - factor_research: モメンタム/ボラティリティ/バリュー系ファクター計算（calc_momentum, calc_volatility, calc_value）。DuckDB の prices_daily/raw_financials を参照し、営業日ベースのウィンドウ処理を行う設計。
  - research パッケージの __all__ に主要関数を公開（zscore_normalize を含む）。
  - 研究用関数群は標準ライブラリ主体で実装され、外部ライブラリ（pandas 等）に依存しない設計。
- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw レイヤ用テーブル DDL を実装（raw_prices, raw_financials, raw_news, raw_executions 等の定義）。スキーマ初期化用基盤を追加。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- RSS パーサに defusedxml を採用し、安全な XML パースを実現。
- ニュース取得に対して複数レイヤの SSRF 対策を導入（スキーム検証、リダイレクト検査、プライベートアドレス検出）。
- 外部 API クライアントはレート制限を尊重し、Retry-After を考慮した再試行を実施。
- データベース保存は可能な限り冪等化（ON CONFLICT）とトランザクション管理を行い、整合性を確保。

### Notes / Limitations
- research モジュールは DuckDB テーブル（prices_daily / raw_financials 等）を前提としており、本実装はそれらの前処理（processed/feature layer）と組み合わせて利用する想定です。
- calc_* 関数は「営業日ベース（連続レコード数）」でのホライズン設計を採用しており、カレンダー日数との差分を考慮しています。
- 一部テーブル定義・DDL の続き（raw_executions 等）はコードベースに含まれているが、運用時は必要に応じてスキーマ拡張が必要です。

---

参照:
- パッケージバージョン: kabusys.__version__ = 0.1.0
- 本 CHANGELOG はリポジトリ内コードの実装内容から推測して作成しています。