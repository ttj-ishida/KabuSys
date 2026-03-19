# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初期リリースを記録しています。

## [0.1.0] - 2026-03-19

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期リリース。
  - __version__ を "0.1.0" に設定。パッケージトップで主要サブモジュールをエクスポート (data, strategy, execution, monitoring)。

- 環境設定管理 (src/kabusys/config.py)
  - Settings クラスを提供し、環境変数からアプリ設定を取得。
  - 必須設定の取得ヘルパー `_require`（未設定時は ValueError を送出）。
  - 自動 .env ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
  - 自動ロードの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサは `export KEY=val`、クォート処理、行内コメント処理に対応。
  - Settings に J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベル判定関数を実装。
  - 環境変数の妥当性チェック: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API からのデータ取得ユーティリティ群を実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を厳守する RateLimiter。
  - リトライ/バックオフ: 最大 3 回、指数バックオフ、HTTP 408/429/5xx に対するリトライ処理。429 の場合は Retry-After ヘッダを優先。
  - 401 時の自動トークンリフレッシュを 1 回だけ行いリトライ。
  - トークンのモジュールレベルキャッシュ（ページネーション間で共有）。
  - ページネーション対応の fetch_* 関数 (fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar)。
  - DuckDB への保存関数 (save_daily_quotes, save_financial_statements, save_market_calendar) は冪等（ON CONFLICT DO UPDATE）で保存。
  - 型変換ユーティリティ `_to_float` / `_to_int` を提供（変換ルール・不正値の扱いを明確化）。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集と raw_news / news_symbols への保存機能を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XMLBomb 等から防御）。
    - URL スキーム検証（http/https のみ許可）、SSRF 防止のためプライベート/ループバック/リンクローカル/マルチキャスト宛先の排除。
    - リダイレクト時に検査するカスタム RedirectHandler（_SSRFBlockRedirectHandler）。
    - 受信サイズ上限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後の上限チェック（Gzip-bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）。
  - テキスト前処理（URL 除去・空白正規化）。
  - DB 保存はチャンク化してトランザクションで実行し、INSERT ... RETURNING により実際に挿入されたID/件数を返す。重複は ON CONFLICT でスキップ。
  - 銘柄コード抽出ロジック（4桁数字パターン \b(\d{4})\b）と既知銘柄集合を用いたフィルタリング。
  - run_news_collection により複数ソースを順次処理し、ソース単位でエラーを隔離。

- 研究（Research）モジュール (src/kabusys/research/)
  - feature_exploration:
    - calc_forward_returns: DuckDB の prices_daily を用いて将来リターン（既定 [1,5,21]）をまとめて計算。
    - calc_ic: ファクター と 将来リターンを code で結合し、スピアマンランク相関（IC）を計算（有効レコード < 3 は None）。
    - rank: 同順位は平均ランクとし、round(v,12) により浮動小数の誤差を吸収。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。データ不足時は None。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算。true_range の NULL 伝播を厳密に扱い、ウィンドウ不足は None。
    - calc_value: raw_financials の最新財務データを取得し PER（EPS=0/欠損時は None）と ROE を計算。
  - いずれの関数も DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみを参照。本番発注 API にはアクセスしない実装。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw Layer の DDL を定義:
    - raw_prices（date, code, ohlcv, turnover, fetched_at）: PK(date, code)、数値チェック制約を含む。
    - raw_financials（code, report_date, period_type, eps, roe 等）: PK (code, report_date, period_type)。
    - raw_news（id, datetime, source, title, content, url, fetched_at）: id が PK。
    - raw_executions（execution_id ...）: テーブル定義の一部を含む（初期定義）。
  - スキーマ初期化の土台を提供。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector にて SSRF 対策、受信サイズ制限、defusedxml 使用など多数の外部入力に対する防御を実装。
- jquants_client でのトークン管理と自動リフレッシュにより認証エラーに対応。

### 既知の制限 / 注意事項 (Notes)
- research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリのみで実装されているため、大規模データや高度な統計処理では性能面や機能面で制限がある可能性があります。
- calc_value は PBR や配当利回りを未実装（将来拡張の余地あり）。
- schema の raw_executions 定義はスニペットの途中で終わっているため、完全な実装は別箇所で補完される想定です。
- .env 自動読み込みはプロジェクトルートの特定に __file__ を起点とするため、特殊な配置や配布後の環境で挙動が異なる場合があります。自動ロードを無効にする環境変数が用意されています。

---

今後の予定:
- Strategy / Execution / Monitoring の具体的な実装追加（発注ロジック・モニタリング・バックテスト等）。
- Feature 層や Processed 層の DDL 完全実装、マイグレーション・管理ユーティリティの追加。
- research の性能改善や外部ライブラリ（numpy/pandas）利用オプションの検討。