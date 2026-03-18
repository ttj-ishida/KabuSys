# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python パッケージです。データ取得・ETL、特徴量計算、研究用ユーティリティ、ニュース収集、監査ログ（発注トレーサビリティ）など、トレーディングシステムのバックエンド処理を幅広くカバーします。

主な設計方針：
- DuckDB を中心としたローカルデータレイク（Raw / Processed / Feature / Execution 層）
- J-Quants API など外部データソースとの安全で冪等な連携
- 研究（Research）用途のファクター計算／IC 計算等を標準ライブラリだけで実装
- セキュリティ（SSRF 対策、XML の安全パース等）を考慮

---

## 機能一覧

- 環境変数 / .env 管理
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可能）
- データ取得（J-Quants）
  - 日足（OHLCV）取得・ページネーション対応
  - 財務データ取得（四半期 BS/PL）
  - 市場カレンダー取得
  - レート制限・リトライ・トークン自動リフレッシュを備えたクライアント
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - 監査ログ（order/signal/execution）の専用スキーマ初期化
- ETL パイプライン
  - 差分取得（最新日確認）、バックフィル、保存（冪等）をまとめて実行
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集
  - RSS 取得、本文前処理、記事ID生成、DuckDB への冪等保存
  - SSRF 回避、受信サイズ制限、defusedxml による安全な XML パース
  - 銘柄コード抽出（テキスト中の 4 桁コード）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、Z スコア正規化
- 監視 / 監査
  - 監査用テーブル（signal_events / order_requests / executions）と索引
- 汎用統計ユーティリティ（外部ライブラリに依存しない実装）

---

## セットアップ手順（開発向け）

1. リポジトリをクローンして仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存ライブラリをインストール
   - 最低限必要なパッケージ（例）
     ```bash
     pip install duckdb defusedxml
     ```
   - プロジェクトをパッケージとしてインストール（開発時は -e 推奨）
     ```bash
     pip install -e .
     ```
   - ※ requirements.txt / pyproject.toml がある場合はそれに従ってください。

3. 環境変数の設定
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルトあり）:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB（例）: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
   - プロジェクトルートの `.env` / `.env.local` を用いることができます。自動ロードを無効にしたいテスト等では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## 使い方（主要な操作例）

以下は基本的な利用フローの抜粋です。詳細は各モジュールのドキュメント（ソース内 docstring）を参照してください。

- 設定を参照する
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.env)  # development / paper_trading / live
  ```

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成
  ```

- 日次 ETL を実行する（J-Quants からデータを取得して DuckDB に保存、品質チェック含む）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes を渡すと本文から銘柄コード抽出して紐付けを行う
  known_codes = {"7203", "6758", "9984"}  # 事前に用意した銘柄コードセット
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # ソースごとの新規保存数
  ```

- 研究用ファクター計算例
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- J-Quants Client の直接利用例
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  token = get_id_token()  # settings.jquants_refresh_token を使用して ID トークンを取得
  rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, rows)
  ```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabuAPI ベース URL（オプション、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH / SQLITE_PATH: データ格納パス（任意、デフォルト値あり）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化するには 1 をセット

注意: settings（kabusys.config.Settings）はこれらをプロパティ経由で検証・取得します。必須変数が未設定の場合は ValueError が投げられます。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なファイル／モジュール構成は以下の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数読み込み・設定管理
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（rate limit / retry / save_*）
    - news_collector.py  — RSS ニュース収集・保存・銘柄紐付け
    - schema.py  — DuckDB スキーマ定義と初期化
    - pipeline.py  — ETL パイプライン（差分取得 / 品質チェック）
    - quality.py  — データ品質チェック
    - calendar_management.py — market_calendar 管理・営業日判定
    - audit.py  — 監査ログ（signal/order/execution）スキーマ
    - stats.py  — z-score 等の統計ユーティリティ
    - features.py — features への公開インターフェース（zscore_normalize 再エクスポート）
    - etl.py — ETLResult 再エクスポート
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン / IC / サマリー等
    - factor_research.py — momentum / volatility / value のファクター計算
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

---

## 運用上の注意

- J-Quants API のレート制限（120 req/min）を遵守するため、クライアント側でスロットリングを行っています。大量取得時は十分な間隔・バッチ化を検討してください。
- DuckDB への挿入は冪等性（ON CONFLICT）を基本にしていますが、外部からの手動操作やスキーマ変更には注意が必要です。
- ニュース収集では SSRF や XML Bomb を考慮していますが、公開インターネットアクセス時の環境設定（プロキシ等）に注意してください。
- 本システムは取引（発注）ロジックを含む場合、実運用（特に live 環境）では厳格なレビューと十分なテストが必要です。KABUSYS_ENV を正しく使い分けてください。

---

## 貢献

バグ報告や機能提案は Issue を立ててください。Pull Request はコード規約に沿ったドキュメンテーション付きでお願いします。

---

この README はソースコード内の docstring を基に要点をまとめています。細かな挙動や引数、戻り値等は各モジュールの docstring を参照してください。