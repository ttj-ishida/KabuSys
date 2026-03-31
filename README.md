# KabuSys

日本株向けの自動売買・データ基盤ライブラリ / フレームワークです。  
J-Quants や kabuステーション、OpenAI（LLM）など外部サービスと連携して、データ収集（ETL）、品質チェック、ニュースセンチメント解析、マーケットレジーム判定、研究用ファクター計算、監査ログ等を提供します。

---

## 主な特徴（概要）
- J-Quants API を用いた株価・財務・カレンダーの差分取得と DuckDB への冪等保存
- ニュース収集（RSS）→ raw_news 保存と銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別 / マクロ）
- ETF（1321）200日移動平均乖離＋マクロセンチメントの合成による市場レジーム判定
- ETL パイプライン（差分取得、バックフィル、品質チェック）の単一エントリポイント
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化
- 研究用ユーティリティ（モメンタム・バリュー・ボラティリティ等のファクター計算、IC / 前方リターン計算、Zスコア正規化）

---

## 機能一覧（モジュール単位）
- kabusys.config
  - .env ファイル / 環境変数の自動読み込み（プロジェクトルート検出）。必須設定取得ユーティリティ。
- kabusys.data
  - jquants_client: J-Quants API 呼び出し・保存・ページネーション・認証リフレッシュ・レート制御
  - pipeline: 日次 ETL（run_daily_etl 等）、個別 ETL ジョブ（run_prices_etl 等）
  - news_collector: RSS 取得・前処理・SSRF対策・raw_news 保存処理
  - calendar_management: 市場カレンダー管理、営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ用テーブル定義・初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の汎用統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.score_regime: ETF 200日 MA 乖離 + マクロニュースで市場レジームを算出して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提・依存関係
- Python 3.10+
  - （typing の | 記法や typing 拡張、from __future__ import annotations を利用）
- ランタイム依存（主なもの）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- その他標準ライブラリ（urllib, json, logging, datetime 等）

（プロジェクトに requirements.txt / pyproject.toml があればそちらを優先してください）

---

## セットアップ手順

1. リポジトリをクローン / ワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - 例: pip を使う場合
     ```
     pip install -U pip
     pip install duckdb openai defusedxml
     ```
   - もし pyproject.toml / requirements.txt がある場合はそれを使ってください:
     ```
     pip install -e .
     # または
     pip install -r requirements.txt
     ```

4. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動でロードされます（自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須（主要なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API のパスワード（発注系を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知を使用する場合の Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI 呼び出しを行う場合に必要（score_news / score_regime に渡すことも可）
   - 例 `.env`:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     LOG_LEVEL=INFO
     KABUSYS_ENV=development
     ```

5. データベースファイル（DuckDB）用ディレクトリを作る（必要なら）
   - デフォルトの DuckDB パス: data/kabusys.duckdb
   - 監査用 DB の初期化には以下を利用できます（init_audit_db が親ディレクトリを作成します）。

---

## 使い方（主要な例）

以下はライブラリを直接 Python から使う簡単な例です。実運用ではジョブスケジューラ（cron / Airflow 等）から呼び出してください。

- DuckDB 接続と ETL の実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  # 日次 ETL（当日）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（LLM）を計算して保存
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date に対するニュースウィンドウ（前日15:00〜当日08:30 JST）を対象にスコア化
  written = score_news(conn, target_date=date(2026, 3, 20))  # 戻り値は書き込んだ銘柄数
  print("written:", written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメント合成）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/monitoring_audit.duckdb")
  # conn を使って監査ログを記録していく
  ```

- カレンダー更新ジョブ（J-Quants から市場カレンダー取得）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  calendar_update_job(conn)
  ```

- 設定値参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.is_live)
  ```

注意:
- score_news / score_regime は OpenAI API キー（api_key 引数または OPENAI_API_KEY 環境変数）を必要とします。
- run_daily_etl 等は DB のテーブルスキーマ前提です。初回はスキーマ作成処理を別途行うか、ETL を実行するコードからスキーマ準備を行ってください（schema 初期化用ユーティリティがある可能性があります）。

---

## 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: 必須。J-Quants リフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD: kabu API のパスワード（発注を行う場合）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しで使用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment: development / paper_trading / live
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化

---

## テスト・開発時のヒント
- 自動で .env を読み込む仕組みはプロジェクトルート（.git または pyproject.toml）から探索します。テストで環境を汚したくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分（_call_openai_api）はユニットテストでパッチしやすいように設計されています（モック差替え可能）。
- jquants_client はネットワーク・レート制御・リトライ・トークンリフレッシュを備えています。テストでは get_id_token や _request をモックしてください。
- news_collector は SSRF 対策やサイズ上限を備えています。fetch_rss/_urlopen をモックすると容易にユニットテスト可能です。

---

## ディレクトリ構成（主要ファイル）
（抜粋・説明付き）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動ロードと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（銘柄別）と score_news
    - regime_detector.py — マクロセンチメント＋ETF MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - news_collector.py — RSS 収集・前処理・保存
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - quality.py — データ品質チェック（missing/spike/duplicates/date consistency）
    - stats.py — zscore_normalize 等
    - audit.py — 監査ログ用スキーマ / init_audit_db
    - etl.py — ETLResult を公開（再エクスポート）
  - research/
    - __init__.py
    - factor_research.py — momentum, value, volatility 等の計算
    - feature_exploration.py — 前方リターン, IC, 統計サマリー 等
  - research モジュールはバックテストや研究用途に使える純粋な計算ユーティリティ群です。

その他:
- README.md（このファイル）
- .env.example（存在する場合は各種環境変数の例を確認してください）

---

## ライセンス・貢献
- ライセンス情報や貢献ガイドラインがプロジェクトルートにあればそちらに従ってください。

---

README は主要な使い方と設定をまとめたものです。必要であれば、具体的な schema 初期化スクリプトやサンプル ETL 実行スクリプト、CI / デプロイ手順、運用上の注意（本番口座での発注フロー、安全対策）などのドキュメントも追加できます。追加したい項目があれば教えてください。