# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。データ取得（J‑Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログなど自動売買システムで必要となる主要機能を集約しています。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（サンプル）
- 環境変数
- ディレクトリ構成
- トラブルシューティング / 注意点

---

## プロジェクト概要
KabuSys は日本株自動売買システムのためのユーティリティ群です。主に以下を提供します。

- J‑Quants API を用いた株価・財務・カレンダーの差分取得（Rate limit / retry 対応）
- DuckDB を利用した ETL パイプライン（差分取得・保存・品質チェック）
- RSS ベースのニュース収集と前処理（SSRF / Gzip / トラッキング除去対策）
- OpenAI を使ったニュースセンチメント評価（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Zスコア）
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）

設計上、バックテストで「ルックアヘッドバイアス」を起こさないように日時の扱いに注意を払っています（関数は `date.today()` 等に依存しないよう設計）。

---

## 主な機能一覧
- data/jquants_client.py
  - J‑Quants との通信、ページネーション・認証リフレッシュ・リトライ・保存（DuckDB）機能
- data/pipeline.py / data/etl.py
  - 日次 ETL（run_daily_etl）・個別 ETL（株価・財務・カレンダー）
  - ETL 結果クラス ETLResult
- data/quality.py
  - 欠損・スパイク・重複・日付整合性チェック
- data/news_collector.py
  - RSS 取得・前処理（URL 正規化、トラッキング除去、SSRF 対策）
- ai/news_nlp.py
  - 銘柄ごとのニュースをまとめて OpenAI（gpt-4o-mini）でスコア化し ai_scores に書き込む
- ai/regime_detector.py
  - ETF 1321 の 200 日 MA 乖離 + マクロニュースの LLM 評価で市場レジーム判定
- research/*
  - ファクター計算（Momentum / Value / Volatility）、前方リターン、IC、統計サマリ
- data/audit.py
  - 監査ログスキーマ（signal_events / order_requests / executions）初期化ユーティリティ
- config.py
  - 環境変数の読み込み（.env 自動ロード）と設定アクセサ

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の | アノテーション等を使用）
- ネットワーク接続（J‑Quants、OpenAI など）

1. リポジトリをチェックアウト / クローン

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （実プロジェクトでは requirements.txt / pyproject.toml を用意して pip install -e . などを使ってください）

4. 環境変数 / .env の準備
   - プロジェクトルート（pyproject.toml または .git があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須変数の例は下記「環境変数」セクションを参照してください。

5. DuckDB の準備
   - デフォルト DB パスは `data/kabusys.duckdb`。settings.duckdb_path から変更できます。

---

## 環境変数（主要）
必須（多くの機能で参照されます）:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知を利用する場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- KABU_API_PASSWORD — kabu ステーション API のパスワード（必要な場合）

任意 / デフォルトあり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト "development"）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト "INFO"）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動ロードを無効化
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視データ等の SQLite（デフォルト data/monitoring.db）
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / regime_detector に使用）

簡単な .env の例:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（サンプル）

以下はライブラリ内の主要な関数の使用例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作る（ファイル DB を使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日が対象（内部で営業日に調整される）
result = run_daily_etl(conn, target_date=None, id_token=None)
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を生成（OpenAI API キーが必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを組み合わせる）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用の DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn に対して signal_events / order_requests / executions テーブルが作成される
```

- RSS フィードを取得する（メモリ上で処理して DB 保存は呼び出し側で行う）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
# raw_news テーブルへの保存はプロジェクト固有の保存処理を実装して行ってください
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの辞書リスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

注意: 上記の ai 関連関数は OpenAI の Chat Completions（gpt-4o-mini）を利用します。API キーが環境変数 OPENAI_API_KEY に設定されていることを確認してください。呼び出しはライブラリ内でリトライ・フェイルセーフ処理を行いますが、API 制限や料金に注意してください。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 配下）

- __init__.py — パッケージ初期化（__version__ = "0.1.0"）
- config.py — 環境変数読み込み・Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント集約・OpenAI 呼び出し
  - regime_detector.py — 市場レジーム判定ロジック
- data/
  - __init__.py
  - jquants_client.py — J‑Quants API クライアント（取得・保存）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポートインターフェース
  - news_collector.py — RSS ニュース収集、前処理
  - calendar_management.py — JPX カレンダー管理・営業日判定
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック
  - audit.py — 監査ログスキーマの初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility 等
  - feature_exploration.py — 将来リターン / IC / 統計サマリ / rank

---

## トラブルシューティング / 注意点
- 環境変数未設定で値を参照すると Settings が ValueError を投げます（必須変数は _require によりチェック）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テストや特殊環境で無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J‑Quants 側のレート制限（120 req/min）を守るため内部でスロットリングを実施しています。大量データ取得の際は時間がかかる場合があります。
- OpenAI 呼び出しはリトライやフェイルセーフ（失敗時は 0.0 など）を行いますが、API コスト・レート制限に注意してください。
- DuckDB 側の executemany で空リスト渡すとエラーとなるバージョンがあります（コード内で対応済み）。
- news_collector は RSS → NewsArticle 取得までを担当します。DB 保存はプロジェクト固有の保存ロジック（raw_news への挿入）を利用してください。
- 監査スキーマ（audit）を初期化する際は TimeZone を UTC に固定するため init_audit_db / init_audit_schema を利用してください。

---

この README はコードベースの主要機能をまとめたものです。実運用では pyproject.toml / requirements.txt に依存関係を明示し、環境ごとの .env 管理（例: .env.example）を整備してください。必要であれば README に具体的な DB スキーマ定義や運用スケジュール（cron / Airflow ジョブ例）を追加できます。