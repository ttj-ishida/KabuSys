# KabuSys

日本株向けのデータパイプライン / 研究 / AI支援市場判定 / 監査ログを備えた自動売買基盤ライブラリです。  
このリポジトリは主に次の用途を想定しています：J‑Quants からのデータ取得と DuckDB への保存（ETL）、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算・特徴量探索、監査ログ（発注→約定のトレーサビリティ）など。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（.env 例）
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J‑Quants API を用いた株価・財務・マーケットカレンダーの差分取得（ETL）
- DuckDB を用いたデータ永続化と品質チェック
- RSS ベースのニュース収集と LLM（OpenAI）を用いたニュースセンチメントスコアリング
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull / neutral / bear）
- 研究用ファクター（モメンタム、バリュー、ボラティリティ等）と特徴量探索ユーティリティ
- 発注・約定までのフローを記録する監査ログ（DuckDB に監査テーブルを作成）

設計上の特徴：
- ルックアヘッドバイアス防止（内部で date.today() 等に依存しない設計）
- DuckDB によるローカル分析向けスキーマと冪等保存（ON CONFLICT を使用）
- LLM 呼び出しに対する堅牢なリトライ・パース保護
- RSS の SSRF 対策やサイズ上限などセキュリティ考慮

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 各種設定の型安全なラッパ（J‑Quants トークン、OpenAI キー、DB パス等）

- kabusys.data
  - jquants_client：J‑Quants API クライアント（取得・保存関数、リトライ/レート制御）
  - pipeline：日次 ETL（run_daily_etl）と個別 ETL ジョブ（prices/financials/calendar）
  - news_collector：RSS 収集・前処理と raw_news への保存ユーティリティ
  - calendar_management：JPX カレンダーの扱い（営業日判定、next/prev_trading_day 等）
  - quality：データ品質チェック（欠損、重複、スパイク、日付不整合）
  - audit：監査ログ（signal_events / order_requests / executions テーブルの初期化ユーティリティ）
  - stats：Zスコア正規化など汎用統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news：ニュースを LLM でスコアリングし ai_scores に書き込み
  - regime_detector.score_regime：ETF（1321）200日MA乖離とマクロニュースを統合して市場レジームを判定

- kabusys.research
  - factor_research：モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration：将来リターン計算、IC（Spearman）計算、統計サマリー、ランク関数

---

## セットアップ手順

前提：Python（開発時には 3.9+ を想定）と pip がインストールされていること。

1. リポジトリをクローン / 作業ディレクトリへ移動

2. 仮想環境を作成・有効化（推奨）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 必要パッケージをインストール
   - 最低依存（このリポジトリに基づく）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install --upgrade pip
     - pip install duckdb openai defusedxml

   （パッケージ管理に setup.cfg/pyproject.toml があれば pip install -e . を推奨）

4. 環境変数設定
   - プロジェクトルートに .env を配置すると自動で読み込まれます（但し KABUSYS_DISABLE_AUTO_ENV_LOAD をセットすると無効化）。
   - 必須の環境変数は README 下部のサンプルを参照してください。

5. DuckDB 用ディレクトリを作成（必要に応じて）
   - デフォルトでは data/kabusys.duckdb, data/monitoring.db 等を使用します。dir が存在しない場合は自動生成する機能を呼ぶ前にディレクトリを作成してください（init_audit_db が親ディレクトリを作りますが、用途により任意）。

---

## 使い方（コード例）

※ 以下は Python スクリプトや REPL からの呼び出し例です。

- 基本的な DuckDB 接続
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（カレンダー／株価／財務を差分取得し品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API 必須）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査用 DuckDB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- RSS を直接取得してパース（news_collector のユーティリティ）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

---

## 環境変数（.env 例）

このプロジェクトが期待する主な環境変数（必須／任意）と説明です。

必須:
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（ETL 用）
- SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン（このコードでは設定参照のみ）
- SLACK_CHANNEL_ID: Slack 通知先チャネルID（このコードでは設定参照のみ）
- OPENAI_API_KEY: OpenAI 呼び出しに使う API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能等で使用）

任意（デフォルト有り）:
- KABUSYS_ENV: development|paper_trading|live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化
- KABU_API_BASE_URL: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: duckdb のパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視等で利用する sqlite のパス（デフォルト data/monitoring.db）

サンプル .env（プロジェクトルートに置く）
```env
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# kabuステーション
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789

# DB パス等（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- .env の読み込みは kabusys.config が自動でプロジェクトルート（.git または pyproject.toml を探索）を探して行います。自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/__init__.py
  - パッケージのエントリポイント、__version__ 定義

- src/kabusys/config.py
  - 環境変数 / .env のロードと設定ラッパ（settings オブジェクト）

- src/kabusys/data/
  - jquants_client.py
    - J‑Quants API 呼び出し、取得関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）と DuckDB 保存関数（save_*）
  - pipeline.py
    - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl と ETLResult 型
  - news_collector.py
    - RSS 収集と前処理（SSRF 対策、サイズ制限、正規化）
  - calendar_management.py
    - market_calendar の操作と営業日判定（is_trading_day / next_trading_day / get_trading_days 等）
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py
    - 監査テーブル DDL と init_audit_db（signal_events / order_requests / executions）
  - stats.py
    - zscore_normalize 等、汎用統計ユーティリティ
  - etl.py
    - ETLResult を再エクスポート（インターフェース用）

- src/kabusys/ai/
  - news_nlp.py
    - ニュース記事を OpenAI に送って銘柄ごとにセンチメント（ai_scores）を生成する score_news
  - regime_detector.py
    - ETF 1321 の MA200 乖離とマクロニュース（LLM）を重み付けして市場レジームを判定する score_regime

- src/kabusys/research/
  - factor_research.py
    - calc_momentum / calc_value / calc_volatility（ファクター計算）
  - feature_exploration.py
    - calc_forward_returns / calc_ic / rank / factor_summary（研究ユーティリティ）

- そのほか：logging を利用した豊富なログ出力と、DB への冪等保存・トランザクション管理が各モジュールで実装されています。

---

## 注意点 / 運用上のヒント

- OpenAI の呼び出しは外部 API に依存するため、API キーの管理と料金に注意してください。テスト時は API 呼び出し部分をモックする設計になっています。
- J‑Quants の API レートリミット（120 req/min）を遵守するため、jquants_client は内部でレートリミットとリトライを実装しています。
- DuckDB の executemany に関するバージョン差異（空リスト不可など）に配慮した実装がなされています。
- ETL / 品質チェックは Fail-Fast ではなく問題を集めて返す実装です。運用側で result.has_quality_errors 等を見てアラートや停止判定を行ってください。
- 監査テーブルは削除を前提としない設計（トレーサビリティ重視）です。init_audit_db で初期化できます。

---

もし README に加えて、サンプルスクリプトや CI 用のワークフロー、あるいはパッケージ配布（pyproject.toml / setup.cfg）向けの追加内容が必要であれば教えてください。README に追記して整備します。