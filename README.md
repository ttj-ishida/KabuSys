# KabuSys

日本株向けのデータ基盤・研究・自動売買ユーティリティ群（KabuSys）のリポジトリ用 README。  
このドキュメントはコードベース（src/kabusys 以下）に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、特徴量（ファクター）計算、ニュースの NLP スコアリング（OpenAI）、
市場レジーム判定、監査ログ（order/signal/execution）などを一貫して扱うためのライブラリ群です。  
主に以下用途を想定しています。

- J-Quants からの株価・財務・カレンダーの差分 ETL
- raw_news の収集・前処理と LLM によるニュースセンチメント解析
- ファクター計算・リサーチ用ユーティリティ（forward returns / IC / summary 等）
- 市場レジーム判定（ETF + マクロニュースを組み合わせたスコアリング）
- 監査用 DuckDB スキーマ初期化（トレース可能な発注・約定ログ）
- データ品質チェック（欠損・重複・スパイク・日付整合性）

設計上、ルックアヘッドバイアスを避ける実装や、API 呼び出しのリトライ・バックオフ、冪等保存（ON CONFLICT）などを重視しています。

---

## 主な機能一覧

- データ ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）: rate limit / token refresh / pagination 対応
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合の検出
- ニュース取得・前処理（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、記事 ID の冪等保存設計
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI を使った銘柄別ニュースセンチメント取得（JSON mode）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離 + マクロニュースセンチメントを合成して日次レジーム判定
- 研究用ユーティリティ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター算出
  - forward returns / IC / factor summary / rank（スピアマン）
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions の DDL と初期化ヘルパー
- 設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート判定）と Settings API

---

## セットアップ手順

以下は開発環境でライブラリを使うための最低限の手順例です。

1. Python 環境準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージのインストール（本リポジトリに requirements.txt がないため代表的なパッケージを例示）
   - pip install duckdb openai defusedxml
   - またはパッケージを editable install:
     - pip install -e .

   必要に応じて logging, urllib 等は標準ライブラリを利用しています。

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` および `.env.local` を置けます。
   - 自動読み込み順序: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（最低限設定が必須なもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID : Slack 通知先チャンネルID（必須）
   - OPENAI_API_KEY : OpenAI 呼び出しに必要（news_nlp / regime_detector を使う場合）
   - DUCKDB_PATH : デフォルト "data/kabusys.duckdb"
   - SQLITE_PATH : デフォルト "data/monitoring.db"

   ※ .env の書式は shell スタイル（export を許容、クォートとコメント処理あり）です。

4. DuckDB ファイル領域
   - settings.duckdb_path に示されるパスの親ディレクトリが必要です。`kabusys.data.audit.init_audit_db()` は親ディレクトリを自動作成します。

---

## 使い方（簡単なコード例）

以下は主要ユーティリティの呼び出し例です。実行前に必要な環境変数（特に API キー）のセットを忘れないでください。

- DuckDB 接続の作成（設定ファイルのパスを利用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（例: 本日分を取得）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ETL の個別ジョブを実行する（株価だけ等）
```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched} saved={saved}")
```

- ニュースセンチメント（OpenAI）でスコアを付ける
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境にセットされている前提
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written scores:", n_written)
```

- 市場レジーム判定（OpenAI を使う）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

# OPENAI_API_KEY が環境にセットされている前提
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

# ファイルを指定（":memory:" でインメモリ DB）
audit_conn = init_audit_db("data/audit.duckdb")
# すぐに使用可能な audit_conn が返る
```

- ニュース RSS を取得する（news_collector.fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- 研究用関数の利用例（ファクター計算）
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

---

## 重要な実装上の注意点

- ルックアヘッドバイアス対策:
  - 多くのモジュール（news_nlp, regime_detector, pipeline 等）は内部で date.today() を不用意に参照せず、呼び出し側が target_date を渡す設計です。バックテスト時は必ず適切な target_date を明示してください。
- 環境変数の自動ロード:
  - kabusys.config はプロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を自動読み込みします。テスト時等に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し:
  - news_nlp / regime_detector は OpenAI の JSON mode を利用しています。API のレート制御・リトライロジックを実装していますが、API キーやコストには注意してください。
- J-Quants API:
  - リフレッシュトークン（JQUANTS_REFRESH_TOKEN）から id_token を取得しページネーション対応でデータを取得します。120 req/min のレート制約を守る実装（RateLimiter）を含みます。
- DuckDB の executemany の挙動:
  - DuckDB の古いバージョンでは executemany に空リストを渡せないため、実装側で空チェックを入れています。

---

## ディレクトリ構成

リポジトリ（src/kabusys）内の主なファイル・モジュールは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                    - 環境変数 / Settings 管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                - ニュースセンチメント（OpenAI）
    - regime_detector.py        - 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py    - 市場カレンダー管理 / 営業日判定
    - etl.py                    - etl の公開インターフェース（ETLResult）
    - pipeline.py               - ETL パイプライン（run_daily_etl 等）
    - stats.py                  - zscore_normalize 等の統計ユーティリティ
    - quality.py                - データ品質チェック
    - audit.py                  - 監査ログスキーマ初期化（signal / order / execution）
    - jquants_client.py         - J-Quants API クライアント（fetch/save）
    - news_collector.py         - RSS 収集 / 前処理 / 保存ユーティリティ
  - research/
    - __init__.py
    - factor_research.py        - momentum/value/volatility 等
    - feature_exploration.py    - forward returns / IC / summary / rank

---

## よくある利用フロー（例）

1. `.env` に J-Quants / OpenAI / Slack 等の秘匿情報をセット
2. DuckDB 接続を作成
3. run_daily_etl をスケジューラで夜間実行（カレンダー先読み + 差分 ETL）
4. news_nlp（score_news）を ETL 後や別バッチで実行して ai_scores を更新
5. research モジュールで特徴量を算出 → シグナル生成 → 監査ログ（signal_events/order_requests）に記録
6. 実際の発注は execution 層（本リポジトリに含まれる発注ラッパーを使用）で処理（本コードには発注の外部 API の抽象が含まれます）

---

## 貢献・テスト

- 現在この README はコード解析に基づいたドキュメントです。ユニットテスト・CI（pytest 等）が存在する場合はリポジトリ内のテストディレクトリを参照してください（本説明ではテストファイルは含めていません）。
- 外部 API を扱うコードが多いので、ユニットテストでは openai / urllib / jquants クライアントのモック化を推奨します。

---

必要であれば、README に以下を追加できます。
- pyproject.toml / requirements.txt に基づくインストール手順
- 各テーブルスキーマ（DDL）の抜粋（audit などは既にコード内に DDL 記載）
- 具体的な実行例（cron / systemd / Docker Compose）や運用注意（コスト管理、Secrets 管理）など

ほかに追記したい項目があれば教えてください。