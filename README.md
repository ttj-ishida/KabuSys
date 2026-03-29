# KabuSys

日本株向けの自動売買基盤ライブラリ（データ ETL / 研究用ファクター計算 / ニュース NLP / 市場レジーム判定 / 監査ログ）。  
このリポジトリはバックテスト・リサーチ・本番オペレーションのための共通ユーティリティ群を提供します。設計上の特徴として「ルックアヘッドバイアス防止」「冪等性（idempotency）」「堅牢な API リトライ／レート制御」「セキュリティ対策（SSRF・XML攻撃対策等）」を重視しています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 動作要件（依存関係）
- セットアップ手順
- 環境変数（.env）例
- 使い方（主要 API の呼び出し例）
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python パッケージです。

- J-Quants API / RSS 等からデータを取得して DuckDB に差分 ETL を行う
- データ品質チェック（欠損・重複・スパイク・日付不整合）を実施する
- ニュース記事の NLP（OpenAI）を用いた銘柄ごとのセンチメントスコア化
- マクロ × テクニカルを組み合わせた市場レジーム判定（LLM と移動平均）
- 監査ログ（signal → order_request → execution）のスキーマ初期化およびユーティリティ
- 研究用ユーティリティ（モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン・IC 計算、Zスコア正規化）

設計方針の一部：
- バックテストやモデル評価におけるルックアヘッドバイアスを避ける（system 内で date.today() を直接参照しない・クエリに排他条件を付ける等）
- DuckDB を主ストレージとして使用し、SQL と Python を組み合わせて高速に処理
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備える

---

## 主な機能一覧

- data (kabusys.data)
  - ETL pipeline（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save 関数、認証・レート制御）
  - market calendar 管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - news_collector：RSS 収集（SSRF 対策、XML 脆弱性対策）
  - quality：データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit：監査ログスキーマの初期化（signal_events, order_requests, executions）
  - stats：Zスコア正規化等の統計ユーティリティ

- ai (kabusys.ai)
  - news_nlp.score_news：銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に書き込む
  - regime_detector.score_regime：ETF の MA とマクロニュース（LLM）を合成して market_regime を決定

- research (kabusys.research)
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

- config (kabusys.config)
  - 環境変数 / .env 読み込み、settings オブジェクトによるアクセス

---

## 動作要件（依存関係）

- Python 3.10 以上（typing の `X | Y` 構文を使用）
- 必要な外部パッケージ（代表的なもの）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging など多数

（実際の開発環境では requirements.txt / pyproject.toml で依存を管理してください）

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成と有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （実プロジェクトでは `pip install -e .` や `pip install -r requirements.txt` を使用）

4. プロジェクトルートに .env を作成（下記参照）。このパッケージは起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env を自動読み込みします。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

5. DuckDB 用ディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 環境変数 (.env) の例

以下は本システムが参照する主要環境変数の例です。プロジェクトルートに .env（および環境毎の .env.local）を配置してください。

- JQUANTS_REFRESH_TOKEN=...        # J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD=...           # kabuステーション API パスワード（必須）
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトあり）
- SLACK_BOT_TOKEN=...             # Slack 通知用（必須）
- SLACK_CHANNEL_ID=...            # Slack チャンネル ID（必須）
- DUCKDB_PATH=data/kabusys.duckdb # DuckDB ファイルパス（デフォルト）
- SQLITE_PATH=data/monitoring.db  # SQLite 等、監視用 DB パス（デフォルト）
- KABUSYS_ENV=development         # development | paper_trading | live
- LOG_LEVEL=INFO                  # DEBUG | INFO | WARNING | ERROR | CRITICAL
- OPENAI_API_KEY=...              # OpenAI API キー（ai モジュール利用時必要）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 # 自動 .env 読み込みを無効化する場合

注意:
- .env.local は .env の上書き（override=True）で読み込まれます。
- OS 環境変数が優先され、保護されます。

---

## 使い方（主要な呼び出し例）

以下は簡単な利用例です。DuckDB 接続を作成して各ユーティリティを呼び出します。

1) ETL を日次実行（データ取得・品質チェックまで）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n_written} codes")
```

3) 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> OPENAI_API_KEY を参照
```

4) 監査ログ DB 初期化（別 DB を用意して監査用テーブルを作成）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って監査ログを操作できます
```

5) 研究用ファクター計算の呼び出し例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

6) 設定値の取得
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

注意事項:
- OpenAI 呼び出しを行う関数（score_news / score_regime）は API エラー時にゼロフォールバックや部分スキップを行うように設計されていますが、実行前に OPENAI_API_KEY を設定してください。
- ETL は J-Quants の API レート制限を尊重する実装になっています（内部でスロットリング・リトライを実施）。

---

## よく使うユーティリティ関数

- market calendar
  - is_trading_day(conn, date)
  - next_trading_day(conn, date)
  - prev_trading_day(conn, date)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn)

- data quality
  - run_all_checks(conn, target_date, reference_date)

- data ETL
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl

- AI
  - score_news(conn, target_date, api_key)
  - score_regime(conn, target_date, api_key)

---

## ディレクトリ構成（主要ファイルの説明）

（root）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み、Settings クラス（settings オブジェクト）を提供
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの LLM によるセンチメント評価と ai_scores への書き込み
    - regime_detector.py — ETF MA と LLM マクロセンチメントの合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
    - pipeline.py        — ETL パイプラインの実装（run_daily_etl 等）
    - etl.py             — ETLResult の再エクスポートインタフェース
    - calendar_management.py — market_calendar 管理と営業日判定ユーティリティ
    - news_collector.py  — RSS 収集（SSRF 対策、XML セキュリティ対策）
    - quality.py         — データ品質チェック
    - stats.py           — zscore_normalize 等の統計ユーティリティ
    - audit.py           — 監査ログ用の DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — モメンタム、ボラティリティ、バリュー等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー等

---

## 運用上の注意 / 設計に関するポイント

- ルックアヘッドバイアス対策: 多くのモジュールで「target_date 未満」「target_date の前日〜前日23:30 のウィンドウ」など、データのみを使用する日付条件を厳格にしています。バックテストで使用する場合は注意して運用してください。
- 冪等性: ETL の保存関数は ON CONFLICT を用いて上書き保存するため、再実行に耐えます。
- セキュリティ: RSS 収集では URL 正規化・トラッキング除去・SSRF 対策・defusedxml を使用しています。
- OpenAI: API レスポンスは JSON モードで受け取り、パース失敗時はフェイルセーフでスコア 0.0 またはスキップする挙動です。

---

README ではこのパッケージの主要な利用方法と注意点をまとめました。さらに詳細な設計ドキュメント（StrategyModel.md / DataPlatform.md 等）やテスト、CI の設定を追加することで本番運用により適した形にできます。必要であればサンプルの pyproject.toml / requirements.txt や、より具体的な運用手順（cron / Airflow ジョブ例、Slack 通知連携例）を追加しますのでご希望をお知らせください。