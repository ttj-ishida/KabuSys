# KabuSys

日本株向け自動売買・データプラットフォーム（ライブラリ）  
本リポジトリはデータ収集（J-Quants / RSS）、データ品質チェック、特徴量計算、ニュースNLP（LLM）によるセンチメント評価、ならびに市場レジーム判定・監査ログ管理を行うモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアス（backtestで未来情報を参照する問題）を避ける実装
- DuckDB をローカル DB として利用した差分 ETL、冪等な保存
- 外部 API 呼び出しはレート制御・リトライ・フェイルセーフを備える
- OpenAI（gpt-4o-mini）を用いた JSON Mode によるニュース解析
- 監査ログ（signal → order → execution のトレーサビリティ）を DuckDB に保持

---

## 主な機能一覧

- 環境設定管理
  - `.env` / `.env.local` を自動読み込み（無効化可）
  - settings オブジェクト経由で構成値取得

- データ取得・ETL（kabusys.data）
  - J-Quants API クライアント（レートリミット・トークン自動リフレッシュ・リトライ）
  - 差分 ETL（株価日足 / 財務 / 市場カレンダー）
  - 市場カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS）および前処理（SSRF 対策、サイズ制限、トラッキング除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（signal_events, order_requests, executions）
  - 汎用統計ユーティリティ（Zスコア正規化 等）

- ニュース NLP / LLM（kabusys.ai）
  - ニュース記事を銘柄ごとに集約して LLM へ送りセンチメントを算出（ai_scores に保存）
  - マクロニュースと ETF（1321）の MA ギャップを合成して市場レジームを判定（bull / neutral / bear）

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（モメンタム・バリュー・ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリーなど

- その他設計特徴
  - 多くの関数が「api_key を引数で注入可能」 → テストしやすい
  - DuckDB への保存処理は冪等（ON CONFLICT）で安全

---

## 必要条件（推奨）

- Python 3.10+
  - 型注記で `Path | None` 等の構文を使用しているため 3.10 以上を推奨します
- 必要なパッケージ（代表）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリの urllib 等を使用）

依存はプロジェクト側の packaging / requirements に記載している想定です。必要に応じて pip でインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン・移動
   ```bash
   git clone <このリポジトリURL>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - 簡易例:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 開発用や extras があれば `requirements.txt` / `pyproject.toml` を参照してください。
   - パッケージを編集可能インストールする場合:
     ```bash
     pip install -e .
     ```

4. 環境変数の準備
   - プロジェクトルートに `.env` と `.env.local` を置けます（自動ロードされます）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   推奨の `.env`（例）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # OpenAI
   OPENAI_API_KEY=your_openai_api_key

   # kabuステーション（必要なら）
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack（通知用）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 動作モード: development | paper_trading | live
   KABUSYS_ENV=development

   # ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的なユースケース）

以下は Python REPL やスクリプトからの呼び出し例です。DuckDB 接続には `duckdb.connect()` を使用します。

- ETL（日次）を実行してデータを更新する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを計算して ai_scores に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written: {written}")
  ```

- 市場レジームをスコアリング（1321 MA + マクロセンチメント）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 研究用ファクターを計算する
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(momentum), momentum[:3])
  ```

- 監査ログ DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
  ```

注意点：
- OpenAI API 呼び出しは `OPENAI_API_KEY` か各関数の `api_key` 引数で指定可能です（テスト容易性のため）。
- J-Quants 認証は `JQUANTS_REFRESH_TOKEN` 環境変数から自動で解決されます（`kabusys.data.jquants_client.get_id_token()` を通じて使用）。
- 多くの処理はフェイルセーフ（APIエラー時にスキップしてログ）を意図しています。ログを参照して問題を確認してください。

---

## 便利な環境変数一覧

必須（実行する機能に依存）：
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- OPENAI_API_KEY — OpenAI 呼び出し（news_nlp / regime_detector）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を使う場合

任意／デフォルトあり：
- KABU_API_PASSWORD — kabuステーション連携
- KABU_API_BASE_URL — デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効にする（1 または存在で無効化）

---

## テスト・開発のヒント

- 自動 .env ロードはパッケージ読み込み時に行われます。単体テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定するか、`settings` をモックしてください。
- OpenAI 呼び出しは内部で `_call_openai_api` を使っており、テスト時にパッチ差し替えが可能です（unittest.mock.patch）。
- J-Quants クライアントも `_request` の挙動をモックすることで API 呼び出しをシミュレートできます。
- DuckDB はインメモリ `":memory:"` を指定できるため、テスト用 DB の初期化が簡単です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
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
  - etl.py (ETL インターフェース再エクスポート)
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py
  - etl.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/__init__.py
- research/*（ファクター / 特徴量探索）
- その他（strategy / execution / monitoring 等のエクスポートは将来的に追加）

（上記はコードベースの主要モジュールを抜粋しています）

---

## 実装上の重要な設計メモ（抜粋）

- Look-ahead バイアス対策：多くの関数は内部で `date.today()` を参照しない・SQL において `date < target_date` のような排他条件を使用する等の対策を行っています。
- 冪等性：DB保存は基本的に ON CONFLICT DO UPDATE / INSERT ... DO UPDATE で上書きし、重複や再実行に耐える設計。
- レート制御・リトライ：J-Quantsクライアントに RateLimiter、指数バックオフ、401時のトークン自動更新等を実装。
- LLM 呼び出しは JSON Mode を使用し、堅牢なパースとフェイルセーフ（失敗時はスコア 0.0 など）を行う。

---

## ライセンス・貢献

- ライセンス情報や貢献ガイドラインはリポジトリに合わせて追加してください（本 README には含まれていません）。

---

不明点や README に追記してほしい項目（CI 手順、詳細な env.example、具体的なスキーマ定義など）があれば教えてください。