# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、研究用ファクター計算、監査ログ / 発注トレーサビリティなどの機能群を提供します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数（.env 例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS によるニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄別 ai_score / マクロセンチメント）
- 研究用途のファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal_events / order_requests / executions）用の DuckDB スキーマ初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 設定管理（.env 自動読み込み / 環境変数）

設計方針の特徴:
- Look-ahead bias を避ける実装（内部で date.today()/datetime.today() に依存しない設計が多い）
- 冪等性（DB への保存は ON CONFLICT で上書き）
- 外部 API 呼び出しに対するリトライ・バックオフ・フェイルセーフ処理
- DuckDB をデータプラットフォームの単一ソースとして利用

---

## 機能一覧

主なモジュールと提供機能（抜粋）

- kabusys.config
  - .env の自動読み込み（プロジェクトルート検出：.git / pyproject.toml）
  - Settings クラスで環境変数を型変換してアクセス

- kabusys.data
  - ETL パイプライン（data.pipeline.run_daily_etl など）
  - J-Quants クライアント（data.jquants_client）
  - カレンダー管理（data.calendar_management）
  - ニュース収集（data.news_collector）
  - データ品質チェック（data.quality）
  - 統計ユーティリティ（data.stats）
  - 監査ログスキーマ初期化（data.audit.init_audit_db / init_audit_schema）

- kabusys.ai
  - ニュース NLP（ai.news_nlp.score_news）：銘柄ごとの ai_score を作成して ai_scores テーブルへ
  - 市場レジーム判定（ai.regime_detector.score_regime）：ETF 1321 の MA200 とマクロニュースを合成

- kabusys.research
  - ファクター計算（research.factor_research: calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（research.feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank）
  - zscore_normalize の再利用

---

## セットアップ手順

想定 Python バージョン: 3.10 以上（typing の | などを使用）

1. リポジトリをクローンする
   ```bash
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境を作って依存をインストール
   requirements.txt がない場合は主要依存を個別にインストールしてください（例）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb openai defusedxml
   # 追加で必要なパッケージがあればインストール
   ```

   パッケージを手元で編集して使う場合:
   ```bash
   pip install -e .
   ```

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を配置できます。
   - 自動読み込みはデフォルトで有効。無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします。
   - 必要な環境変数の例は次章「環境変数（.env 例）」を参照してください。

4. DuckDB データベース用ディレクトリを作成（settings.duckdb_path の親ディレクトリ）
   - デフォルト: `data/kabusys.duckdb`
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要 API の例）

以下は最小限の利用例です。実行前に必要な環境変数（J-Quants の refresh token、OpenAI API key など）を設定してください。

- DuckDB 接続と監査スキーマ初期化
```python
import duckdb
from kabusys.data.audit import init_audit_db, init_audit_schema

# ファイル DB を初期化して接続を得る（:memory: も可）
conn = init_audit_db("data/audit.duckdb")
# あるいは既存接続に対してスキーマを追加
# conn = duckdb.connect("data/kabusys.duckdb")
# init_audit_schema(conn, transactional=True)
```

- 日次 ETL 実行（J-Quants から株価・財務・カレンダーを取得して保存）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア生成（ai -> ai_scores へ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
print("written:", n_written)
```

- 市場レジーム判定（ma200 とマクロニュースを合成して market_regime に保存）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- ニュース RSS 取得（単体テスト・収集確認）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

注意:
- OpenAI 呼び出しを行う関数は api_key を引数で渡すか、環境変数 `OPENAI_API_KEY` を用いてください。
- J-Quants の認証は `JQUANTS_REFRESH_TOKEN`（Settings で参照）から ID トークンを取得します。

---

## 環境変数（.env 例）

kabusys はプロジェクトルートの `.env` / `.env.local` を自動ロードします（OS 環境変数が優先、.env.local は上書き）。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

推奨される最低限の .env 例:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
# KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス（相対 or 絶対）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 監視 / 実行関連
PID_FILE_PATH=data/execution.pid
CPU_THRESHOLD_PCT=90.0
MEMORY_THRESHOLD_PCT=85.0
DISK_THRESHOLD_PCT=90.0

# システム環境
KABUSYS_ENV=development    # development | paper_trading | live
LOG_LEVEL=INFO
```

設定は `from kabusys.config import settings` 経由でアクセスできます。例:
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.is_live)
```

必須 env（アプリで参照されると例外になるもの）
- JQUANTS_REFRESH_TOKEN
- OPENAI_API_KEY（ai モジュール使用時）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知を利用する場合）
- KABU_API_PASSWORD（kabuAPI を利用する場合）

---

## 注意点 / 運用メモ

- Look-ahead bias を避けるため、関数は基本的に引数で target_date を受け取り、内部で現在日時を参照しない実装が推奨されます（テスト・バックテストで再現性が高い）。
- OpenAI 呼び出しは冗長性のためリトライやフォールバック（失敗時は 0.0 など）を行う設計ですが、API 利用料とレート制限に注意してください。
- J-Quants API はレート制限（120 req/min）を意識して実装済み（モジュール内 RateLimiter）。
- DuckDB の executemany に関する実装上の注意（空リスト禁止）をコード内で扱っています。
- ニュース収集は SSRF / XML Bomb 対策（defusedxml、ホスト検証、最大受信バイト数）を実装しています。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル構成の抜粋です：

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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールの役割は本 README の「機能一覧」と該当ソースの docstring に詳述されています。

---

## 最後に

この README はリポジトリの主要機能と利用開始手順をまとめたものです。個別の関数やクラスの詳細はソースコード内の docstring を参照してください。使い始めや運用で不明点があれば、どの操作（ETL / AI スコア / 監査初期化）について知りたいかを教えてください。具体例や補足コマンドを追加で用意します。