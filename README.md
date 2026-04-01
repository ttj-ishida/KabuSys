# KabuSys

日本株向けの自動売買・データプラットフォーム（ライブラリ）。  
DuckDBベースのデータパイプライン、ニュースNLP / 市場レジーム推定、ファクター計算、監査ログ/発注トラッキングなどを含みます。

バージョン: 0.1.0

## 概要

KabuSys は以下の機能群を提供する Python パッケージです。

- J-Quants API からのデータ取得（株価日足、財務データ、JPX カレンダー）
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集（RSS）と LLM を用いた銘柄単位のセンチメントスコアリング
- マクロニュース + ETF (1321) MA200乖離を用いた市場レジーム判定
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ）と特徴量解析ユーティリティ
- 監査ログ（signal / order_request / executions）用スキーマ初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計方針として、ルックアヘッドバイアス回避、冪等性、フェイルセーフ（API失敗は無視して続行）を優先しています。

---

## 主な機能一覧

- data.jquants_client: J-Quants との通信（取得 + DuckDB 保存）
- data.pipeline: 日次 ETL のエントリポイント run_daily_etl 等
- data.news_collector: RSS 収集、前処理、raw_news への保存
- ai.news_nlp: ニュースを LLM（gpt-4o-mini）でバッチ評価して ai_scores に書き込み（score_news）
- ai.regime_detector: ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime を書き込む（score_regime）
- research.*: ファクター計算（momentum/volatility/value）と探索用ユーティリティ
- data.audit: 監査ログ用スキーマ作成・初期化（init_audit_schema / init_audit_db）
- data.quality: ETL 後の品質チェック群（run_all_checks）
- config: 環境変数/.env 管理（自動ロード・取得ユーティリティ）

---

## 要件

- Python 3.10+
- 必須パッケージ（主なもの）
  - duckdb
  - openai（OpenAI Python SDK）
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI API）

（pip の正確な依存バージョンは setup.py / pyproject.toml を参照してください）

---

## インストール

開発環境でのセットアップ例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# パッケージ依存をインストール（プロジェクトの pyproject.toml/setup.cfg に合わせて）
pip install duckdb openai defusedxml
# 開発用にローカルパッケージとしてインストールする場合
pip install -e .
```

---

## 環境変数（設定）

KabuSys は .env / .env.local をプロジェクトルート（.git または pyproject.toml の親）から自動で読み込みます（優先順位: OS 環境 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に使用する環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必要）
- KABU_API_PASSWORD: kabuステーション API パスワード（使用する場合）
- KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（通知などに使用する場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: デフォルト DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB などの SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視関連
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

必須項目（最低限動かすために必要なもの）:
- JQUANTS_REFRESH_TOKEN
- OPENAI_API_KEY（AI 機能を使う場合）

例（.env）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（初期化）

1. 環境を用意し、依存パッケージをインストール。
2. プロジェクトルートに .env（または .env.local）を作成して必要な環境変数を設定。
3. DuckDB データベースファイルの親ディレクトリを作成（多くの関数は自動で作成しますが、必要なら手動でも可）。

監査用 DB の初期化（例）:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# これで signal_events, order_requests, executions 等のテーブルが作成されます
```

---

## 使い方（主要な呼び出し例）

- 日次 ETL を実行する:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリング（AI）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使う
print(f"scored {n_written} symbols")
```

- 市場レジーム判定を行う:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使う
```

- ファクター計算（研究用）:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

- 監査スキーマをトランザクション付きで初期化:

```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 設定・挙動の注意点

- ルックアヘッドバイアス回避:
  - 多くの関数は内部で date.today() を直接参照せず、引数の target_date に基づいて処理します（バックテストでの誤用を防止）。
- .env の自動ロード:
  - パッケージインポート時にプロジェクトルートを探索して .env/.env.local を自動で読み込みます。テスト等で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI API 呼び出し:
  - gpt-4o-mini を想定し JSON Mode を利用します。API 呼び出しに失敗した場合はフェイルセーフとして 0.0 を返すか該当処理をスキップする設計です。
- J-Quants API:
  - レート制限（120 req/min）に合わせて内部で RateLimiter を使用しています。401 エラー時はリフレッシュトークンでトークン更新を試みます。

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 以下に配置されています）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env の自動読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py : ニュースを LLM で評価して ai_scores に書き込む（score_news）
    - regime_detector.py : ETF MA200 + マクロセンチメントで market_regime を作る（score_regime）
  - data/
    - __init__.py
    - jquants_client.py : J-Quants API クライアント（fetch / save）
    - pipeline.py : ETL パイプライン（run_daily_etl 等）、ETLResult
    - etl.py : ETLResult 再エクスポート
    - news_collector.py : RSS 収集と前処理
    - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py : zscore_normalize 等の統計ユーティリティ
    - calendar_management.py : 市場カレンダー管理（is_trading_day 等）
    - audit.py : 監査ログスキーマ定義と初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py : momentum / volatility / value の計算
    - feature_exploration.py : 将来リターン、IC、統計サマリー等

---

## ログ・実行環境

- 環境変数 `LOG_LEVEL`（デフォルト INFO）でログ出力レベルを制御します。
- KABUSYS_ENV（development / paper_trading / live）により動作モードを判定するユーティリティが Settings にあります（settings.is_live 等）。

---

## その他

- テストや CI についてはこの README では触れていませんが、モジュール内の設計は unittest.mock などによるモック差し替えを想定しています（例: OpenAI 呼び出しをモックするフックが各モジュールで用意されています）。
- セキュリティに配慮した実装（SSRF対策、defusedxml の利用、API レート/リトライ制御等）を行っています。

---

もし README に追加したい使い方例や CI / デプロイ手順、または .env.example の内容が必要であれば教えてください。