# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、ニュース収集・NLP（OpenAI）、ETL、監査ログ、リサーチ／ファクター計算、マーケット監視などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API を介した株価・財務・カレンダーの差分取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除外）
- OpenAI を使ったニュースセンチメント（ai.score_news）および市場レジーム判定（ai.score_regime）
- 監査ログ（signal → order_request → execution）用の DuckDB スキーマ初期化
- ファクター計算／特徴量探索（research パッケージ）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- マーケットカレンダー管理（営業日判定、next/prev trading day 等）

設計上の要点：
- ルックアヘッドバイアス防止（内部で datetime.today()/date.today() を直接参照する処理を極力排除）
- DuckDB を中心に SQL と軽量 Python 実装で高速処理
- 冪等性（ON CONFLICT 等）と堅牢なリトライ・バックオフロジック
- セキュリティ対策（RSS の SSRF 対策、defusedxml の利用等）

---

## 機能一覧

- data/
  - jquants_client: J-Quants からのデータ取得（株価、財務、カレンダー）と DuckDB 保存関数
  - pipeline: 日次 ETL（run_daily_etl）・個別 ETL（run_prices_etl 等）と ETLResult
  - news_collector: RSS 収集、前処理、raw_news への保存支援
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: market_calendar を扱うユーティリティ（is_trading_day 等）
  - audit: 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の汎用統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI で評価し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して市場レジーム判定
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config:
  - 環境変数管理（.env, .env.local 自動ロード／設定取得用 Settings）

---

## 必要条件（推奨）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- （実行環境に応じて）ネットワークアクセス（J-Quants API、OpenAI、RSS）

※ 実際の依存関係はプロジェクトの pyproject.toml / requirements.txt に合わせてインストールしてください。

---

## セットアップ手順（例）

1. リポジトリをクローンして作業ディレクトリへ
   - git clone ... && cd repo

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もしくは pyproject.toml を使う場合: pip install -e .

   ※ requirements.txt / pyproject.toml がない場合は最低限 duckdb / openai / defusedxml をインストールしてください。

4. 環境変数を設定
   - プロジェクトルートに .env または .env.local を作成できます（config モジュールが自動で読み込みます）。
   - 必須（Settings._require により参照される主要な環境変数）例:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（必要な場合）
     - SLACK_CHANNEL_ID: Slack 通知対象チャンネル
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注系を使う場合）
     - OPENAI_API_KEY: OpenAI 呼び出しを行う場合は環境変数または各関数引数で指定
   - 任意 / デフォルト値あり:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（監視用）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   - 自動 .env 読み込みはデフォルト ON。無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB ファイルディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な例）

以下は簡単な Python スニペット例です。実運用ではログ・例外処理を適切に追加してください。

- 基本：DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に保存する
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
cnt = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"scored {cnt} codes")
```

- 市場レジームを判定する
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査DBの初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

conn = init_audit_db(Path("data/audit.duckdb"))
# 以降 conn を使って order/signals/executions を記録する
```

- リサーチ関数の利用例
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄のファクターを含む dict のリスト
```

---

## 主要な環境変数（要設定）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY — OpenAI 呼び出し（ai.news_nlp / ai.regime_detector など）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注を行うなら）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 開発モード: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（例: INFO）

注意: config.Settings は .env / .env.local を自動読み込みします。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）

以下は主要ファイルの構成（src/kabusys 配下）です。実際のファイル一覧はリポジトリ内を参照してください。

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
    - quality.py
    - stats.py
    - calendar_management.py
    - audit.py
    - pipeline.py (ETLResult)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - (その他モジュール: strategy / execution / monitoring 等のパッケージ名が __all__ に含まれていますが、ここでは主に data/ ai/ research を中心に実装されています)

---

## 注意点 / 運用メモ

- OpenAI 呼び出しには API レートの考慮とリトライ設計が入っていますが、実行時のコスト・レート制限には注意してください（バッチサイズ等を調整）。
- ETL / 保存処理は DuckDB の互換性（executemany の空パラメータ問題など）を考慮しています。DuckDB のバージョンや挙動に依存する箇所があるため運用時は DuckDB バージョンを固定することを推奨します。
- news_collector は RSS の SSRF 対策・受信サイズ制限等の安全対策を実装しています。外部 RSS を追加する場合は信頼できるソースを指定してください。
- 本ライブラリはバックテストや実際の売買に用いる際に「ルックアヘッドバイアス」を防ぐ設計方針を掲げていますが、利用側（呼び出し方）でも日付引数等を正しく扱う必要があります。

---

README に記載してほしい追加情報や、サンプルスクリプト（CLI やデプロイスクリプト等）の要望があれば教えてください。必要に応じて README を拡張します。