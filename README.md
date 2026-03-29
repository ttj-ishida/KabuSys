# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、研究用ファクター計算、監査ログ（オーダー／約定トレーサビリティ）、および市場レジーム判定などを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムとデータ基盤向けに設計された Python モジュール群です。主な目的は次のとおりです。

- J-Quants API からの株価・財務・マーケットカレンダーの差分 ETL（DuckDB 保存、冪等性確保）
- RSS 等からのニュース収集と前処理、ニュースに対する LLM（OpenAI）を用いた銘柄別センチメントスコア算出
- マーケット（ETF）ベースのテクニカル指標とマクロニュースを合成した市場レジーム判定
- 研究用のファクター（モメンタム/バリュー/ボラティリティ等）算出、将来リターン・IC 等の統計解析ユーティリティ
- 監査ログ（signal / order_request / executions）向けの DuckDB スキーマ初期化とユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計上の特徴として、ルックアヘッドバイアス対策、冪等処理、堅牢なリトライ / レートリミット制御、外部 API 呼び出し時のフェイルセーフ、SQL による効率的な集計処理を重視しています。

---

## 機能一覧

- data
  - ETL（data.pipeline）
    - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
    - ETL 結果を ETLResult オブジェクトで取得
  - J-Quants クライアント（data.jquants_client）
    - fetch_* / save_*（daily quotes / financial statements / market calendar / listed info）
    - トークン自動リフレッシュ、固定間隔レート制限、冪等保存
  - カレンダー管理（data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - ニュース収集（data.news_collector）
    - RSS 取得、前処理、記事ID生成、SSRF 対策、保存前処理
  - 監査ログ（data.audit）
    - init_audit_schema / init_audit_db（signal / order_requests / executions テーブル）
  - 品質チェック（data.quality）
    - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - 統計ユーティリティ（data.stats）
    - zscore_normalize

- ai
  - news_nlp.score_news: 複数銘柄を gpt-4o-mini へ送り JSON レスポンスから銘柄スコアを取得、ai_scores へ保存
  - regime_detector.score_regime: ETF(1321) の 200 日 MA 乖離とマクロニュースの LLM スコアを合成して market_regime テーブルへ保存

- research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize を組み合わせた解析ワークフローに対応

- config
  - 環境変数 / .env 自動読み込み、Settings 経由で設定を取得

---

## 必要条件 / 推奨環境

- Python >= 3.10（typing の union 表記や from __future__ の使用を前提）
- 必須 Python パッケージ（主なもの）
  - duckdb
  - openai（OpenAI Python SDK）
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS 等）
- J-Quants のリフレッシュトークン、OpenAI API キー等のシークレット

インストール例（仮の例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# パッケージとしてセットアップ済みなら:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）
2. Python 仮想環境を作って依存をインストール（上記参照）
3. プロジェクトルートに .env を作成（config.Settings が自動で .env / .env.local を読み込みます）
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

例: .env (プロジェクトルート)
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabu station API（必要に応じて）
KABU_API_PASSWORD=your_kabu_password
# KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知用)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス（任意、デフォルト: data/kabusys.duckdb）
DUCKDB_PATH=data/kabusys.duckdb

# 動作環境
KABUSYS_ENV=development  # development|paper_trading|live
LOG_LEVEL=INFO
```

必須環境変数（Settings により取得され、未設定時はエラー）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意:
- KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL

4. DuckDB 用ディレクトリの作成（必要な場合）
```bash
mkdir -p data
```

---

## 使い方（主要な例）

以下はライブラリを直接呼び出すサンプルです。実行前に .env の設定とパッケージ依存を満たしてください。

- DuckDB に接続して ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を指定しなければ今日が対象（内部で営業日に調整される）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか api_key 引数を渡す）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"scored {count} symbols")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/monitoring_audit.duckdb")
# または既存 conn に対して init_audit_schema(conn)
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore_normalize は data.stats にあります
from kabusys.data.stats import zscore_normalize
norm = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- RSS フィードからニュースを取得（news_collector のユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"])
```

---

## ディレクトリ構成（主なファイル）

リポジトリ内の主要モジュールを抜粋しています（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                -- 環境変数 / .env 管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュース NLP（OpenAI 呼び出し・ai_scores 書込）
    - regime_detector.py     -- 市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py            -- ETL パイプライン (run_daily_etl 等)
    - jquants_client.py      -- J-Quants API クライアント / 保存ユーティリティ
    - calendar_management.py -- 市場カレンダー管理関数
    - news_collector.py      -- RSS 収集 / 前処理 / SSRF 対策
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（zscore_normalize 等）
    - audit.py               -- 監査ログスキーマ初期化
    - etl.py                 -- ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     -- モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py -- forward returns, IC, summary, rank

---

## 設定と動作モード

- KABUSYS_ENV（development / paper_trading / live）
  - settings.is_dev / is_paper / is_live で分岐可能
- LOG_LEVEL（DEBUG, INFO, ...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動読み込みを無効化可能
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から .env → .env.local の順で行われ、.env.local は上書きされます（OS 環境変数は保護されます）。

---

## トラブルシューティング

- OpenAI API キーがない / 未設定:
  - score_news / score_regime は api_key 引数か環境変数 OPENAI_API_KEY が必要。未設定だと ValueError を送出します。
- J-Quants トークン:
  - JQUANTS_REFRESH_TOKEN が settings で必須。get_id_token() を経て ID トークンを取得します。
- DuckDB ファイルの作成権限:
  - 設定した DUCKDB_PATH の親ディレクトリが存在しない場合は作成してください（init_audit_db は親ディレクトリを自動作成します）。
- ネットワーク周り:
  - news_collector は SSRF対策やレスポンスサイズ制限を行います。RSS の最終 URL がプライベートアドレスの場合は取得を拒否します。
- ETL 実行中の partial failure:
  - run_daily_etl は各ステップで例外をキャッチして処理を継続します。結果は ETLResult.errors / quality_issues に集約されます。

---

## 開発 / テストについて

- ユニットテストでは外部 API 呼び出し（OpenAI / J-Quants / HTTP）はモックしてテストすることを想定しています。コード内にモック容易化のための分離（例: _call_openai_api の差し替えポイント等）が用意されています。
- ロギングは各モジュールで logger = logging.getLogger(__name__) を使用しています。必要に応じてルートロガーを設定してください。

---

もし README の補足（例: 実行スクリプト、CI 設定、詳細な schema 定義、サンプル .env.example の生成など）が必要であれば、用途に合わせて追記します。