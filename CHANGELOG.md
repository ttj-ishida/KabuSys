# CHANGELOG

全般仕様: 本リリースは初回の公開版です。以下はソースコードから推測した主要な追加機能・実装上の注意点を日本語でまとめています。

フォーマットは "Keep a Changelog" 準拠。

## [0.1.0] - 2026-03-19

### Added
- 基本パッケージ構成
  - パッケージエントリポイント: `kabusys`（src/kabusys/__init__.py）。公開 API: data, strategy, execution, monitoring。
  - 空のサブパッケージプレースホルダ: `kabusys.strategy`, `kabusys.execution`（拡張用）。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - プロジェクトルート自動検出ロジック: `.git` または `pyproject.toml` を基準に .env 自動読み込みを行う（CWD に依存しない）。
  - .env ファイルのパース実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いなどをサポート。
  - 自動ロードの制御: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - Settings クラス: J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等をプロパティ経由で取得。必須 env が未設定のときは明示的に例外を発生。

- データ取得クライアント（J-Quants）（src/kabusys/data/jquants_client.py）
  - レート制限制御: 固定間隔スロットリング（120 req/min）を実装する `_RateLimiter`。
  - 再試行ロジック: 指数バックオフ、最大リトライ回数 3、HTTP 408/429/5xx に対するリトライ、429 の場合は Retry-After を尊重。
  - トークン管理: リフレッシュトークンから ID トークンを取得する `get_id_token()`、モジュールレベルのトークンキャッシュ、401 受信時の自動リフレッシュ（1 回）をサポート。
  - ページネーション対応の取得関数:
    - `fetch_daily_quotes()`（日足）
    - `fetch_financial_statements()`（財務）
    - `fetch_market_calendar()`（マーケットカレンダー）
  - DuckDB への冪等保存関数:
    - `save_daily_quotes()`, `save_financial_statements()`, `save_market_calendar()` は ON CONFLICT を用いて重複更新を回避。
  - 型変換ユーティリティ: `_to_float()` / `_to_int()`（安全な None/空文字処理・float 文字列からの int 変換時の丸め検査など）。

- ニュース収集（RSS）モジュール（src/kabusys/data/news_collector.py）
  - RSS 取得と前処理:
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリキーソート）と SHA-256 ベースの記事ID生成（先頭32文字）。
    - テキスト前処理: URL 除去、空白正規化。
    - pubDate のパースと UTC 正規化（失敗時は警告ログと現在時刻を代替）。
  - セキュリティ / 頑健性:
    - SSRF 対策: リダイレクト時のスキーム検証・プライベートアドレス検査（`_SSRFBlockRedirectHandler`、`_is_private_host`）を実装。
    - defusedxml を利用して XML 攻撃（XML bomb 等）に対処。
    - レスポンスサイズ上限チェック（デフォルト 10MB）および gzip 解凍後の再チェック（Gzip bomb 対策）。
    - 許可スキームは http/https のみ。
  - DB 保存:
    - `save_raw_news()` はチャンク分割で INSERT ... RETURNING を利用し、実際に挿入された記事 ID を返す（冪等保存）。
    - `save_news_symbols()` / `_save_news_symbols_bulk()` により news と銘柄コードの紐付けを効率的に保存（ON CONFLICT で重複スキップ）。
  - コード抽出:
    - 4桁数字パターンによる銘柄コード抽出（既知コードセットでフィルタ）`extract_stock_codes()`。
  - 統合ジョブ:
    - `run_news_collection()`：複数 RSS ソースを回して記事取得→保存→銘柄紐付けを行う。ソース単位でエラーを孤立させる設計。

- 研究（Research）モジュール（src/kabusys/research/*）
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: `calc_forward_returns(conn, target_date, horizons=[1,5,21])`（単一クエリで LEAD を使って取得、horizons の検証あり）。
    - IC（Information Coefficient）計算: `calc_ic(factor_records, forward_records, factor_col, return_col)`（スピアマンの ρ をランクから算出、レコード不足時は None）。
    - 基本統計量: `factor_summary(records, columns)`（count/mean/std/min/max/median）。
    - ランク変換: `rank(values)`（同順位は平均ランク、丸め誤差対策に round(v, 12) を適用）。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: `calc_momentum(conn, target_date)` → mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離。データ不足時は None）。
    - Volatility / Liquidity: `calc_volatility(conn, target_date)` → atr_20, atr_pct, avg_turnover, volume_ratio（ATR の null 伝播、カウント条件により不足時は None）。
    - Value: `calc_value(conn, target_date)` → per（EPS が 0/欠損時 None にする）、roe（raw_financials から最新の target_date 以前レコードを取得）。
    - 設計方針として DuckDB の prices_daily / raw_financials のみ参照し、本番発注 API 等にはアクセスしない。

- DuckDB スキーマ初期化（src/kabusys/data/schema.py）
  - Raw レイヤーのテーブル定義（例: raw_prices, raw_financials, raw_news, raw_executions 等）を DDL で提供し、初期化用に利用可能。

- 研究パッケージの公開エクスポート（src/kabusys/research/__init__.py）
  - 主要関数を __all__ で集約して外部から import しやすく整備（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- 初回リリースのため該当なし（新規追加中心）。

### Fixed
- 初回リリースのため該当なし（実装上の堅牢性・入力検証は複数箇所で考慮済み）。
  - 例: calc_forward_returns の horizons 検証（正の整数かつ <=252）、rank() の丸めによる ties 処理、_to_int の小数部検査など。

### Security
- RSS パーサーに defusedxml を採用して XML 関連攻撃に対処。
- SSRF 対策を導入（リダイレクト時の検証、ホスト/IP のプライベートアドレスチェック、スキーム検証）。
- RSS のレスポンスサイズ上限・gzip 解凍後のサイズ検証を実装してメモリ DoS を緩和。

### Notes / Migration
- 環境変数は Settings のプロパティ経由で取得することを推奨（未設定時は例外が発生するため、`.env` の用意や OS 環境変数の設定が必要）。
- 自動 .env ロードはプロジェクトルートの検出に基づくため、パッケージを別場所に配置して使う場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定のうえ手動で環境をセットアップすること。
- DuckDB スキーマ（DDL）は既存 DB に対して互換性のある変更を行う際は注意（PRIMARY KEY 定義やカラム制約など）。初回は DDL に従って初期化してください。
- J-Quants API クライアントはレート制限とリトライを備えるが、実運用時は API 利用状況に応じた監視とロギング設定の調整を推奨。

---

（将来のリリースでは "Changed"/"Fixed"/"Security" に具体的な差分を都度追記してください。）