# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants からのデータ取得（ETL）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログスキーマ、ファクター／研究ユーティリティなどを含みます。

主な用途:
- J-Quants からの日次データ ETL（株価・財務・市場カレンダー）
- RSS ニュース収集と LLM による銘柄別センチメント算出（ai_scores）
- マクロニュースと ETF MA を使った日次市場レジーム判定
- 監査テーブル（シグナル → 発注 → 約定）初期化ユーティリティ
- 研究向けファクター計算・特徴量解析ユーティリティ

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local をプロジェクトルートから自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants API クライアント（kabusys.data.jquants_client）: レート制御・リトライ・トークン自動リフレッシュ
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合検出
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / next/prev trading day / calendar_update_job（J-Quants から取得）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・正規化・SSRF対策・DB への冪等保存を想定
- LLM ベースのニュース分析（kabusys.ai.news_nlp）
  - gpt-4o-mini（JSON Mode）で銘柄ごとのセンチメントを算出し ai_scores に書き込み
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の 200 日 MA 乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成して market_regime に保存
- 研究用ユーティリティ（kabusys.research）
  - momentum/volatility/value 等のファクター計算、forward return、IC、統計サマリー
- 監査ログ初期化（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル作成・インデックス設定

---

## セットアップ手順

前提:
- Python 3.10 以上推奨（PEP 604 の型表記を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS 等）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   （requirements.txt がない場合は以下をインストール）
   ```
   pip install duckdb openai defusedxml
   ```
   必要に応じて他のライブラリを追加してください（例: requests 等）。

4. 環境変数の設定
   プロジェクトルートに `.env` を作成することで自動的に読み込まれます（.env.local は上書き）。
   例: `.env`（実際の値は適切に保護してください）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
   自動ロードを無効にする場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な API の例）

以下はライブラリ API を直接呼ぶ簡単な例です。実運用ではジョブスクリプトやワーカーから呼び出してください。

- DuckDB 接続（例）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略時は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（ai_scores へ書き込む）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"書き込んだ銘柄数: {count}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査ログ DB 初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- カレンダー更新ジョブ（J-Quants から差分取得）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from datetime import date
  saved = calendar_update_job(conn)
  print(f"保存件数: {saved}")
  ```

- 研究系: モメンタム計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意点:
- OpenAI を使う関数は api_key 引数を受け取ります。指定しない場合は環境変数 OPENAI_API_KEY を参照します。
- ETL / API 呼び出しはネットワークや API レートの影響を受けます。ログや例外に注意してください。
- DuckDB の executemany に空リストを渡すとエラーとなる箇所があるため、ライブラリは内部でガードしています。呼び出し側でも注意ください。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（LLM を利用する機能で必要）
- SLACK_BOT_TOKEN: Slack 通知用トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化する場合に "1" を設定

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境設定の読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI）と ai_scores 書き込み
    - regime_detector.py           — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult 再エクスポート
    - stats.py                     — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py                   — データ品質チェック
    - calendar_management.py       — 市場カレンダー管理
    - news_collector.py            — RSS 取得・前処理・保存（raw_news）
    - audit.py                     — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Value / Volatility 等
    - feature_exploration.py       — forward returns, IC, サマリー等
  - research/*.py
- data/                              — デフォルトの DB 出力先（推奨）
  - kabusys.duckdb
  - monitoring.db
- .env.example                       — （推奨して用意）必要な環境変数の例

---

## ロギングと実行モード

- settings.env による KABUSYS_ENV（development / paper_trading / live）で挙動を変更可能。
- LOG_LEVEL によりログ出力を調整してください（INFO 推奨、デバッグ時は DEBUG）。

---

## テスト・開発メモ

- LLM / 外部 API 呼び出しはモックしやすい設計（内部の _call_openai_api やネットワーク関数を patch 可能）。
- DuckDB を利用しているため、テストでは ":memory:" 接続を使うと便利（kabusys.data.audit.init_audit_db 関数は ":memory:" をサポート）。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を検索）を基準に行います。テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して読み込みを抑制してください。

---

## ライセンス / 貢献

（該当するライセンス情報・貢献手順をここに追加してください）

---

必要であれば、利用例のスクリプトや systemd / cron / Airflow 用のジョブ定義サンプル、.env.example のテンプレートを追加で作成します。どの部分を優先して補足しましょうか？