# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
データ収集（J-Quants）、ETL、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（DuckDBベース）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよび研究プラットフォーム向けの共通ユーティリティ群です。主に以下の役割を持ちます。

- J-Quants API を用いた株価・財務・カレンダー等の取得と DuckDB への保存（ETL）
- RSS ニュース収集と前処理
- OpenAI（gpt-4o-mini 等）によるニュースセンチメント解析（銘柄単位・マクロ）
- 市場レジーム判定（ETF の MA200 乖離 + マクロセンチメント）
- ファクター（モメンタム・バリュー・ボラティリティ等）算出・解析ユーティリティ
- データ品質チェック
- 監査ログ（シグナル→発注→約定のトレーサビリティ）テーブル初期化ユーティリティ

設計上の特徴:
- Look-ahead バイアスを避けるため、内部で日付を固定的に扱う（datetime.today() を直接使わない等）
- DuckDB を主要なローカルDB として用いる（軽量かつ高速）
- API 呼び出しに対するリトライ/バックオフやレート制御を備える
- 冪等的な DB 保存（ON CONFLICT / upsert）を行う

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants からのデータ取得（daily_quotes, financials, market_calendar, listed_info）
  - DuckDB への保存 (save_daily_quotes, save_financial_statements, save_market_calendar)
  - API レート制御・リトライ・トークン自動リフレッシュを実装

- data/pipeline.py
  - run_daily_etl：日次の ETL パイプライン（calendar → prices → financials → 品質チェック）
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETLResult 型による結果返却・品質問題の集約

- data/news_collector.py
  - RSS フィード取得、前処理、raw_news への冪等保存、news_symbols との紐付け補助
  - SSRF / Gzip bomb / トラッキングパラメータ除去等の安全対策実装

- ai/news_nlp.py
  - 銘柄ごとのニュースをまとめて OpenAI に投げ、銘柄毎の ai_score を ai_scores テーブルへ保存
  - バッチ処理、リトライ、レスポンス検証を実装

- ai/regime_detector.py
  - ETF(1321) の 200 日 MA 乖離とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）を判定し保存

- research/*
  - ファクター計算（calc_momentum, calc_value, calc_volatility）や特徴量探索（forward returns, IC, summary）を提供

- data/quality.py
  - 欠損・重複・スパイク・日付不整合のチェック群。QualityIssue で詳細を返す

- data/audit.py
  - 監査ログ（signal_events / order_requests / executions）のスキーマ作成・初期化（init_audit_schema / init_audit_db）

- config.py
  - 環境変数 / .env 読み込みユーティリティ（自動ロード機構）と Settings オブジェクト

---

## セットアップ手順

前提
- Python >= 3.10（型アノテーションで PEP 604 の `X | Y` を使用）
- DuckDB, OpenAI SDK 等が必要（以下は最低限の例）

1. リポジトリをクローン、仮想環境を作成

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール（例）

   requirements.txt がない場合は最低限以下をインストールしてください:

   ```bash
   pip install duckdb openai defusedxml
   ```

   （プロジェクトで使用する他のパッケージがある場合は適宜追加してください）

3. 環境変数の設定

   プロジェクトルートに .env を配置すると自動で読み込まれます（.env.local が上書き）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   .env の例:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   必須環境変数（Settings が raise するもの）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   OpenAI の API キーは `OPENAI_API_KEY` または ai 関数呼び出し時の `api_key` 引数で供給できます。

4. データディレクトリの作成（必要に応じて）

   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下は最小限の利用例です。DuckDB 接続には `duckdb.connect()` を用います。

1. 日次 ETL を実行する

   ```python
   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

   run_daily_etl は ETLResult を返し、各種フェッチ・保存件数や品質チェックの結果を含みます。

2. ニュースの NLP スコアを生成する（OpenAI API 使用）

   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   # OPENAI_API_KEY が環境変数に設定されていれば api_key は不要
   written = score_news(conn, target_date=date(2026, 3, 20))
   print(f"書き込み銘柄数: {written}")
   ```

3. 市場レジーム判定を行う

   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

4. 監査ログ用 DB を初期化する

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn を使って order_requests / signal_events / executions を操作できます
   ```

5. 監視・品質チェックを個別に実行する

   ```python
   from kabusys.data import quality
   import duckdb
   from datetime import date

   conn = duckdb.connect("data/kabusys.duckdb")
   issues = quality.run_all_checks(conn, target_date=date(2026, 3, 20))
   for i in issues:
       print(i)
   ```

注意点:
- OpenAI 呼び出しや J-Quants API 呼び出しは外部ネットワークを伴います。テスト時は各モジュールの `_call_openai_api` などをモック可能です。
- 多くの関数は「Look-ahead バイアス」を排除するため、内部で現在日時を直接参照しない設計です。バックテスト時は target_date を明示的に指定してください。

---

## 環境設定の挙動（config.py）

- .env / .env.local はプロジェクトルート（.git または pyproject.toml の存在を基準）から自動読み込みされます。
  - 優先順位: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Settings により次のプロパティを取得できます:
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url
  - slack_bot_token, slack_channel_id
  - duckdb_path, sqlite_path
  - env (development | paper_trading | live), log_level
  - is_live / is_paper / is_dev

---

## ディレクトリ構成

主要ファイルとサブパッケージのツリー（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - (その他のデータユーティリティ)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/（ユーティリティ）
    - ai/（NLP・レジーム関連）
    - data/（ETL・品質・監査・J-Quants client）
    - monitoring/, strategy/, execution/ （パッケージ公開対象として __all__ に定義ありが想定される）

この README のコード例は DuckDB 接続や環境変数設定が前提です。実運用では DB スキーマの初期化やマイグレーション、ジョブスケジューラ（cron / Airflow 等）からの定期実行、監視（Slack 通知等）を組み合わせてください。

---

## 開発・テストに関して（簡易ガイド）

- 単体テストを書く際は外部 API 呼び出しをモックしてください。
  - news_nlp._call_openai_api や regime_detector._call_openai_api、jquants_client._request、news_collector._urlopen などは差し替えが想定されています。
- config の自動 .env 読み込みはテストで邪魔になる場合、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ライセンス / 貢献

（ここにライセンス情報や貢献ルールを追記してください）

---

他に README に追加したい内容（例: CI 設定、サンプル .env.example、より具体的な実行手順や Dockerfile、マイグレーション方法など）があれば教えてください。必要に応じて追記・改善します。