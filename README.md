# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL、ニュースNLP（LLMを用いたセンチメント）、市場レジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などの機能を提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 必要ライブラリ
- セットアップ手順
- 環境変数 (.env)
- 使い方（主要なユースケースの例）
- ディレクトリ構成（主要ファイルの説明）
- 注意事項

---

## プロジェクト概要
KabuSys は以下を目的とした Python モジュール群です。
- J-Quants（日本株データ）からの差分 ETL（株価・財務・カレンダー）
- RSS ベースのニュース収集と銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（銘柄別 / マクロ）
- マーケットレジーム判定（ETF + マクロセンチメントの重み合成）
- 研究用途のファクター計算・統計ユーティリティ
- 発注〜約定に至る監査ログ（DuckDB ベース）管理
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計の重点:
- ルックアヘッドバイアス回避（date 引数ベースで処理）
- DuckDB を中心としたオンディスク DB（ローカル解析・監査）
- API 呼び出しはリトライ・レートリミット考慮で安全に実行

---

## 機能一覧
主な機能（モジュール別）
- kabusys.config
  - .env / 環境変数の自動ロード、設定取得（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API の取得／保存ユーティリティ（差分取得、ページネーション、トークンリフレッシュ、保存は冪等）
  - pipeline: run_daily_etl などの ETL パイプライン
  - calendar_management: 営業日判定、カレンダー更新ジョブ
  - news_collector: RSS 取得・正規化・raw_news への保存（SSRF 防御・XML 安全パース）
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - audit: 発注〜約定の監査スキーマ初期化 (init_audit_schema / init_audit_db)
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを生成して ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロセンチメントを合成して market_regime に記録
- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration: 将来リターン算出、IC、summary 等

---

## 前提条件 / 必要ライブラリ
- Python >= 3.10
- 必須ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, logging, datetime 等）

インストール例（最低限）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```
プロジェクト配布に requirements.txt / pyproject.toml があればそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージをインストール
   - 開発環境であれば editable install:
     ```
     pip install -e .
     ```
     （プロジェクトに pyproject.toml / setup.cfg がある場合）

2. 必要な Python パッケージをインストール（上記参照）

3. 環境変数設定 (.env)
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に自動で `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL用）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注等がある場合）
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     LOG_LEVEL=INFO
     KABUSYS_ENV=development
     ```

4. DuckDB ファイルの準備
   - デフォルトは `data/kabusys.duckdb`。settings.duckdb_path で変更可。
   - 監査用 DB を分けたい場合は `kabusys.data.audit.init_audit_db(path)` を使用して初期化できます。

---

## 使い方（主要な例）

以下はライブラリを直接呼ぶ最低限のサンプルです。実際はエントリポイントスクリプトやジョブスケジューラ（cron / systemd / Airflow 等）から呼び出します。

1) ETL（日次 ETL を実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（銘柄別）を生成して DB に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を明示的に渡すか、OPENAI_API_KEY を環境変数で設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

3) 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメント合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログスキーマ / DB の初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# :memory: も可（テスト用）
conn = init_audit_db(settings.sqlite_path)  # もしくは settings.duckdb_path
```

5) 市場カレンダー更新ジョブ（J-Quants から差分取得）
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

---

## 環境変数一覧（主要）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（news_nlp/regime_detector）
- KABU_API_PASSWORD (必須 for kabu API): kabuステーション用パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite/DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 開発環境 (development|paper_trading|live)
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

注意: settings オブジェクト（kabusys.config.settings）から上述の値を参照できます。必須の値が不足している場合は ValueError が発生します。

---

## ディレクトリ構成（主要ファイルの説明）
（パッケージは src/kabusys 以下に配置されている想定）

- src/kabusys/__init__.py
  - パッケージ初期化、バージョン情報

- src/kabusys/config.py
  - .env 自動読み込み、settings オブジェクト（環境変数から設定値を取得）

- src/kabusys/ai/
  - news_nlp.py : ニュースを LLM でスコアリングし ai_scores に保存する機能
  - regime_detector.py : ETF（1321）MA200 乖離とマクロセンチメントを合成して market_regime を作成

- src/kabusys/data/
  - jquants_client.py : J-Quants API クライアント（取得 + DuckDB への冪等保存）
  - pipeline.py : ETL パイプライン（run_daily_etl 等）
  - calendar_management.py : JPX カレンダー管理 / 営業日ユーティリティ
  - news_collector.py : RSS 取得・前処理・保存（SSRF 対策, XML 安全パーサ）
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py : 監査ログ（signal_events, order_requests, executions）スキーマ初期化
  - stats.py : 汎用統計ユーティリティ（zscore_normalize など）
  - etl.py : ETLResult の再エクスポート

- src/kabusys/research/
  - factor_research.py : モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration.py : 将来リターン・IC・統計サマリー等

- src/kabusys/ai/news_nlp.py / regime_detector.py / その他
  - OpenAI (gpt-4o-mini) の JSON Mode を使った安全な呼び出し、リトライ、レスポンスバリデーションを実装

---

## 注意事項 / 運用上のポイント
- OpenAI API 使用時はレスポンスの JSON バリデーションに失敗した場合はフェイルセーフ（0.0 にフォールバック）する実装です。API キャンセルや課金に注意してください。
- J-Quants API にはレート制限があるため、jquants_client はレート制御とリトライを行います。
- ETL や LLM 呼び出しは実行コスト（API 料金・時間）が発生します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD などを利用して環境を分離してください。
- DuckDB 向けの executemany 空リスト等の挙動に注意（コード内でガードされています）。
- 日時の扱いは Look-ahead バイアス防止のため、内部で date.today() を直接参照しない設計の箇所が多くあります（target_date を明示的に渡すことが推奨されます）。

---

もし README に含めたい具体的なセットアップ手順（pipenv/poetry/コンテナ化）、実行スクリプト例（systemd / cron / Docker Compose）、またはサンプル .env.example を追加で希望される場合は教えてください。必要に応じて実運用向けの推奨設定や監視（pid/kill flag / resource thresholds）についても追記できます。