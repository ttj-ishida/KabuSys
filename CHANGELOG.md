# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。  
リリースポリシー: セマンティックバージョニング (MAJOR.MINOR.PATCH)

## [Unreleased]
- 今後のリリースでの作業予定:
  - strategy / execution パッケージの具体的実装
  - data.stats の拡張（zscore 正規化以外の統計ユーティリティ）
  - 追加の DB スキーマ（Execution / Position 層）の完成
  - 単体テスト追加と CI ワークフロー整備

## [0.1.0] - 2026-03-19
初回公開リリース。

### Added
- パッケージ基本情報
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。公開 API: data, strategy, execution, monitoring。バージョンは 0.1.0 に設定。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env と .env.local の優先順位と上書き制御をサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - 環境変数パーサを実装（コメント、export プレフィックス、クォート、エスケープ対応）。
  - Settings クラスを提供し、必要な設定値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）をプロパティとして取得。
  - 環境パラメータ検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）、便利メソッド（is_live / is_paper / is_dev）。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - レート制御（固定間隔スロットリングで 120 req/min に準拠）。
  - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
  - 401 発生時の自動トークンリフレッシュと 1 回の再試行処理。
  - id_token のモジュール内キャッシュ（ページネーション間トークン共有）。
  - ページネーション対応のデータ取得: 日足 (fetch_daily_quotes)、財務データ (fetch_financial_statements)、マーケットカレンダー (fetch_market_calendar)。
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。INSERT ... ON CONFLICT 句で重複を更新または無視。
  - データ変換ユーティリティ (_to_float / _to_int) により外部データの堅牢な型変換を実現。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集と前処理パイプラインを実装。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url, _make_article_id）。
  - DefusedXML を用いた安全な XML パース。
  - SSRF 対策: URL スキーム検証、リダイレクト先の事前検査、プライベート IP 判定（_is_private_host）、カスタムリダイレクトハンドラ。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - テキスト前処理（URL 除去・空白正規化）。
  - 記事の ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - DuckDB への保存関数（save_raw_news, save_news_symbols, _save_news_symbols_bulk）を実装。チャンク挿入、トランザクション管理、INSERT ... RETURNING により実際に挿入された行数を正確に取得。
  - 銘柄コード抽出ユーティリティ（extract_stock_codes、4桁コード抽出 + known_codes フィルタリング）。

- DuckDB スキーマ (src/kabusys/data/schema.py)
  - Raw Layer のテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions の定義を含む。初期化処理用モジュール）。
  - スキーマ定義は DataSchema.md の想定設計に準拠（Raw / Processed / Feature / Execution 層を想定）。

- リサーチ / ファクター計算 (src/kabusys/research/*.py)
  - feature_exploration.py:
    - 将来リターン計算: calc_forward_returns（マルチホライズン対応、1クエリで取得）。
    - IC（Information Coefficient）計算: calc_ic（Spearman ρ の計算、ランク算出を含む）。
    - 基本統計サマリー: factor_summary（count/mean/std/min/max/median）。
    - rank ユーティリティ（同順位は平均ランク、丸めによる ties 対応）。
    - 標準ライブラリのみでの実装を志向（pandas 等に依存しない）。
  - factor_research.py:
    - モメンタム: calc_momentum（1M/3M/6M リターン、MA200 乖離率、データ不足時は None）。
    - ボラティリティ/流動性: calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）。
    - バリュー: calc_value（raw_financials から最新財務を取得して PER / ROE を算出、EPS 0/欠損時は None）。
    - 各関数は DuckDB 接続と prices_daily / raw_financials テーブルのみを参照し、本番発注 API へアクセスしない設計。
  - research パッケージ初期化で主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- （該当なし — 初回リリース）

### Fixed
- （該当なし — 初回リリース）

### Security
- ニュース収集における SSRF 対策強化:
  - リダイレクト先のスキーム/ホスト検査、プライベート IP 判定、許可スキームは http/https のみ。
  - defusedxml を利用して XML に関する攻撃を緩和。
  - レスポンスサイズ制限と gzip 解凍後のサイズチェックでメモリ DoS 対策。

### Notes / Limitations
- calc_value では PBR・配当利回りは未実装（README/ドキュメントに記載予定）。
- strategy / execution パッケージは初期化ファイルのみで具体的実装は未提供（将来のリリースで追加予定）。
- research の実装は外部ライブラリに依存しない設計だが、大規模データ処理の最適化（並列化や pandas 併用）は今後検討。
- news_collector の RSS ソースはデフォルトで Yahoo Finance のカテゴリ RSS のみを設定。ソース追加は引数で可能。

---

著者: KabuSys 開発チーム  
初版: 0.1.0 (2026-03-19)