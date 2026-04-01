# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、リサーチ用ファクター計算、AI を用いたニュースセンチメント、監査ログ（約定トレーサビリティ）、市場レジーム判定などの機能を提供します。

---

## 主要ポイント（概要）
- DuckDB をデータ基盤として利用し、J-Quants API から株価・財務・市場カレンダーを差分取得して保存する ETL パイプラインを提供します。
- RSS からニュースを収集し、OpenAI（gpt-4o-mini 等）を用いた銘柄別 / マクロセンチメント評価を行います。
- リサーチ用途のファクター計算（モメンタム、バリュー、ボラティリティ等）・特徴量解析ユーティリティを提供します。
- 発注・約定までの監査ログテーブル（監査スキーマ）を初期化・管理する機能があります。
- 環境変数・`.env` 自動読み込み、堅牢なエラー/リトライ処理、Look-ahead バイアス対策（時刻参照の取り扱い）を考慮した設計。

---

## 機能一覧
- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（優先度: OS env > .env.local > .env）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）
- データ取得・ETL（kabusys.data.pipeline, jquants_client）
  - J-Quants からの株価/財務/カレンダー取得（ページネーション対応・レートリミッティング・リトライ）
  - DuckDB へ冪等保存（ON CONFLICT による上書き）
  - ETL 実行関数 run_daily_etl（品質チェックオプションあり）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合などの検出
- ニュース収集・NLP（kabusys.data.news_collector, kabusys.ai.news_nlp）
  - RSS 収集（SSRF 防御、URL 正規化、トラッキングパラメータ除去）
  - OpenAI を用いた銘柄別 sentiment（score_news）
  - マクロ記事を用いた市場レジーム判定（score_regime）
- リサーチ / ファクター計算（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等の定量ファクター（calc_momentum 等）
  - 将来リターン計算、IC 計算、統計サマリー
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions の DDL 作成、インデックス、初期化（init_audit_schema / init_audit_db）
- ユーティリティ（kabusys.data.stats 等）
  - Z スコア正規化などの統計ユーティリティ

---

## 必要条件（例）
- Python 3.10+
- 主要ライブラリ（一例）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトで requirements.txt があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン / コピー
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトに requirements があれば:
   # pip install -r requirements.txt
   ```

4. 開発インストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数を設定（.env ファイル推奨）
   - 自動読み込み: パッケージはプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込みます。OS 環境変数が優先されます。
   - 自動読み込みを無効にするには: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

   例: `.env`（最低限）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

- DuckDB 接続を作って ETL を実行する（簡単なスクリプト例）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- OpenAI を使ってニューススコアを付与（score_news）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定（score_regime）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで監査用テーブルが作成されます
  ```

- リサーチ用関数（例: モメンタム計算）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点:
- score_news / score_regime は OpenAI API キーを必要とします（環境変数 OPENAI_API_KEY または関数の api_key 引数）。
- ETL / データ取得は J-Quants の認証トークン（JQUANTS_REFRESH_TOKEN）を必要とします（設定は settings.jquants_refresh_token 経由で取得）。
- 各種関数はルックアヘッドバイアス対策のため、内部で date.today() を参照せず、引数で date を受け取る設計です（バックテスト適合）。

---

## 主要環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD     : kabu ステーション API のパスワード（発注連携する場合）
- SLACK_BOT_TOKEN       : Slack 通知用ボットトークン（通知機能がある場合）
- SLACK_CHANNEL_ID      : Slack チャンネル ID
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL             : ログレベル ("DEBUG", "INFO", ...)

設定は .env, .env.local, もしくは OS 環境変数で行えます。自動ロードはプロジェクトルートを基準に行われます。

---

## 典型的ワークフロー
1. .env を用意して API キー等をセットアップ
2. DuckDB を用意（`data/` ディレクトリ作成等）
3. 初回に ETL を実行して株価・財務・カレンダーを取得（run_daily_etl）
4. ニュース収集ジョブを定期実行（news_collector.fetch_rss を使い raw_news へ保存）
5. AI スコアリング（score_news） → ai_scores テーブルへ
6. レジーム判定（score_regime） → market_regime テーブルへ
7. リサーチ・バックテストに必要なファクター計算を実行（kabusys.research.*）

---

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント評価（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - pipeline.py            — ETL パイプライン (run_daily_etl 等)
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py — 市場カレンダー管理（営業日ロジック）
    - audit.py               — 監査ログ（監査スキーマ初期化）
    - etl.py                 — ETL 関連の公開インターフェース
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（モメンタム・バリュー・ボラティリティ）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - ai/、research/、data/ 以下に実装ファイル多数

---

## 運用上の注意
- API レート制限・課金に注意（OpenAI / J-Quants）。
- run_daily_etl では品質チェックを行い、問題が検出されても ETL は可能な限り継続して動作します。結果の ETLResult で問題の有無を確認してください。
- News Collector は外部 RSS を取得するため SSRF 対策やレスポンスサイズ制限が実装されています。独自フィードを追加する場合は設定を確認してください。
- 監査ログ（audit schema）は冪等で初期化できます。既存 DB に追加する場合の transactional オプションに注意してください（DuckDB のトランザクション性）。

---

この README はコードベースの主要機能の要約です。詳細な API 仕様や使用例は各モジュール（kabusys.data.pipeline、kabusys.ai.news_nlp、kabusys.data.jquants_client など）の docstring を参照してください。必要であればサンプル設定ファイル（.env.example）や運用手順書を別途作成します。