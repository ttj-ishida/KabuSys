# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。J-Quants からのデータ取得・ETL、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ・発注トレーサビリティなどを含むモジュール群を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API を通じた株価・財務・カレンダー等の差分ETL
- RSS ニュースの収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄単位）および市場レジーム判定
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（signal / order_request / executions 等）のスキーマ初期化と管理
- DuckDB を主要な永続化ストレージとして想定

設計方針としては、ルックアヘッドバイアス回避、冪等性（ON CONFLICT）、外部APIのリトライ／レート制御、安全なRSS取得（SSRF対策）などが組み込まれています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API 経由の取得・保存（株価、財務、カレンダー、上場情報）
  - pipeline / etl: 日次 ETL パイプライン（差分取得・保存・品質チェック）
  - news_collector: RSS 収集、前処理、raw_news への保存用ユーティリティ
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - quality: データ品質チェック（missing, duplicates, spike, date consistency）
  - audit: 監査ログテーブル定義と初期化ユーティリティ
  - stats: z-score 正規化などの統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄毎のニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime を更新
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数読み込み（.env / .env.local 自動読み込み、オーバーライド制御）
  - settings オブジェクト経由で設定参照

---

## セットアップ手順

前提
- Python 3.10 以上（コード内で `X | None` などの構文を使用）
- Git（.git をプロジェクトルートに置くことで .env 自動読み込みが有効になる想定）

例: 仮想環境の作成と依存のインストール

```bash
# 仮想環境作成
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# pip を最新化
pip install -U pip

# 必要なパッケージをインストール
pip install duckdb openai defusedxml
# （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
```

環境変数（.env）の準備
- プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（テスト時など自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
- サンプル（.env.example としてプロジェクトに用意してください）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション（任意）
KABU_API_PASSWORD=...

# システム
KABUSYS_ENV=development
LOG_LEVEL=INFO

# DB パス（例）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

主要な依存:
- duckdb
- openai
- defusedxml

（追加ユーティリティが必要な場合はプロジェクトの packaging / requirements ファイルを参照してください）

---

## 使い方（主要 API とサンプル）

以下は主要な機能の利用例です。実行時は適切に環境変数を設定しておいてください。

1) 日次 ETL を実行する（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントを計算して ai_scores に保存（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定済みであれば api_key 引数は不要
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

3) 市場レジーム判定を行い market_regime を更新（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査用 DuckDB を初期化する（監査テーブル作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions 等のテーブルが作成されます
```

5) RSS フィード取得ユーティリティ（ニュース収集の内部で使用）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

注意点
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON モードで厳密な JSON を返すようプロンプトが設計されています。API レスポンスのバリデーションとリトライが組み込まれていますが、テスト時は _call_openai_api をモックしてください（コード内コメント参照）。
- ETL / 保存処理は DuckDB の `ON CONFLICT` を利用して冪等動作を目指しています。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD: kabu ステーション API パスワード（order 実装等で利用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視関連
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

詳細は kabusys.config.Settings のプロパティ実装を参照してください。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要モジュール構成（src/kabusys 以下の抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py            -- 銘柄毎ニュースセンチメント（score_news）
    - regime_detector.py     -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（fetch / save）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETLResult 再公開
    - calendar_management.py -- 市場カレンダー管理（is_trading_day 等）
    - news_collector.py      -- RSS 収集・前処理
    - quality.py             -- 品質チェック
    - stats.py               -- zscore_normalize 等
    - audit.py               -- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py     -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py -- calc_forward_returns / calc_ic / factor_summary / rank
  - research/* (その他)

各モジュールはドキュメンテーション文字列（docstring）で振る舞いが説明されています。実装コメントも豊富です。

---

## 開発・テストに関するメモ

- 自動 .env 読み込みはプロジェクトルートの .git または pyproject.toml を検知して行います。テスト等で自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し (_call_openai_api) やネットワーク I/O 部分は unittest.mock.patch 等で差し替えることで単体テストが容易です（モジュール内のコメントを参照）。
- DuckDB を使っているため、テスト用に ":memory:" を指定してインメモリ DB に接続できます（init_audit_db などは ":memory:" を受け付けます）。
- RSS 収集は defusedxml を利用して XML 攻撃から保護していますが、外部へのネットワークアクセスを伴うため CI ではネットワークをモックしてください。

---

## ライセンス・貢献

（ここにライセンス情報や貢献方法を記載してください。プロジェクトに LICENSE ファイルがあればその内容を参照してください。）

---

README に記載した以外の詳細はソースコード内の docstring / コメントを参照してください。必要であれば、サンプルスクリプトや .env.example を追加で作成するのを手伝います。