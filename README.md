# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants からの市場データ取り込み）、ニュース収集・NLP（OpenAI を使ったセンチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注〜約定トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株アルゴリズム・トレーディングおよびデータ基盤（Data Platform / Research）向けのモジュール群を提供します。主な目的は次の通りです。

- J-Quants API からの株価・財務・カレンダーの差分 ETL と DuckDB への冪等保存
- RSS ニュース収集と記事の前処理・保存
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別スコア）とマクロセンチメントによる市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → executions）と DuckDB 初期化ユーティリティ
- 環境変数ベースの設定管理と .env 自動読み込み（プロジェクトルート基準）

設計上の共通ポリシーとして、バックテストでのルックアヘッドバイアスを避けるため「現在時刻を直接参照しない」「DBクエリで date < target_date の排他条件を使う」等が徹底されています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、トークン自動リフレッシュ、レートリミット・リトライ）
  - news_collector（RSS 取得・前処理・SSRF対策）
  - quality（データ品質チェック）
  - calendar_management（営業日判定・カレンダー更新ジョブ）
  - audit（監査ログテーブル定義と初期化）
- ai/
  - news_nlp.score_news（銘柄別ニュースセンチメントを ai_scores に保存）
  - regime_detector.score_regime（ETF 1321 の MA とマクロニュースの LLM 評価を合成して market_regime に書込）
- research/
  - factor_research（calc_momentum, calc_value, calc_volatility）
  - feature_exploration（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込み・検証（.env 自動ロード、必須変数チェック、環境モード判定: development/paper_trading/live）

---

## 必要な環境変数

このプロジェクトで使用される主要な環境変数（例）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン（get_id_token 用）
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード（実行モジュールで使用）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時に必要）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — one of: development, paper_trading, live (デフォルト development)
- LOG_LEVEL — one of: DEBUG, INFO, WARNING, ERROR, CRITICAL (デフォルト INFO)

.env 例ファイル（プロジェクトルートに .env / .env.local）を用意してください。  
自動読み込みはプロジェクトルート（.git または pyproject.toml の存在する親ディレクトリ）から行われます。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. Python 3.10+ をインストールしてください（typing の union 表記等を使用）。

2. 仮想環境を作成して有効化：

   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（代表例）:

   pip の requirements.txt はプロジェクトに含まれていない想定のため、主要依存を手動でインストールします。

   ```
   pip install duckdb openai defusedxml
   ```

   実行環境に応じて追加パッケージ（例: sqlite3 は標準、requests を好む場合は別途）を導入してください。

4. プロジェクトをインストール（開発モード）:

   ```
   pip install -e .
   ```

   （pyproject.toml / setup.cfg が用意されている想定です）

5. プロジェクトルートに `.env` または `.env.local` を作成し、上記の必須環境変数を設定してください。

---

## 使い方（主要な呼び出し例）

注: すべてのサンプルは Python スクリプト内または REPL で実行します。DuckDB 接続はファイル（デフォルト data/kabusys.duckdb）または ":memory:" を指定できます。

- DuckDB 接続を作る:

  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する（J-Quants からデータ取り込み）:

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores に保存:

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("wrote", written, "codes")
  ```

  api_key を引数で渡さない場合は環境変数 `OPENAI_API_KEY` を参照します。

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）:

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB の初期化:

  ```python
  from kabusys.data.audit import init_audit_db

  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit を使って監査テーブルにアクセス可能
  ```

- 市場カレンダーの夜間更新ジョブを実行:

  ```python
  from datetime import date
  from kabusys.data.calendar_management import calendar_update_job
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print("saved", saved)
  ```

- 研究用ファクトル計算の例:

  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  # momentum: list of dicts with keys: date, code, mom_1m, mom_3m, mom_6m, ma200_dev
  ```

---

## 設定の自動読み込みについて

- パッケージ起点の config モジュールはプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を探索して .env と .env.local を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 書式は shell 形式のキー=値（`export KEY=val` も可）。コメントやクォートを適切に扱います。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ロギング・モード

- KABUSYS_ENV により実行モードを切り替えます: `development` / `paper_trading` / `live`
- ログレベルは環境変数 `LOG_LEVEL`（デフォルト INFO）で制御します。

---

## 主要ディレクトリ構成

プロジェクトの主なファイル・ディレクトリ構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py              — 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py       — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py        — J-Quants API クライアント（fetch/save）
    - news_collector.py        — RSS 収集・前処理（SSRF 防止等）
    - calendar_management.py   — マーケットカレンダー管理（営業日判定・更新ジョブ）
    - quality.py               — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                 — 統計ユーティリティ（zscore_normalize）
    - audit.py                 — 監査ログテーブル定義・初期化
    - pipeline.py (ETLResult を含む)
    - etl.py                   — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum, value, volatility）
    - feature_exploration.py   — 将来リターン計算・IC・統計サマリー
  - research/*                  — 研究用ユーティリティ群
  - その他モジュール（strategy, execution, monitoring 等は __all__ に含む想定）

（上記は主要ファイルを抜粋したもので、実際のソースに応じて増減します）

---

## 開発時の注意点 / ベストプラクティス

- OpenAI や J-Quants の API 呼び出しは課金やレート制限がかかるため、ローカル開発ではモックや少量のデータで動作確認してください。score_news / regime_detector の _call_openai_api はテスト時に差し替え可能です（unittest.mock.patch を想定）。
- DuckDB の executemany に空リストを渡すと不具合が起きるバージョンがあるため、コード中で空リストを避けるガードがあります（pipeline、news_nlp 等）。
- 監査スキーマは冪等で作成しますが、DuckDB のトランザクション動作に注意してください（init_audit_schema の transactional オプションを参照）。
- ニュース収集は SSRF や XML 攻撃（XML Bomb）対策を実装していますが、外部入力をそのまま処理するパイプラインではさらに検証や監査を行ってください。

---

## ライセンス / 貢献

この README はソースコードベースから自動的に要点を抜粋して作成しています。実際のライセンス情報や貢献ガイドラインはリポジトリのトップレベル（LICENSE, CONTRIBUTING.md など）を参照してください。

---

README に含めてほしい追加の実行例（例えば CLI、systemd タスク、GitHub Actions のワークフロー例）や、requirements.txt / pyproject.toml の雛形が必要であれば教えてください。