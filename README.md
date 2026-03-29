# KabuSys — 日本株自動売買システム（概要ドキュメント）

このリポジトリは日本株のデータ取得・ETL・特徴量生成・ニュースNLP・市場レジーム判定・監査ログ等を含む自動売買プラットフォームのコアライブラリ群です。  
README は日本語で記載しています。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API から株価・財務・カレンダー等の市場データを差分取得して DuckDB に保存する ETL パイプライン
- ニュース記事を収集し、OpenAI（gpt-4o-mini 等）で銘柄別センチメントを算出するニュースNLP
- マクロニュースと ETF（1321）200日移動平均乖離を組み合わせた市場レジーム判定
- 研究用途のファクター計算・特徴量探索ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 発注〜約定までのトレースが可能な監査ログ（DuckDB テーブル設計・初期化）
- 環境変数 / .env 管理ユーティリティ

設計上の特徴：
- Look-ahead bias を避ける実装（date.today / datetime.today を不用意に使用しない）
- 各 API 呼び出しにリトライ・バックオフとフェイルセーフ（失敗時はスキップし続行）を備える
- DuckDB への保存は冪等（ON CONFLICT）で安全に上書き
- テストしやすいように API 呼び出し箇所を差し替え可能にしている

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants API クライアント（トークン管理、ページネーション、レート制限、保存関数）
  - 市場カレンダー管理（営業日判定・next/prev/get_trading_days、calendar_update_job）
  - ニュース収集（RSS フィード取得／正規化／SSRF 対策／raw_news 保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events / order_requests / executions の DDL と初期化）
  - 汎用統計ユーティリティ（zscore_normalize 等）

- ai/
  - news_nlp.score_news: 銘柄ごとにニュースをまとめ、OpenAI に投げて ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime を書き込み

- research/
  - ファクター計算（momentum / value / volatility）
  - 将来リターン・IC・統計サマリー等の探索ユーティリティ

- config
  - 環境変数/.env の自動読み込みと設定値アクセス（settings オブジェクト）

---

## 動作要件（主な依存ライブラリ）

- Python 3.10+
- duckdb
- openai（OpenAI SDK v1 系を想定）
- defusedxml
- そのほか標準ライブラリ（urllib, json, datetime, logging 等）

※ バージョンや追加パッケージはプロジェクトの pyproject.toml / requirements.txt に従ってください（本リポジトリのサンプルコードに基づく必要パッケージ）。

---

## セットアップ手順

1. Python 仮想環境作成（例）

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

2. 依存パッケージをインストール

   requirements.txt / pyproject.toml がない場合は最低限以下をインストールしてください：

   ```bash
   pip install duckdb openai defusedxml
   ```

3. .env ファイルの作成（プロジェクトルートに配置）

   config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

   .env の例:

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabu ステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack（通知等で使用）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678

   # OpenAI（news_nlp / regime_detector で必要）
   OPENAI_API_KEY=sk-...

   # システム
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   # DB パス（省略可）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   必須環境変数（Settings により参照・必須判定されるもの）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   OpenAI のキーは news_nlp / regime_detector を利用する場合に必要（関数の api_key 引数で上書き可能）。

4. DuckDB 初期化（監査ログ DB を別ファイルに作る例）

   Python から監査ログ DB を作成する例:

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

   通常は ETL 等の処理で schema 作成を行うユーティリティを呼ぶ想定です。

---

## 使い方（主なユースケース）

以下は簡単な Python 呼び出し例です。

- 日次 ETL を実行する

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

  - ETL は市場カレンダー → 株価 → 財務 → 品質チェック の順で実行します。
  - J-Quants の id_token は settings.jquants_refresh_token を使って自動的に取得・キャッシュされます。

- ニュースのセンチメントスコアを計算する（ai.news_nlp）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数で設定するか、api_key 引数で渡す
  n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"scored {n} symbols")
  ```

  - タイムウィンドウは前日15:00 JST ～ 当日08:30 JST（UTC変換済み）です。
  - 1チャンク最大 20 銘柄で OpenAI にバッチ送信します。API 局所的エラーはリトライ・スキップ実装あり。

- 市場レジーム判定（ai.regime_detector）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM スコア（重み 30%）を合成して market_regime テーブルに冪等書き込みします。
  - API 失敗時は macro_sentiment を 0.0 にフォールバックします。

- 監査スキーマを初期化する

  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

  または専用 DB を作る:

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

---

## 設計上の注意点（運用上のポイント）

- Look-ahead bias の回避:
  - 各スコアリング・ETL・調整処理は内部で datetime.today() を直接参照せず、呼び出し側が target_date を与えることを期待します。バックテストで現在時刻を誤って使わないよう注意してください。
- 冪等性:
  - DuckDB への保存は ON CONFLICT（INSERT ... ON CONFLICT DO UPDATE）により冪等化されています。ETL の再実行は安全です。
- 自動 .env 読み込み:
  - プロジェクトルートを .git または pyproject.toml で検出し、.env → .env.local の順に読み込みます。OS 環境変数が優先され、.env.local は .env を上書きします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- OpenAI / J-Quants API 利用:
  - API 呼び出しにはレート制限・リトライ・バックオフが組み込まれていますが、運用環境のキー／コスト管理（API 利用料）に注意してください。
- エラー処理:
  - 多くの処理は「失敗時に部分スキップして継続」する設計です（フェイルセーフ）。致命的なエラーや品質チェックの警告/エラーをモニタリングして運用判断を行ってください。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要モジュールを抜粋した構成例：

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / settings
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP スコアリング
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント + 保存関数
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL インターフェース公開
    - calendar_management.py         — 市場カレンダー管理
    - news_collector.py              — RSS ニュース収集
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum / value / volatility）
    - feature_exploration.py         — 将来リターン / IC / summary 等

（上記はコードベースの抜粋です。実際のリポジトリにはさらにファイルが存在する場合があります。）

---

## よくある運用コマンド（例）

- ETL を定期実行する cron / Airflow タスクでは、仮想環境を有効にした上で Python スクリプトから run_daily_etl を呼び出すのが簡単です。
- ニュース収集は夜間バッチで RSS 全取得 → raw_news に保存 → score_news を実行するワークフローが推奨です。
- 監査 DB は発注ロジックと同一 DB にするか専用 DB にするか運用方針に応じて選択してください（init_audit_db で別 DB を簡単に作成できます）。

---

もし README に追加して欲しい内容（例: 実運用での注意点、CI 設定、詳しい API レスポンス例、テスト方法、pyproject.toml に基づくインストール手順）があれば教えてください。必要に応じてサンプル .env.example や典型的な ETL スケジュール例、Dockerfile / systemd ユニット例も作成します。