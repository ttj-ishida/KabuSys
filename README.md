# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注/約定のトレース）等のユーティリティを提供します。

---

## 主な特徴

- データ収集・ETL
  - J-Quants API から株価日足・財務情報・JPX カレンダーを差分取得・保存（DuckDB）
  - レート制御・リトライ・トークン自動リフレッシュ対応
- ニュース収集・NLP
  - RSS からニュースを収集し前処理／保存
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメントスコアリング（ai_scores へ書込み）
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン算出、IC（スピアマン）や統計サマリー
- データ品質チェック
  - 欠損値・スパイク・重複・日付不整合のチェックを実行
- 監査ログ
  - signal → order_request → execution のトレース可能な監査スキーマを DuckDB に初期化

---

## 機能一覧（主要 API）

- 設定
  - kabusys.config.settings: 必須環境変数やパスを参照する設定オブジェクト
- ETL / データ
  - kabusys.data.pipeline.run_daily_etl(conn, target_date=...)
  - kabusys.data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl
  - kabusys.data.jquants_client.fetch_* / save_*（J-Quants API クライアント）
  - kabusys.data.news_collector.fetch_rss / preprocess_text
  - kabusys.data.quality.run_all_checks / check_missing_data / check_spike / ...
  - kabusys.data.calendar_management.is_trading_day / next_trading_day / get_trading_days
- ニュース NLP / レジーム
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- リサーチ
  - kabusys.research.calc_momentum / calc_value / calc_volatility
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.data.stats.zscore_normalize
- 監査ログ初期化
  - kabusys.data.audit.init_audit_db(db_path) / init_audit_schema(conn)

---

## セットアップ手順

前提
- Python 3.10+ を想定（PEP 604 の union 型記法などを使用）
- DuckDB, OpenAI SDK, defusedxml 等が必要

推奨インストール例:

1. 仮想環境作成（例）
   python -m venv .venv
   source .venv/bin/activate

2. 必要パッケージのインストール（例）
   pip install duckdb openai defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

3. 環境変数 / .env の準備  
   プロジェクトルート（pyproject.toml または .git のあるディレクトリ）に `.env` / `.env.local` を置くことで自動読み込みされます。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（例）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - OPENAI_API_KEY=...

   任意（デフォルト値あり）:
   - KABUSYS_ENV=development|paper_trading|live (default: development)
   - LOG_LEVEL=INFO (default)
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABU_API_BASE_URL (kabuステーションの URL; default: http://localhost:18080/kabusapi)

   .env のフォーマットは一般的な KEY=VAL を想定し、'export ' プレフィックスやクォートにも対応しています。

---

## 使い方（例）

以下は簡単なサンプルコード。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作成して日次 ETL を実行する:

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY か引数で渡す）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str("/path/to/your.duckdb"))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str("/path/to/your.duckdb"))
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数か api_key 引数
```

- 監査用 DuckDB を初期化（監査スキーマの作成）:

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルに書き込み／クエリが可能
```

- カレンダー関連ユーティリティ:

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for NLP / regime modules) — OpenAI API キー
- KABU_API_PASSWORD (必須 if using kabu API)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須 if Slack 通知を使う)
- DUCKDB_PATH (任意, default: data/kabusys.duckdb)
- SQLITE_PATH (任意, default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動ロードを無効化

---

## ディレクトリ構成（要約）

リポジトリの主要なソースは `src/kabusys` にあります。主なファイル／ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（.env 自動ロードロジック含む）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの LLM スコアリング、score_news を公開
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch / save）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - news_collector.py       — RSS 取得・正規化・保存ロジック
    - calendar_management.py  — JPX カレンダー管理 / 営業日判定
    - quality.py              — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py                — z-score 等の統計ユーティリティ
    - audit.py                — 監査ログテーブル定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility 等の計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー / rank
  - ai, research, data 以下はそれぞれのドメイン固有のユーティリティをまとめています。

---

## 設計上のポイント / 注意点

- Look-ahead bias 防止
  - 多くのモジュールは内部で datetime.today() を直接参照せず、引数の target_date を基準に処理します。バックテスト目的での利用時は target_date を正しく制御してください。
- フォールバック設計
  - カレンダーが未取得の場合は曜日ベースのフォールバックを行う等、可用性を重視した実装が多くあります。
- OpenAI / J-Quants 呼び出しはリトライ・バックオフやエラーハンドリングを実装していますが、API 使用量や課金には注意してください。
- DuckDB の executemany で空リストを渡すとバージョンによってエラーになるため、モジュール内部でガードしています（互換性への配慮）。

---

## 開発 / テスト

- 単体テストやモックを用いたテストが可能なように、外部 API 呼び出し点は小さなラッパー関数として切り出されています（例: _call_openai_api の差し替え等）。
- 自動テスト時に環境変数の自動ロードを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

疑問点や追加してほしいサンプル（例: デプロイ手順、CI 設定、より詳細な .env.example）などがあれば教えてください。README を拡張して必要な情報を追加します。