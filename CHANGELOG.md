# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従っています。  

格式:
- Unreleased: 開発中の変更（将来リリース予定）
- 各リリース: バージョン名と日付、カテゴリ別の変更点

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回公開リリース。本バージョンでは日本株自動売買システム「KabuSys」の基盤機能群を提供します。主な追加点は以下のとおりです。

### Added
- パッケージ初期化
  - pakage エントリ `kabusys.__init__` を追加。バージョン情報 `__version__ = "0.1.0"` と公開モジュールリスト `__all__ = ["data", "strategy", "execution", "monitoring"]` を定義。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルと OS 環境変数を統合して設定を管理する `Settings` クラスを提供。
  - 自動 .env ロード機能:
    - プロジェクトルート判定は `.git` または `pyproject.toml` を探索。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト用）。
    - 既存の OS 環境変数を保護するための `protected` ロジックを実装。
  - .env パーサは次をサポート/対処:
    - `export KEY=val` 形式
    - シングル/ダブルクォート内のエスケープ処理
    - インラインコメントの扱い（クォートの有無での挙動を区別）
  - 必須設定を要求する `_require` の実装（未設定時は ValueError）。
  - 主要設定プロパティ:
    - J-Quants 用: `jquants_refresh_token`
    - kabuステーション API: `kabu_api_password`, `kabu_api_base_url`
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`, `sqlite_path`
    - 実行環境判定: `env`, `log_level`, `is_live`, `is_paper`, `is_dev`
  - 設定値の妥当性チェック（env と log_level の許容値検証）

- データ層: J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API 呼び出しユーティリティを実装:
    - レート制限管理: 固定間隔スロットリング（120 req/min をデフォルト）。
    - リトライ: 指数バックオフ、最大 3 回。リトライ対象ステータス 408, 429, 5xx。
    - 401 ハンドリング: トークン自動リフレッシュを1回行って再試行。
    - ページネーション対応の取得ロジック。
    - レスポンス JSON のデコードとエラー報告を行う `_request`。
  - 認証: `get_id_token()`（refresh_token から idToken を取得）。
  - データ取得関数:
    - `fetch_daily_quotes()`, `fetch_financial_statements()`, `fetch_market_calendar()`
  - DuckDB への保存関数（冪等性を考慮）:
    - `save_daily_quotes()` → `raw_prices`
    - `save_financial_statements()` → `raw_financials`
    - `save_market_calendar()` → `market_calendar`
    - 各保存は ON CONFLICT DO UPDATE を利用して重複を解消し、挿入件数をログ出力。
  - 型変換ユーティリティ: `_to_float()`, `_to_int()`（入力の堅牢な処理）

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィード取得と前処理パイプラインを実装:
    - フィード取得: `fetch_rss()`
      - HTTP リダイレクト時に事前検査を行うカスタムハンドラ（SSRF 対策）。
      - スキーム検証（http/https のみ許可）。
      - レスポンスサイズ上限チェック（デフォルト 10MB）と gzip 解凍後の検査（Gzip bomb 対策）。
      - defusedxml を用いた安全な XML パース。
      - タイトル・本文の前処理（URL 除去、空白正規化）。
      - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - DB 保存:
      - `save_raw_news()`: チャンク分割して INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、新規挿入ID を返す。1 トランザクションで実行。
      - `save_news_symbols()`, `_save_news_symbols_bulk()`: news_symbols テーブルへの紐付けをバルク挿入し、挿入件数を正確に返す。
    - 銘柄コード抽出: `extract_stock_codes()`（4桁数字パターンと既知コード集合で重複除去して抽出）。
    - 統合ジョブ: `run_news_collection()`（複数ソースの収集・保存・銘柄紐付けを安全に実行、ソース単位でのエラーハンドリング）
  - セキュリティ対策:
    - SSRF 防止（リダイレクト先のスキーム／プライベート IP 検査）
    - defusedxml による XML 攻撃防御
    - レスポンスサイズ制限と gzip 解凍後の再検査

- DuckDB スキーマ初期化 (`kabusys.data.schema`)
  - Raw レイヤーを中心としたテーブル定義（DDL）を実装:
    - `raw_prices`, `raw_financials`, `raw_news`（および raw_executions の雛形の一部）を CREATE TABLE IF NOT EXISTS で定義。
  - テーブル定義に制約（CHECK、PRIMARY KEY）を含め、データ整合性を高める。

- リサーチ / ファクター計算 (`kabusys.research`)
  - feature_exploration:
    - `calc_forward_returns()`：DuckDB 上の prices_daily を参照して将来リターン（デフォルト [1,5,21]）を一度のクエリで計算。
    - `calc_ic()`：Spearman ランク相関（IC）を計算。欠損・非有限値を除外し、サンプル数が少なければ None を返す。
    - `rank()`：同順位は平均ランクとするランク関数（丸め処理により ties 検出を安定化）。
    - `factor_summary()`：複数カラムの count/mean/std/min/max/median を計算。
  - factor_research:
    - `calc_momentum()`：1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を DuckDB のウィンドウ関数で計算。データ不足時は None を返す。
    - `calc_volatility()`：20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比（volume_ratio）を計算。true_range の NULL 伝播制御に注意。
    - `calc_value()`：raw_financials から最新財務データを取得して PER（EPS が有効な場合）と ROE を計算。
  - 設計方針:
    - DuckDB 接続を受け取り prices_daily / raw_financials のみを参照（外部 API に依存しない、発注 API へはアクセスしない）。
    - 結果は (date, code) をキーにした dict のリストで返す。
    - z-score 正規化ユーティリティ（`kabusys.data.stats.zscore_normalize`）を利用可能（research パッケージからエクスポート）。

### Performance
- 大規模取得/保存に配慮:
  - J-Quants クライアントのレート制限スロットリング。
  - fetch のページネーション対応で重複を回避。
  - news_collector のバッチ/チャンク挿入（_INSERT_CHUNK_SIZE）により SQL 長・パラメータ数を抑制。
  - DuckDB のウィンドウ関数を活用して単一クエリでの集計を実現（calc_forward_returns / calc_momentum 等）。

### Security
- RSS パーサで defusedxml を採用。
- SSRF 対策: URL スキーム検証、プライベート IP 検査、リダイレクト時の再検証。
- レスポンスサイズ制限（メモリ DoS 防止）と Gzip 解凍後の検査。

### Other
- ロギングを各モジュールで適切に出力（info/warning/error/exception）。
- ドキュメント的な docstring と設計方針コメントを各モジュールに記載。

### Changed
- （初版のためなし）

### Fixed
- （初版のためなし）

### Removed
- （初版のためなし）

---

注: 上記はコードベースに含まれるコメントと実装から推測して記載した変更内容／特徴です。実際のリリースノートや将来の変更には、追加の説明や既知の制限事項・互換性情報を付記してください。