# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
データ収集（J-Quants）、データ品質チェック、特徴量/ファクター計算、ニュースのNLPスコアリング、マーケットレジーム判定、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主なAPI例）
- 環境変数（.env）例
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／研究プラットフォーム向けのライブラリセットです。  
主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダー等の差分ETL
- raw データの品質チェック（欠損・スパイク・重複・日付不整合）
- ニュースの収集と LLM（OpenAI）を使った銘柄別センチメントスコア算出
- ETF に基づく市場レジーム判定（MA + マクロニュースセンチメントの合成）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- 監査ログ（signal → order_request → execution のトレース可能なスキーマ）
- DuckDB を用いたローカルデータ管理

設計方針の一部：
- ルックアヘッドバイアス防止（内部で date.today() を直接参照しない箇所が多い）
- 冪等性（ETL 保存は ON CONFLICT/UPDATE）
- フェイルセーフ（外部API失敗時はスキップorデフォルトで継続）
- DuckDB を中心に SQL + Python で実装（外部 heavy 依存を最小化）

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env 自動読み込み（OS env > .env.local > .env）
  - 設定取得ラッパー（JQUANTS_REFRESH_TOKEN 等）

- kabusys.data
  - jquants_client: J-Quants API の取得/保存（株価・財務・カレンダー・上場情報）
  - pipeline: 日次 ETL 実行 run_daily_etl（差分取得・保存・品質チェック）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - news_collector: RSS 取得・正規化・raw_news への保存ロジック
  - calendar_management: 営業日判定 / next/prev_trading_day / calendar_update_job
  - audit: 監査ログスキーマ初期化（signal_events, order_requests, executions）
  - stats: zscore_normalize 等

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に格納
  - regime_detector.score_regime: ETF（1321）のMA乖離とニュースセンチメントを合成して market_regime に保存

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（型注釈に PEP 604 等を使用）
- DuckDB を利用（pip パッケージ duckdb）
- OpenAI Python SDK（openai）を利用
- defusedxml（RSS解析の安全対策）

例: 仮想環境の作成と依存インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd <repo>

# 仮想環境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 必要なパッケージをインストール（例）
pip install duckdb openai defusedxml
# もし package 化されていれば editable install:
# pip install -e .
```

推奨される requirements.txt（例）
```
duckdb
openai
defusedxml
```

注意:
- OpenAI API を用いるため、OpenAI のアカウントと API キーが必要です。
- J-Quants API を利用するには J-Quants のリフレッシュトークンが必要です。
- 実行環境によっては追加のネットワーク/プロキシ設定が必要です。

---

## 使い方

以下は代表的な利用例とコードスニペットです。すべて Python スクリプトや REPL から実行できます。

1) 設定のロード
- 環境変数は自動で .env / .env.local からロードされます（プロジェクトルートに .git または pyproject.toml があることが条件）。
- 自動ロードを無効にする場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

2) DuckDB 接続を作成して日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path 型でデフォルト: data/kabusys.duckdb
conn = duckdb.connect(str(settings.duckdb_path))

# 今日分の ETL（引数を date オブジェクトで指定して過去日向けにも実行可）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニューススコアリング（OpenAI API キー必須）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")  # api_key を省略すると環境変数 OPENAI_API_KEY を参照
print(f"書き込んだ銘柄数: {n_written}")
```

4) 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # None だと OPENAI_API_KEY を参照
```

5) 監査ログDB初期化

```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/monitoring.duckdb")  # ":memory:" も可
# 以降、order_requests / executions 等に書き込めます
```

6) カレンダー更新ジョブ（J-Quants から差分取得）

```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

7) 研究用ファクター計算

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

備考:
- 上の関数群は DuckDB 上の特定テーブル（raw_prices, raw_financials, raw_news, news_symbols, prices_daily など）を前提に動作します。ETL を実行しテーブルが存在する状態で使用してください。
- OpenAI 呼び出しは API 制限やコストに注意してください。失敗時は設計上フォールバック（スコア=0 等）が行われますが、ログを必ず確認してください。

---

## 環境変数（.env）例

プロジェクトは .env / .env.local による設定をサポートします。主なキー:

- JQUANTS_REFRESH_TOKEN (必須)  
- OPENAI_API_KEY (OpenAI 呼び出しに使用)
- KABU_API_PASSWORD (kabuステーション API 用)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知用)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視データ用)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env ロードを無効化

例 (.env.example):

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

- .env の読み込みルール: OS 環境変数 > .env.local > .env（.env.local が .env を上書き）
- .env ファイルの詳細なパース挙動は kabusys.config 内に実装されています（export 形式、引用符、コメント等に対応）。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - audit.py
    - stats.py
    - pipeline.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (placeholder in __all__ — 実装があれば監視関連)
  - execution/, strategy/ (パッケージ配布時に存在想定)

（上記はリポジトリの現状の主要モジュールに基づく）

---

## 開発・貢献

- テスト: 各モジュールはネットワーク呼び出しを行う箇所があるため、ユニットテストでは外部呼び出し（OpenAI, J-Quants, RSS 等）をモックすることを推奨します。関数内部でモック可能な `_call_openai_api` や HTTP の `urlopen` などの差し替えポイントがあります。
- 依存関係の追加・管理は requirements.txt または pyproject.toml を利用してください。
- セキュリティ: news_collector は SSRF や XML Bomb 対策（defusedxml、ホスト検査、最大バイト数制限）を考慮しています。外部RSSを扱う場合はロギングと検証を徹底してください。

---

## 注意事項

- 実運用で発注を行う場合は、発注ロジック・監査・リスク管理の十分な検証が必須です。本ライブラリの研究/開発用のコードをそのまま本番で使用することは推奨しません。
- OpenAI 利用や外部APIの呼び出しはコスト・レート制限に留意してください。
- DuckDB のバージョンによっては executemany の空リスト挙動など互換性がある点に注意しています（実装内に回避ロジックあり）。

---

README に記載されていない利用方法・追加の API の詳細は各モジュールの docstring を参照してください。必要に応じて README を拡張しますので、追加で載せたいサンプルや手順があれば教えてください。