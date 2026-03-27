# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）等の機能を提供します。

---

## プロジェクト概要

KabuSys は以下のような目的で設計されたモジュール群です。

- J-Quants API を利用した株価・財務・市場カレンダーの差分 ETL と品質チェック
- RSS ベースのニュース収集と前処理（SSRF・大容量対策を含む堅牢な実装）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント分析と市場レジーム判定（Safe fallback / retry 実装あり）
- リサーチ用途のファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 発注・約定に関する監査ログ（DuckDB による冪等テーブル定義、UUID ベースのトレーサビリティ）
- テストしやすく、ルックアヘッドバイアスを避ける設計方針（date.today() に依存しない等）

バッチ処理・研究・実行系を分離しており、DuckDB を中心にデータ永続化を行います。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（トークンリフレッシュ、レート制御、リトライ、保存関数）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS 取得、URL 正規化、SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（init_audit_db / init_audit_schema）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news：銘柄ごとに LLM でセンチメント算出）
  - 市場レジーム判定（score_regime：ETF 1321 の MA200 と LLM センチメントを合成）
  - いずれも OpenAI 呼び出しはリトライやフェイルセーフを備える
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索 / 統計（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - .env 自動読み込み（プロジェクトルート検出、.env/.env.local の優先度）
  - アプリ設定オブジェクト settings（必要な環境変数を明示）

---

## セットアップ手順

前提：
- Python 3.9+（型ヒントに union といった構文が使われているため Python 3.10 推奨）
- DuckDB、OpenAI SDK、defusedxml 等を使用します

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（requirements.txt がある想定）
   例（最低限）:
   ```bash
   pip install duckdb openai defusedxml
   ```
   実運用では logger やテスト用のパッケージ等も追加してください。

4. 環境変数を設定
   プロジェクトルートに .env または .env.local を置くと自動的に読み込まれます（config.py）。
   必須環境変数（少なくともこれらを設定してください）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（発注機能を使う場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack 通知対象チャネル
   - OPENAI_API_KEY: OpenAI を使う場合（score_news / score_regime）

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   自動ロードを無効にする場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

5. データベースディレクトリ作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な呼び出し例）

以下は Python REPL / スクリプトから直接使う簡単な例です。DuckDB 接続は duckdb.connect() を使用します。

- 日次 ETL 実行（J-Quants からのデータ取得・保存・品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄ごとの ai_scores へ書き込み）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書込件数: {written}")
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化
  ```python
  from pathlib import Path
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db(Path("data/audit.duckdb"))
  # conn を使って audit テーブルへアクセスできます
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意点:
- OpenAI 呼び出しは外部 API を使うため料金・レート制限・鍵管理に注意してください。テスト時は内部の _call_openai_api をモックして外部呼び出しを抑制できます（例: unittest.mock.patch）。
- J-Quants API はレート制限（120 req/min）に従う実装になっています。get_id_token / fetch_* 系は自動リトライ・トークン更新を行います。

---

## 環境設定（重要な変数）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API Key（score_news, score_regime で使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注実装を使う場合）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: 監視用 sqlite パス（デフォルト "data/monitoring.db"）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化するには 1 をセット

config.py により .env/.env.local の自動読み込みを行います。プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

---

## ディレクトリ構成

主要ファイル・モジュールを抜粋して示します（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの LLM スコアリング（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存・認証・リトライ）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL の公開インターフェース（ETLResult 等）
    - news_collector.py      — RSS ニュース収集・前処理
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログ / スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — momentum/value/volatility 計算
    - feature_exploration.py — forward returns / IC / rank / summary
  - ai/ (上記)
  - research/ (上記)
  - その他：strategy/, execution/, monitoring/ （パッケージ列挙のみ、実装は別途ある想定）

各モジュールはドキュメント文字列内に設計方針・フェイルセーフ挙動が記載されています。

---

## 開発者向けメモ

- テスト容易性のため、外部 API 呼び出し（OpenAI, J-Quants, HTTPなど）は各モジュールで差し替え・モック可能な設計になっています。例えば news_nlp._call_openai_api や regime_detector._call_openai_api を patch してテストできます。
- DuckDB を利用することで単一ファイルでローカル検証が容易です。大量データを扱う際はファイルパスや並列化方針を検討してください。
- ルックアヘッドバイアス対策がコード全体の設計原則になっています（関数は target_date を受け取り内部で現在時刻を直接参照しない等）。
- audit.init_audit_schema は transactional 引数で BEGIN/COMMIT を制御します。DuckDB のトランザクション特性に注意して利用してください。

---

必要であれば README に「CLI 例」「cron / Airflow での運用例」「.env.example」を追記できます。どの操作（ETL, AI スコア, レジーム判定等）の使用方法を詳しく追加したいか教えてください。