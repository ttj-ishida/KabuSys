# KabuSys

日本株向けの自動売買/データ基盤ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI）、市場レジーム判定、監査ログ（約定トレース）など、売買システムの中核機能を提供します。

主な目的は「バックテスト／研究用データパイプライン」と「自動売買／監視実行環境」を支える共通ライブラリの提供です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（設定項目）
- 使い方（簡単なコード例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです：

- J-Quants API を用いた株価・財務・カレンダー等の差分取得（ETL）
- DuckDB を使った社内データベースへの冪等保存
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集・NLP による銘柄ごとのセンチメント算出（OpenAI）
- ETF とマクロセンチメントを合わせた市場レジーム判定
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）
- 市場カレンダー（JPX）ユーティリティ（営業日判定等）

設計の特徴として、ルックアヘッドバイアス回避（日時の明示的受け渡し）、API の堅牢なリトライ、DuckDB への冪等保存、外部通信の安全対策（RSS の SSRF 対策等）が考慮されています。

---

## 機能一覧

- data/
  - jquants_client: J-Quants API 呼び出し（取得・保存・認証・レートリミット・リトライ）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）と ETL 結果型 ETLResult
  - quality: データ品質チェック（missing_data, spike, duplicates, date_consistency）
  - calendar_management: 営業日判定 / next/prev_trading_day / calendar_update_job
  - news_collector: RSS 収集（URL 正規化、SSRF/サイズ制限、前処理、冪等保存）
  - audit: 監査ログ用スキーマ作成・初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize（ファクター正規化）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）で評価し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime に記録
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility（各種ファクター）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config.py
  - 環境変数の自動読み込み（.env, .env.local）とアプリ設定アクセス（settings）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントで `X | Y` を使用）
- DuckDB を利用するためネイティブ環境で動くこと

1. リポジトリをクローン
   - git clone .../kabusys.git

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e .  または
   - pip install duckdb openai defusedxml

   （requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動でロードされます（ただしテスト時に無効化するなら環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数は下の「環境変数」節を参照してください。

5. DuckDB データベース作成
   - デフォルトは data/kabusys.duckdb（settings.duckdb_path）を使います。必要ならフォルダを作成してください（init_audit_db が自動で親ディレクトリを作成します）。

---

## 環境変数（主な設定項目）

config.Settings 経由で参照されます。自動読み込みはプロジェクトルートの .env / .env.local を読みます（OS 環境変数が優先）。

必須:
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD
  - kabuステーション API のパスワード
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL  (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH        (default: data/kabusys.duckdb)
- SQLITE_PATH        (default: data/monitoring.db)
- PID_FILE_PATH      (default: data/execution.pid)
- CPU_THRESHOLD_PCT  (default: 90.0)
- MEMORY_THRESHOLD_PCT (default: 85.0)
- DISK_THRESHOLD_PCT (default: 90.0)
- KABUSYS_ENV        (development | paper_trading | live) (default: development)
- LOG_LEVEL          (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)

OpenAI:
- OPENAI_API_KEY を設定するか、ai モジュールの関数に api_key 引数を渡します（score_news / score_regime は api_key 引数を受け付けます）。

テスト用:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化できます。

---

## 使い方（簡単なコード例）

以下は最小の使用例です。実行環境で適切に環境変数を設定してから利用してください。

- ETL（日次パイプライン）を実行する例

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄ごとの AI スコア）を実行する例

```python
from datetime import date
import os
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数に設定するか api_key に文字列を渡す
n = score_news(conn, target_date=date(2026, 3, 20), api_key=os.environ.get("OPENAI_API_KEY"))
print(f"scored {n} symbols")
```

- 市場レジーム判定を実行する例

```python
from datetime import date
import os
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=os.environ.get("OPENAI_API_KEY"))
```

- 監査ログ DB を初期化する例

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成されます
```

- J-Quants API の直接操作（例: トークン取得 / 銘柄リスト取得）

```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を利用
quotes = fetch_daily_quotes(date_from=..., date_to=..., id_token=token)
```

注意点:
- AI 関連（score_news, score_regime）は OpenAI の API を使用します。API 呼び出しはコスト・レート制限に注意してください。
- 各関数のドキュメントには「Look-ahead バイアス回避」のため日付を引数で渡す方針が書かれています。内部で date.today() や datetime.today() を参照しないよう設計されています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

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
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/  (モニタリング関連モジュールが想定されています)
  - strategy/    (戦略関連モジュールが想定されています)
  - execution/   (約定実行関連モジュールが想定されています)

各モジュールはドキュメント文字列やログを通じて設計方針・フォールバック動作が明記されているため、内部実装を参照すると具体的な挙動（例: ETL のバックフィル方式、API のリトライ仕様、ニュースの時間ウィンドウ定義など）が確認できます。

---

## 補足 / 運用上の注意

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テスト環境等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に対する executemany の挙動（空リストの扱い）に配慮した実装になっていますが、使用する DuckDB バージョンの差異に注意してください。
- news_collector では SSRF 対策、受信サイズ制限、XML パース時の安全ライブラリ（defusedxml）利用などの安全対策が組み込まれています。
- OpenAI 呼び出しはレスポンスのバリデーション・冗長パース対策・リトライを行っていますが、API ポリシー変更により追加対応が必要になる場合があります。
- 本リポジトリは研究・運用支援ライブラリ群として設計されており、本番運用時はリスク管理・注文出力部分（kabu API 連携）の追加実装や監視・アラート設定を併せて整備してください。

---

何か特定のモジュール（例: ETL の詳細な実行手順、news_collector の RSS 登録方法、監査スキーマの拡張方法など）について README を拡張したい場合は、どのトピックを追加すべきか教えてください。