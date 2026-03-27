# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースのNLP解析、マーケットレジーム判定、監査ログ（発注→約定トレース）、リサーチ用ファクタ計算などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株の自動売買システムやデータプラットフォームを構築するためのモジュール群です。以下の領域をカバーします。

- J-Quants API を利用した株価・財務・市場カレンダーの差分取得と DuckDB への冪等保存
- 日次 ETL パイプライン（差分取得、保存、品質チェック）
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント分析（銘柄ごとの ai_score）とマクロセンチメントを使った市場レジーム判定
- リサーチ用のファクター計算（モメンタム/バリュー/ボラティリティ）と統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ生成ユーティリティ
- 環境設定管理（.env の自動読み込み・保護）

設計上の特徴として、バックテストに対するルックアヘッドバイアス回避、API 呼び出しのフェイルセーフ・リトライ、DuckDB を中心とした SQL ベース処理、外部依存を最小限にすることを重視しています。

---

## 機能一覧

主な機能（抜粋）:

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
  - pipeline: 日次 ETL（run_daily_etl、個別 ETL ジョブ）
  - calendar_management: 市場カレンダー管理・営業日判定
  - news_collector: RSS 取得・前処理（SSRF/サイズ/トラッキング除去対策）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（監査スキーマ生成、init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースの LLM センチメントを合成して market_regime に書き込む
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config:
  - Settings: 環境変数読み取り（.env 自動ロード／KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）

---

## 動作環境 / 依存

- Python 3.10+
- 必要な主なパッケージ（例）:
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトでは pyproject.toml / requirements.txt を参照してインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン／取得

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml があれば `pip install -e .` を推奨）

4. 環境変数を設定
   - ルートに `.env` または `.env.local` を置くと、モジュール起動時に自動で読み込まれます（既存 OS 環境変数は保護されます）。
   - 自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env の最小例 (.env.example)
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=your_openai_api_key
- KABU_API_PASSWORD=your_kabu_station_password
- SLACK_BOT_TOKEN=your_slack_bot_token
- SLACK_CHANNEL_ID=your_slack_channel_id
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

注意: Settings が必須とする変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定だと起動時に ValueError を投げます。

---

## 使い方（簡単な例）

Python REPL / スクリプト内での利用例をいくつか示します。

- DuckDB 接続を使った日次 ETL 実行（J-Quants から取得して保存・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を指定しなければ今日が使われる
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア（銘柄別）生成:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
# api_key を明示的に渡すことも可能: score_news(conn, date(...), api_key="sk-...")
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# init_audit_schema は init_audit_db 内で transactional=True で実行されます
```

- カレンダーの夜間更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## よくあるトラブルと注意点

- 環境変数未設定で ValueError:
  - Settings の必須項目が未設定だと例外になります。README の .env 例を参考に設定してください。

- OpenAI / J-Quants の API レート・鍵制限:
  - jquants_client と AI モジュールにはリトライとレート制御がありますが、API 使用に伴う課金・制限に注意してください。

- DuckDB の executemany に空リストを渡すとエラーとなるバージョン差:
  - コード中で回避処理を入れていますが、DuckDB のバージョンに依存する挙動に注意してください。

- ルックアヘッドバイアス対策:
  - モジュールはバックテスト用途を想定して設計され、多くの関数は date を引数に取って内部で日付を決め打ちせずに処理します。実運用・研究のどちらでも日付管理に注意してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env 自動読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py       — ニュースを LLM で解析し ai_scores に保存
    - regime_detector.py — ETF MA とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save）
    - pipeline.py       — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理、営業日判定、calendar_update_job
    - news_collector.py — RSS 収集・前処理
    - quality.py        — 品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py          — zscore_normalize 等の統計ユーティリティ
    - audit.py          — 監査ログ（スキーマ定義 / init）
    - etl.py            — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールの docstring に設計・仕様が詳述されているので、詳細は該当ファイルを参照してください。

---

## 貢献 / 開発

- コードは src レイアウトで管理されています。ローカルで開発する際は仮想環境を用い、依存パッケージをインストールしてください。
- テストや CI の設定はプロジェクトのルート（pyproject.toml 等）に従ってください。
- 環境情報や秘匿情報（API キー等）は .env / CI secret を利用し、リポジトリに含めないでください。

---

必要があれば README に「API の具体的なレスポンス例」「データベーススキーマ定義（raw_prices 等）」「運用向けの Cron / Airflow ジョブ例」などの追記や、Docker / systemd のデプロイ例も追加できます。どの情報が必要か教えてください。