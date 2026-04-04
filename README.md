# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群。  
ETL（J-Quantsからのデータ取得）、ニュースNLP（OpenAIを用いたセンチメント）、市場レジーム判定、研究用ファクター計算、データ品質チェック、監査ログスキーマなどを備えたモジュール群です。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買・データ基盤向けユーティリティを集めたパッケージです。主要機能は以下を含みます。

- J-Quants API を利用した日次株価・財務・カレンダーの差分ETL（DuckDB保存）
- RSSベースのニュース収集と前処理（SSRF対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別）とマクロセンチメントを組み合わせた市場レジーム判定
- 研究用途のファクター計算（モメンタム / ボラティリティ / バリュー）・特徴量探索（将来リターン, IC 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 発注 / 約定の監査ログスキーマ初期化ユーティリティ（DuckDB）
- 環境変数・設定管理（.env 自動読込機能付き）

設計上の方針として、ルックアヘッドバイアスを防ぐため日付処理で現在日時を直接参照しない実装や、API呼び出しのフェイルセーフ（失敗時はゼロスコア等）を意識しています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得 + 保存: raw_prices / raw_financials / market_calendar）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS → raw_news / news_symbols）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
- research/
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数読み込み・設定取得（settings オブジェクト）

---

## 要件（主な依存パッケージ）

- Python 3.10+
- duckdb
- openai
- defusedxml

必要に応じてその他標準ライブラリを使用します（urllib, json, logging 等）。

---

## インストール

パッケージを開発モードでインストールする例:

```bash
git clone <repo>
cd <repo>
pip install -e ".[dev]"   # setup.cfg/pyproject があれば extras で依存を管理している想定
# または最低限:
pip install duckdb openai defusedxml
```

※ pyproject.toml / requirements.txt がプロジェクトにある場合はそちらを参照してください。

---

## 環境設定 (.env)

パッケージ起動時に自動でプロジェクトルートの `.env` → `.env.local` を読み込みます（OS 環境変数優先）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須/任意）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注周りで使用）
- OPENAI_API_KEY (必須 for NLP) — OpenAI API キー（score_news / score_regime を使う場合）
- KABU_API_BASE_URL (任意) — kabu API のベースURL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (任意) — 通知連携用
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL

簡単な .env.example:

```
# .env.example
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル実行例）

1. リポジトリをクローンして依存をインストール
2. .env を作成して必要なキーを設定（上の例参照）
3. データ格納用ディレクトリを作成（必要に応じて）:

```bash
mkdir -p data
```

4. DuckDB を初期化（監査用DBを作る例）:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection
```

5. ETL を実行（Python スクリプト / cron などで実行）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

---

## 使い方（主要API例）

- ETL（日次パイプライン）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメントスコアの算出（ai.news_nlp.score_news）

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # returns number of codes written
print("written:", written)
```

- 市場レジーム判定（ai.regime_detector.score_regime）

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（research）

```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records: list of dict with keys like 'code', 'mom_1m', 'ma200_dev'...
```

- データ品質チェック

```python
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

---

## 注意点 / 運用メモ

- OpenAI 呼び出しは外部APIに依存します。APIキーを環境変数 OPENAI_API_KEY に設定してください。API失敗時はフェイルセーフ（0.0 を返す等）の実装がありますが、結果の解釈には注意してください。
- J-Quants API にはレート制限があります（120 req/min）。jquants_client は内部でスロットリングとリトライを行います。
- 日付の扱いはルックアヘッドバイアス防止を重視しています。関数は target_date を引数で受け取り、内部で date.today() / datetime.today() を直接参照しない設計が意図されています（ただし一部ジョブは現在日付を使います）。
- DuckDB の executemany に対する互換性（空リスト許容等）を考慮した実装がなされています。バージョン差異に注意してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。CI やテストで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

概要ツリー（src/kabusys 配下）:

```
src/kabusys/
├── __init__.py             # パッケージ定義、__version__ 等
├── config.py               # 環境変数/設定管理
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py         # ニュースセンチメントスコアリング
│   └── regime_detector.py  # 市場レジーム判定
├── data/
│   ├── __init__.py
│   ├── jquants_client.py   # J-Quants API client + save_* 関数
│   ├── pipeline.py         # ETL パイプライン（run_daily_etl 等）
│   ├── news_collector.py   # RSS 収集
│   ├── calendar_management.py
│   ├── quality.py
│   ├── stats.py
│   ├── audit.py            # 監査ログスキーマ初期化
│   ├── etl.py              # ETLResult 再エクスポート
│   └── ...                 # 他ユーティリティ
├── research/
│   ├── __init__.py
│   ├── factor_research.py
│   └── feature_exploration.py
└── research/...            # 研究用ユーティリティ
```

---

## 貢献 / ライセンス

- この README はコードベースに基づく概要説明です。実運用・本番運用前に十分なテストとセキュリティレビューを行ってください（特に API キー管理、発注ロジック、ネットワーク周り）。
- ライセンス情報やコントリビュートルールはリポジトリの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

必要であれば、README に README の英語版、CI 実行手順、デプロイ/cron の例、詳細な .env.example（全変数列挙）やよくあるエラーと対処方法を追加できます。どの情報を補足しますか？