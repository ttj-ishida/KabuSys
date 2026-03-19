# CHANGELOG

すべての重要なリリース変更をここに記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。  

最新リリース: 0.1.0

未リリースの変更はここに記載します。
（現時点では特に未リリース項目はありません）

## [0.1.0] - 2026-03-19

初回公開リリース。以下の主要機能・実装が追加されました。

### 追加 (Added)
- パッケージエントリポイント
  - src/kabusys/__init__.py: パッケージ名とバージョン（0.1.0）、公開モジュール一覧（data, strategy, execution, monitoring）を定義。

- 設定 / 環境変数管理
  - src/kabusys/config.py:
    - .env ファイル自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサーは export 形式・クォート・インラインコメント等に対応。
    - protected（OS 環境変数）の概念を導入し、override 時に保護。
    - Settings クラスで各種必須設定をプロパティとして提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャネル、DB パス等）。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）と is_live/is_paper/is_dev ヘルパーを提供。

- データ取得・永続化 (J-Quants)
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアントを実装。
    - レート制限制御（_RateLimiter: 固定間隔スロットリング, 120 req/min）。
    - リトライ戦略（指数バックオフ、最大 3 回。HTTP 408/429 と 5xx を再試行対象）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみリトライ）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT DO UPDATE を使用して重複を排除。
    - 型変換ユーティリティ _to_float / _to_int（不正値や空値を安全に None に変換）。

- ニュース収集（RSS）
  - src/kabusys/data/news_collector.py:
    - RSS フィードの取得、記事正規化、DuckDB への永続化を行うニュース収集モジュールを実装。
    - セキュリティ対策:
      - defusedxml を利用した XML パース（XML bomb 等への耐性）。
      - SSRF 対策: 初期ホスト検査、リダイレクト時のスキーム・ホスト検査用ハンドラ (_SSRFBlockRedirectHandler)、プライベート IP 判定。
      - URL スキーム検証（http/https のみ許可）。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES、デフォルト 10MB）と gzip 解凍後のサイズ検査。
    - URL 正規化: トラッキングパラメータ（utm_* 等）除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - fetch_rss: RSS をパースして NewsArticle 型のリストを返す（content:encoded を優先、pubDate パース処理を実装）。
    - DB 保存:
      - save_raw_news: チャンク化して INSERT ... RETURNING id を用い、実際に挿入された記事IDのリストを返す（トランザクションでまとめる）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT で重複スキップ、チャンク化）。
    - 銘柄抽出: 4桁数字パターンを用いた extract_stock_codes 実装（known_codes によるフィルタと重複除去）。
    - run_news_collection: 複数 RSS ソースの統合収集ジョブ（各ソースは独立してエラーハンドリング、既知銘柄との紐付け処理を実行）。

- DuckDB スキーマ定義 / 初期化
  - src/kabusys/data/schema.py:
    - Raw 層テーブルの DDL を定義（raw_prices, raw_financials, raw_news, raw_executions 等のスキーマ定義を含む）。
    - DataSchema.md に基づく 3 層（Raw / Processed / Feature、Execution）構造の方針を記述。

- 研究（Research）モジュール
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、単一クエリでまとめ取得、結果は None 許容）。
    - スピアマン IC 計算 calc_ic（ランク計算・欠損除外・有効レコード数チェック）。
    - ランク関数 rank（同順位は平均ランク、浮動小数の丸めで ties 検出安定化）。
    - factor_summary（count/mean/std/min/max/median の算出、None 排除）。
    - 設計方針: DuckDB の prices_daily を参照のみ、外部 API にはアクセスしない、標準ライブラリのみで実装。
  - src/kabusys/research/factor_research.py:
    - モメンタム（mom_1m, mom_3m, mom_6m, ma200_dev）計算 calc_momentum。
    - ボラティリティ / 流動性（atr_20, atr_pct, avg_turnover, volume_ratio）計算 calc_volatility（ATR の true_range 計算に注意）。
    - バリュー（per, roe）計算 calc_value（raw_financials から target_date 以前の最新財務情報を結合）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し、結果を (date, code) をキーとする dict リストで返す。
  - src/kabusys/research/__init__.py:
    - 主要ユーティリティを __all__ にまとめて公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- その他
  - 空のパッケージ初期化ファイルを配置（src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py）。将来的な実装用のプレースホルダ。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector に複数の SSRF 緩和策を実装（スキーム制限、プライベート IP 判定、リダイレクト時の検査、受信サイズ制限、defusedxml 使用）。
- jquants_client の HTTP リクエストでのリトライ制御により、一時的なネットワーク障害やレート制限応答に対して堅牢化。

### 既知の注意点 / 補足 (Notes)
- 本リリースでは strategy / execution の具象実装は未提供（パッケージのプレースホルダのみ）。
- DuckDB 連携を多用するため、実行環境には duckdb が必要。
- news_collector は既知銘柄セット（known_codes）が与えられない場合は紐付け処理をスキップします。
- jquants_client は J-Quants のリフレッシュトークンを環境変数（JQUANTS_REFRESH_TOKEN）で受け取ります。settings の必須設定に従い .env を準備してください。

---

今後のリリースでは、strategy / execution の実装、より詳細なドキュメント・ユニットテスト、API クライアントの追加エンドポイント対応などを予定しています。