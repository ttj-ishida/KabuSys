# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
データ取得（J-Quants）、ETL、品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、監査ログなどを含むモジュール群を提供します。

主な用途:
- 日次ETL（株価・財務・市場カレンダー）の自動取得・保存
- ニュース記事の収集・NLPによる銘柄センチメント算出
- マーケットレジーム判定（ETF MA と マクロニュースの合成）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- ファクター計算・研究ユーティリティ

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）と DuckDB への冪等保存
  - pipeline: 日次 ETL 実行エントリポイント（run_daily_etl）と個別ETL
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF/サイズ制限/トラッキング除去対策）
  - calendar_management: 営業日判定、next/prev_trading_day、calendar_update_job
  - audit: 監査ログテーブル初期化・監査DB作成ユーティリティ
  - stats: z-score 正規化など汎用統計ユーティリティ

- ai
  - news_nlp.score_news: ニュース記事をまとめて OpenAI に送り、銘柄ごとの ai_score を ai_scores テーブルへ書込む
  - regime_detector.score_regime: ETF (1321) の MA とマクロ記事の LLM センチメントを合成して market_regime に書込む

- research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー、rank 等

- config
  - 環境変数管理（.env 自動読み込みロジック、必須項目チェック、環境種別・ログレベル検証）

---

## 動作要件 / 依存ライブラリ

- Python 3.10 以上（型注釈の | 演算子を使用）
- 必須 Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
```

（リポジトリに pyproject.toml / requirements があれば `pip install -e .` や `pip install -r requirements.txt` を使用してください）

---

## 環境変数（主なもの）

.env または環境変数で設定します（config モジュールはプロジェクトルートの .env / .env.local を自動読み込みします）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数と説明:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector のデフォルト）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 仮想環境作成 & 有効化
3. 必要パッケージをインストール（上記参照）
4. 環境変数を .env に設定（プロジェクトルートに配置）
5. DuckDB ファイルや必要ディレクトリを作成（settings.duckdb_path の親ディレクトリなど）

例:
```bash
git clone <repo-url>
cd <repo-dir>
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# .env を作成
mkdir -p data
```

---

## 使い方（主要な例）

以下はライブラリをインポートして使う最小例です。各関数は duckdb の接続オブジェクトを受け取ります。

- DuckDB 接続（ファイル or ":memory:"）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定しなければ今日が対象
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（aiスコアを ai_scores テーブルへ書込む）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n}")
```
- 市場レジーム判定（market_regime テーブルへ書込む）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DB（監査テーブル群）初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_schema は内部で実行され、テーブルが作成されます
```

- カレンダー更新ジョブ（J-Quants から取得して market_calendar を更新）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"保存件数: {saved}")
```

注意:
- OpenAI を利用する機能は `OPENAI_API_KEY`（または各関数に `api_key` 引数）を必要とします。
- J-Quants API 呼び出しは `JQUANTS_REFRESH_TOKEN` を必要とします。

---

## 実装上の注意点（設計方針の要約）

- Look-ahead バイアス回避: 各モジュールは内部で datetime.today() 等に依存しない設計（backtest での使用を想定）
- ETL は差分更新とバックフィルロジックを持つ（後出し修正を吸収）
- API 呼び出しにはリトライ・レートリミット制御・フェイルセーフ（エラー時は処理継続）を実装
- ニュース RSS は SSRF / Gzip Bomb / トラッキング除去 / サイズ制限などセキュリティ対策を実装
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で行われる
- 品質チェックモジュールはエラー/警告を返し、呼び出し元で対応を決定できる設計

---

## ディレクトリ構成

（リポジトリ内の主要ファイル・モジュール一覧）
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ etl.py
│  ├─ calendar_management.py
│  ├─ news_collector.py
│  ├─ quality.py
│  ├─ stats.py
│  ├─ audit.py
│  └─ ...
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
└─ research/...（ファクター/解析ユーティリティ）
```

主要なエントリポイント:
- ETL: kabusys.data.pipeline.run_daily_etl
- ニュースNLP: kabusys.ai.news_nlp.score_news
- レジーム判定: kabusys.ai.regime_detector.score_regime
- 監査DB 初期化: kabusys.data.audit.init_audit_db

---

## 開発・貢献

- 自動環境読み込み（.env / .env.local）は config モジュールにより行われます。テストなどで自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- テストや CI を整備する場合は、OpenAI/J-Quants 呼び出し部分をモック可能な設計になっています（内部の `_call_openai_api` などは patch で差し替え可能です）。

---

## ライセンス / その他

本 README はコードベースの概要・使い方をまとめたものです。実際に運用する際は API キー・シークレットの管理、実売買環境（live）での十分なリスク管理・検証を行ってください。

ご不明点や README に追記したい項目があれば教えてください。