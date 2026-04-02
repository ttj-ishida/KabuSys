# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買・リサーチ基盤を提供するライブラリです。J-Quants / kabuステーション / OpenAI 等と連携し、データ ETL、ニュース NLP、マーケットレジーム判定、ファクター計算、監査ログなどの機能群を備えています。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は以下です。

- J-Quants API を使った株価・財務・マーケットカレンダーの差分 ETL
- RSS ニュース収集と OpenAI による銘柄センチメント（ai_score）計算
- ETF の長期移動平均乖離とマクロニュースを使った市場レジーム判定（bull/neutral/bear）
- 研究用のファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 発注・約定までのトレーサビリティを保持する監査（audit）テーブル定義・初期化
- データ品質チェック（欠損、スパイク、重複、日付不整合等）
- DuckDB を中心としたローカルデータベース管理

設計上の注意点（抜粋）:
- ルックアヘッドバイアスの防止に配慮（内部で date.today() 等を無闇に参照しない）
- API 呼び出しに対するリトライ / バックオフとレート制御の実装
- ETL / 保存は冪等に設計（ON CONFLICT / UPSERT を利用）
- OpenAI との対話は JSON モードで厳格にパースしフォールバックを行う

---

## 機能一覧

- data/
  - jquants_client: J-Quants API からの取得 & DuckDB への保存（raw_prices, raw_financials, market_calendar, listed info 等）
  - pipeline: 日次 ETL の実行（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 収集と raw_news、news_symbols への保存（SSRF 対策・トラッキング除去 等）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日の判定・next/prev_trading_day、calendar_update_job
  - audit: 監査ログ（signal_events / order_requests / executions）のスキーマ初期化
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: 指定期間の raw_news を集約し OpenAI で銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に書き込む
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: 環境変数 / .env の自動読み込みと Settings（J-Quants トークン、kabu API パスワード、Slack トークン、DB パス 等）

---

## セットアップ手順

前提:
- Python 3.10+（typing | Future annotations を使用しているため）
- ネットワークから外部 API にアクセス可能（J-Quants / OpenAI 等）

1. リポジトリをクローン / プロジェクトルートへ移動

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate    # macOS / Linux
   - .venv\Scripts\activate.bat   # Windows

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   （プロジェクトに requirements.txt がない場合は少なくとも以下が必要）
   - pip install duckdb openai defusedxml

   開発用に editable install:
   - pip install -e .

4. 環境変数 / .env の準備
   プロジェクトルートに .env または .env.local を置くと自動でロードされます（config.py の自動ロードを有効にしている場合）。
   主要な環境変数（最低限）:

   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_station_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567
   - OPENAI_API_KEY=sk-...
   - DUCKDB_PATH=data/kabusys.duckdb        # 任意（デフォルト）
   - SQLITE_PATH=data/monitoring.db         # 任意
   - PID_FILE_PATH=data/execution.pid       # 任意
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # kabuAPI の URL（必要なら）
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO

   自動読み込みを無効にしたい場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要な API と実行例）

すべての例は Python REPL やスクリプトで実行できます。DuckDB には default path（data/kabusys.duckdb）が使われますが、Settings.duckdb_path でカスタマイズ可能です。

1. DuckDB 接続

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2. 日次 ETL 実行（run_daily_etl）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3. ニューススコアリング（OpenAI 必要）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API key を環境変数 OPENAI_API_KEY に設定しておくか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

4. 市場レジーム判定（regime_detector）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

# OpenAI API key を環境変数 OPENAI_API_KEY に設定しておくか、api_key 引数で渡す
score_regime(conn, target_date=date(2026, 3, 20))
```

5. 監査ログ DB 初期化

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
# 必要な監査テーブルが作成される
```

6. 研究用ファクター計算／探索

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

fwd = calc_forward_returns(conn, d)
ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
```

7. 設定読み込み（Settings）

```python
from kabusys.config import settings
print(settings.duckdb_path, settings.jquants_refresh_token)
```

---

## よく使うユーティリティと挙動の注意点

- 自動 .env 読み込み:
  - パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env/.env.local を自動読み込みします。
  - テストや CI で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI 呼び出し:
  - news_nlp と regime_detector は OpenAI の JSON mode を想定しています。API エラーやパース失敗時はフォールバック（0.0 等）を行い、例外を上げない設計です（一部は ValueError を投げる）。

- J-Quants クライアント:
  - レート制限とリトライを内蔵。401 の場合はリフレッシュトークンから ID トークンを自動で取得して再試行します。
  - 取得データは fetched_at を UTC ISO 形式で保存します（Look-ahead の追跡に有用）。

- DuckDB バージョン依存:
  - 一部の executemany や list バインドに関して DuckDB のバージョンによる挙動差異を考慮した実装があります。DuckDB は推奨バージョンで使用してください。

---

## ディレクトリ構成（主要ファイル）

（src ルート: パッケージ名 kabusys）

- src/kabusys/
  - __init__.py
  - config.py                          # 環境変数管理（.env 自動読み込み、Settings）
  - ai/
    - __init__.py
    - news_nlp.py                       # ニュースセンチメント -> ai_scores 書き込み
    - regime_detector.py                # 市場レジーム判定 -> market_regime 書き込み
  - data/
    - __init__.py
    - jquants_client.py                 # J-Quants API client & DuckDB 保存
    - pipeline.py                       # ETL パイプライン（run_daily_etl 他）
    - etl.py                            # ETLResult の再エクスポート
    - news_collector.py                 # RSS 収集（SSRF 対策、前処理）
    - quality.py                        # データ品質チェック
    - stats.py                          # zscore_normalize 等
    - calendar_management.py            # 市場カレンダー管理、営業日判定
    - audit.py                          # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py                # モメンタム/ボラティリティ/バリュー
    - feature_exploration.py            # forward returns, IC, summary
  - (その他)                             # strategy / execution / monitoring パッケージ想定

---

## 環境変数・設定一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY (ai 機能使用時)

任意（デフォルトあり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

---

## 開発・運用上の注意

- データ品質チェック（data.quality）を ETL 後に実行し、発見された問題はログや監査に記録して調査してください。ETL は可能な限り続行する設計です。
- OpenAI/API の呼び出しはレート制限・コストが発生します。運用時はバッチ頻度・バッチサイズ（news_nlp の _BATCH_SIZE 等）を調整してください。
- 監査ログ（audit）は削除しない前提で設計されています。バックアップ戦略・保持方針を策定してください。
- 本ライブラリは実際の発注ロジック（execution/発注接続等）と分離して設計されています。実際の売買を行う場合は安全なテスト（paper_trading）と重複防止（order_request_id の冪等性）を必ず行ってください。

---

## ライセンス / 貢献

（このサンプル README ではライセンス記載は省略していますが、実プロジェクトでは LICENSE を明記してください。Pull request / issue の運用ルールやコントリビュート手順を追記してください。）

---

必要であれば README にサンプル .env.example、より詳しい API リファレンス、実運用時のワークフロー（cron/airflow での ETL スケジュール、監視フロー、Slack 通知の使い方等）を追加できます。どの情報を優先して追加しますか？