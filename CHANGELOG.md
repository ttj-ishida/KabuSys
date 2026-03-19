# Changelog

すべての変更は Keep a Changelog の形式に従います。  
現在のリリース履歴は以下の通りです。

## [Unreleased]
今後の変更に関する項目をここに記載します。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」のコアライブラリを公開します。主に Data / Research / Config 周りの基盤機能を実装しています。

### 追加 (Added)
- パッケージ基礎
  - パッケージのトップレベルを定義（kabusys/__init__.py）。
  - モジュール公開インターフェースに "data", "strategy", "execution", "monitoring" を設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から特定して .env / .env.local を順次読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - OS 環境変数（既存の os.environ）を保護する protected 上書きロジックを実装。
  - .env パーサーを実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - 不正行は無視する堅牢な実装。
  - Settings による必須チェックおよび妥当性検証:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得。
    - KABUSYS_ENV の許容値検査 (development / paper_trading / live)。
    - LOG_LEVEL の検査 (DEBUG/INFO/WARNING/ERROR/CRITICAL)。
    - パス系設定（DUCKDB_PATH / SQLITE_PATH）は pathlib.Path として提供。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API ベース URL / 認証フローを備えたクライアント実装。
  - レート制限制御（固定間隔スロットリング）を実装（120 req/min 想定、_RateLimiter）。
  - 冪等的データ保存:
    - fetch_* 系でページネーション対応。
    - save_daily_quotes / save_financial_statements / save_market_calendar は DuckDB への INSERT ... ON CONFLICT で重複更新を回避。
  - リトライと指数バックオフ:
    - ネットワーク／一部ステータスコード (408, 429, >=500) に対して最大3回のリトライ、429 は Retry-After を尊重。
  - 401 ハンドリング:
    - 401 受信時は ID トークンを自動リフレッシュして 1 回だけリトライするロジックを実装（allow_refresh フラグで再帰回避）。
  - 型変換ユーティリティ:
    - _to_float / _to_int を実装。_to_int は "1.0" を許容するが小数部が非ゼロの float 表現は None を返す等の安全策。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからのニュース収集・保存機能を実装。
  - セキュリティ対策:
    - defusedxml による XML パースで XML Bomb 等を防御。
    - SSRF 対策: リダイレクト先のスキーム / ホストを検証する専用ハンドラ (_SSRFBlockRedirectHandler) と事前のプライベートIPチェック。
    - URL スキーム制限 (http/https のみ)。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後サイズ検査。
    - 不正な Content-Length を検出してスキップ。
  - URL 正規化およびトラッキングパラメータ除去:
    - _normalize_url により utm_* 等のパラメータを除去し、正規化後に SHA-256 ハッシュの先頭32文字で記事IDを生成 (_make_article_id) して冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）。
  - 銘柄コード抽出ユーティリティ:
    - 4桁の数字を候補として known_codes と照合して抽出する extract_stock_codes を実装。
  - DB 保存:
    - save_raw_news: チャンク INSERT + RETURNING を用いて実際に挿入された記事IDのみ返す実装（トランザクションでまとめる）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをバルクで安全に保存（ON CONFLICT DO NOTHING, RETURNING 利用）。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層のためのスキーマ定義を開始。
  - raw_prices, raw_financials, raw_news などの DDL を実装（NOT NULL / CHECK / PRIMARY KEY 等の制約あり）。
  - 初期化用モジュールとして将来のデータレイヤ構築に対応。

- 研究（Research）モジュール (kabusys.research)
  - feature_exploration:
    - calc_forward_returns: 指定日に対する複数ホライズンの将来リターンを DuckDB の prices_daily を参照して一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。小数丸め・NaN/None の取り扱いに配慮。
    - factor_summary: count/mean/std/min/max/median を算出する集計ユーティリティ（None 値除外）。
    - rank: 同順位を平均ランクとして扱うランク計算（丸め誤差対策で round(v, 12) を利用）。
    - 設計方針として標準ライブラリのみで実装（pandas 等の外部依存を回避）。
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily を用いて計算。データ不足は None。
    - calc_volatility: 20日 ATR（atr_20）、atr_pct、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に制御。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得して PER / ROE を計算。EPS が 0/欠損の場合は PER を None にする。
  - research/__init__.py で主要関数群を re-export（zscore_normalize を kabusys.data.stats から参照）。

- その他ユーティリティ
  - ロギング出力や詳細なデバッグ情報を各処理に追加（logger.debug/info/warning/exception を適切に使用）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS 収集に対する SSRF 対策、defusedxml の採用、レスポンスサイズ制限、URL スキーム検証などを実装し、外部入力に起因する脆弱性の軽減を図った。

### 既知の制約 / 注意点 (Notes)
- strategy/ と execution/ パッケージの __init__.py は存在するが具体的な戦略・発注ロジックはまだ実装されていません（プレースホルダ）。
- research.feature_exploration は標準ライブラリのみで実装しており、大規模データ処理時は pandas 等の利用を検討すると良いです。
- DuckDB スキーマ定義は raw 層の DDL を中心に実装済み。Execution レイヤや一部テーブル定義が継続実装中（schema.py の一部が継続）。
- jquants_client のベース URL はコード内定数を使用していますが、settings から上書き可能な仕組み（JQUANTS_REFRESH_TOKEN は必須）を想定しています。
- news_collector の _is_private_host は DNS 解決失敗時に安全側（非プライベート）として通す設計。環境に応じた更なる制限が必要な場合があります。

---

この CHANGELOG は、ソースコードの実装内容から推測して作成しています。実際のリリースノートとして公開する際は、リリース時の差分やテスト結果、追加の設計ノートを反映してください。