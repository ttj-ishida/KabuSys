# KabuSys

日本株向けのデータプラットフォーム & 自動売買基盤のライブラリ群です。  
ETL（J-Quants からのデータ取得・保存）、ニュースの収集・NLP スコアリング、リサーチ用ファクター計算、監査ログ（発注→約定トレース）、市場カレンダー管理、及び一部の戦略／実行補助モジュールを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（date.today()/datetime.today() を不用意に参照しない）
- DuckDB をデータレイクとして利用し、SQL と Python の組合せで処理
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを考慮
- 各保存処理は冪等性（idempotent）を重視

---

## 機能一覧

- data
  - ETL パイプライン（株価・財務・市場カレンダーの差分取得・保存）
  - J-Quants API クライアント（認証・ページング・保存ユーティリティ）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - マーケットカレンダー管理（営業日判定・next/prev/get_trading_days）
  - ニュース収集（RSS → raw_news、SSRF/トラッキング対策付き）
  - 監査ログ（signal / order_request / executions のテーブル定義・初期化）
  - 汎用統計ユーティリティ（Zスコア正規化 等）
- ai
  - ニュース NLP（銘柄ごとのセンチメント算出、OpenAI を利用）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコアを合成）
- research
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 特徴量解析ユーティリティ（将来リターン計算、IC、統計サマリー、ランク化）
- config
  - 環境変数 / .env ロード、設定オブジェクト（settings）

---

## セットアップ手順

前提:
- Python 3.10+（typing の一部構文と union 型を想定）
- DuckDB を使用（pip install duckdb）
- OpenAI の SDK（gpt モデル呼び出しが必要な場合）
- defusedxml（RSS パーシングの安全対策）

例: 仮想環境を作ってパッケージ依存をインストールする
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# 必要なパッケージ例（環境に合わせて調整）
pip install duckdb openai defusedxml
# 開発環境としてローカルで使う場合はパッケージを editable インストール
pip install -e .
```

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必要に応じて）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: モニタリング用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 実行プロセス監視設定
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を検出し、
  .env -> .env.local の順で環境変数をロードします（OS 環境変数を優先）。
- 自動ロードを無効化する: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨: プロジェクトルートに .env.example を作り、そこから .env/.env.local を作成してください。

---

## 使い方（概要とサンプル）

以下は主な使用例の抜粋です。実環境ではログ設定や例外処理を適切に実装してください。

1) DuckDB 接続を作成して ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

2) ニュースの NLP スコアリング（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数または api_key 引数で指定
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

3) 市場レジーム判定（ETF 1321 の MA + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログテーブル（order/signals/executions）の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# conn をアプリが使う DuckDB 接続として使用
```

5) リサーチ用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

6) データ品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意点:
- OpenAI 呼び出しにはレート制御やリトライが組み込まれていますが、API キーと料金管理には注意してください。
- ETL 等で外部 API を多用するため、ネットワークエラーや API 制限に備えた運用ルールを作ってください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py             — 環境変数 / .env 読み込みと settings
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM スコアリング（銘柄別 ai_scores へ）
    - regime_detector.py  — 市場レジーム判定（1321 MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult の公開
    - news_collector.py    — RSS 収集（SSRF/トラッキング対策）
    - calendar_management.py — マーケットカレンダー管理 / is_trading_day 等
    - quality.py           — データ品質チェック
    - stats.py             — zscore_normalize 等ユーティリティ
    - audit.py             — 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py   — Momentum / Value / Volatility 等の計算
    - feature_exploration.py — forward returns / IC / factor_summary / rank
  - ai, research, data といったサブパッケージで機能を分離

補足:
- 多くのモジュールは duckdb.DuckDBPyConnection を引数に取り、テストやアプリ側から接続を注入して使用する設計です。
- OpenAI の呼び出し部分は client を直接生成し、JSON mode を利用するためレスポンスのバリデーションやリトライが実装されています。

---

## 運用上の注意・ベストプラクティス

- 本ライブラリは「実行ロジック」と「ETL/保存ロジック」を分離しています。実際の売買実行や broker 接続は別モジュール／コネクタとして実装してください（kabuステーション関連は config を通じて設定）。
- API キーなど秘匿情報は OS 環境変数か .env.local に置き、リポジトリにはコミットしないでください。
- バックテストではデータの「取得日時（fetched_at）」と「実際にその時点で利用可能であったか」を区別して扱うこと（Look-ahead Bias 対策）。
- DuckDB のスキーマは一部 init 関数で作成できます（例: init_audit_db）。運用時はスキーマ管理手順を整備してください。

---

必要であれば、README にサンプル .env.example のテンプレートや CI / デプロイ手順、より詳細な API 使用例（関数ごとの引数例）も追記できます。どの情報を優先して詳細化したいか教えてください。