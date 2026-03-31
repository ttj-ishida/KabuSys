# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。ETL、ニュースNLP（LLM）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（オーディット）等のユーティリティを含みます。

## 概要
KabuSys は次を主眼に設計されています。
- J-Quants API からのデータ取得（株価・財務・市場カレンダー）
- DuckDB を用いたローカルデータプラットフォーム（ETL / 品質チェック）
- ニュース記事の収集と LLM による銘柄センチメント解析（gpt-4o-mini を想定）
- ETF とマクロセンチメントの合成による市場レジーム判定
- 研究（リサーチ）向けファクター計算・特徴量評価
- 発注〜約定までのトレーサビリティを担保する監査テーブル定義

設計上の特徴：
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を不用意に参照しない）
- API 呼び出しに対するリトライ・バックオフやフェイルセーフ（失敗時は継続）
- DuckDB に対する冪等保存（ON CONFLICT DO UPDATE など）
- テスト容易性のため API キー注入や内部関数の差し替えが可能

---

## 主な機能一覧
- 環境設定管理: 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（有効無効切替可能）
- データ ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）
- データ品質チェック（kabusys.data.quality）
- ニュース収集（RSS）と前処理（kabusys.data.news_collector）
- ニュース NLP（LLM）で銘柄センチメントを ai_scores に書き込む（kabusys.ai.news_nlp）
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメント合成）（kabusys.ai.regime_detector）
- リサーチ向けファクター計算（momentum / value / volatility）（kabusys.research）
- 統計ユーティリティ（zscore_normalize 等）（kabusys.data.stats）
- 監査ログスキーマの初期化・専用 DB 作成（kabusys.data.audit）

---

## セットアップ手順

1. Python 環境（3.11 以上推奨）を用意します。

2. 依存ライブラリをインストールします（例）:
   ```
   pip install duckdb openai defusedxml
   ```
   補足: プロジェクトで管理している requirements.txt / pyproject.toml があればそちらを利用してください。

3. 環境変数の設定
   - プロジェクトルートに `.env` として必要な環境変数を置くことができます。自動読み込み順は:
     OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 最低限必要な環境変数（モジュールで _require() を呼ぶもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（発注系）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（監視等）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネルID
     - OPENAI_API_KEY — OpenAI 呼び出し時（news_nlp / regime_detector）
   - 任意/設定可能項目:
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

4. （任意）DuckDB の初期スキーマ作成や監査 DB 初期化を行う：
   - 監査 DB の初期化例:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # または in-memory:
     conn = init_audit_db(":memory:")
     ```

---

## 使い方（代表的な例）

- settings を使う（環境変数参照）
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)       # Path オブジェクト
  print(settings.is_live)           # ランタイム環境フラグ
  ```

- 日次 ETL を実行する（DuckDB 接続と target_date を渡す）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄ごとスコア付け）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数で設定するか、api_key に渡す
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"scored: {n_written} codes")
  ```

- 市場レジーム判定（ETF 1321 MA + マクロセンチメント）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- 監査スキーマ初期化（既存接続に追加）
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- J-Quants から原データを直接フェッチする（テストや開発で）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # 環境変数から JQUANTS_REFRESH_TOKEN を用いて取得
  rows = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
  ```

注意点:
- OpenAI 呼び出しを伴う機能（news_nlp/regime_detector）は API キーを必須とします。api_key を直接渡すか環境変数 OPENAI_API_KEY を設定してください。
- DuckDB の操作はトランザクションや executemany の挙動に注意（コメントが各関数内にあります）。

---

## ディレクトリ構成（主要ファイル）
（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（LLM）で ai_scores に書き込み
    - regime_detector.py           — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - calendar_management.py       — 市場カレンダー管理・判定ユーティリティ
    - etl.py                       — ETL API の公開（ETLResult 再エクスポート）
    - pipeline.py                  — ETL パイプライン実装（run_daily_etl 等）
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - quality.py                   — データ品質チェック（欠損・スパイク等）
    - audit.py                     — 監査ログ（DDL/初期化）
    - jquants_client.py            — J-Quants API クライアント & 保存処理
    - news_collector.py            — RSS 取得・前処理・保存
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー 等
  - other modules...
  
各ファイル内に詳細な docstring と設計方針・注意点（ルックアヘッドバイアス回避、リトライ方針など）が記載されています。実装を読むことで各関数の前提・副作用が分かるように設計しています。

---

## 注意事項 / ベストプラクティス
- 本ライブラリは実運用での売買ロジックと監査トレースの両方を含みます。実際に発注を行う前に sandbox / paper_trading 環境で十分検証してください。
- 環境変数や API キーは秘匿して管理してください（.env は gitignore 推奨）。
- LLM 呼び出しは料金が発生します。開発時は小さなデータやモックで動作検証することを推奨します（news_nlp/_call_openai_api はテスト時に差し替え可能です）。
- DuckDB ファイルのバックアップ・ローテーションを検討してください（データ量が増えるため）。

---

不明点や README に追加したい利用シナリオ（CI 用の初期化スクリプト、Docker 化手順、サンプル ETL cron 設定など）があれば教えてください。必要に応じてサンプルスクリプトや .env.example も作成します。