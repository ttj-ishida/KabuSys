# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログなどの機能を含みます。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群をまとめたパッケージです。

- J-Quants API からのデータ取得（株価日足・財務・市場カレンダー）
- DuckDB を用いた ETL パイプライン（差分取得・保存・品質チェック）
- ニュース記事収集と LLM によるセンチメント解析（gpt-4o-mini を想定）
- 市場レジーム判定（ETF MA とマクロニュースを複合）
- 研究用のファクター計算・特徴量解析ユーティリティ
- 監査ログ（信号 → 発注 → 約定のトレーサビリティ）スキーマ初期化機能
- 各種設定は環境変数 / .env ファイルで管理（自動ロード機能あり）

パッケージは src/kabusys 以下に実装されています。バッチ処理やバックテスト用に設計された多数のユーティリティを提供します。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API からのデータ取得（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info）
  - DuckDB への冪等保存（save_*）
  - レートリミット・リトライ・トークン自動リフレッシュ対応
- data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl：差分ETL の実行
  - ETLResult：実行結果の集約
- data.quality
  - 欠損・重複・スパイク・日付不整合のチェック（run_all_checks）
- data.news_collector
  - RSS 取得、前処理、raw_news への冪等保存（SSRF 対策・トラッキング除去）
- ai.news_nlp
  - raw_news を集約して LLM に投げ、銘柄ごとの ai_score を ai_scores テーブルへ書き込む（score_news）
- ai.regime_detector
  - ETF（1321）200日 MA 乖離とマクロニュースセンチメントを合成して日次の市場レジームを算出・保存（score_regime）
- research
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量解析・統計）
- data.audit
  - 監査ログ（signal_events / order_requests / executions）スキーマの初期化（init_audit_schema / init_audit_db）
- config
  - .env / 環境変数の自動読み込み（プロジェクトルート基準）と Settings オブジェクト

---

## セットアップ手順

1. Python 環境を用意（推奨: venv / virtualenv）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存パッケージをインストール
   - 必要最低限の依存（例）:
     - duckdb
     - openai
     - defusedxml
   - pip を使う例:
     ```
     pip install duckdb openai defusedxml
     ```
   - プロジェクト用に `requirements.txt` / `pyproject.toml` がある場合はそちらを使用してください。

3. ソースを editable インストール（開発時）:
   ```
   pip install -e .
   ```
   （プロジェクトに pyproject.toml / setup.py があることを想定。ない場合は PYTHONPATH に src を追加する等で利用可能です。）

4. 環境変数設定
   - プロジェクトルートの `.env` / `.env.local` を用意すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロード無効化）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
     - OPENAI_API_KEY (score_news / score_regime 実行時に利用。関数引数でも指定可)
     - KABU_API_PASSWORD (kabu API を使う場合)
     - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) デフォルト: INFO
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用 DB デフォルト: data/monitoring.db)
     - PID_FILE_PATH, KILL_FLAG_PATH, その他監視設定
   - .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。

---

## 使い方（基本例）

以下は典型的な利用例です。全て Python スクリプトから呼び出せます。

- DuckDB に接続して日次 ETL を実行する:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- news_nlp (ニュースセンチメント) を実行して ai_scores に書き込む:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を省略すると OPENAI_API_KEY を使用
print(f"written: {n_written}")
```

- regime_detector (市場レジーム判定) を実行:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用の DuckDB を初期化:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルに書き込み等を行う
```

- 設定（Settings）参照例:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意:
- OpenAI にアクセスする関数は api_key を引数で渡すことができます。引数を省略した場合、環境変数 OPENAI_API_KEY を参照します。
- DuckDB 側のスキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime 等）は事前に用意しておくか、ETL 実行時の初期化ロジックで作成してください（スキーマ定義はプロジェクト内に想定されています）。

---

## 環境変数の自動読み込み

- .env / .env.local がプロジェクトルート（.git または pyproject.toml があるディレクトリ）にあれば、自動で読み込まれます。
- 自動読み込みを無効にする場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で有用）。
- 自動ロードは OS 環境変数より下位（.env.local は .env を上書き）ですが、OS 環境変数は保護され上書きされません。

---

## 開発・デバッグのヒント

- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って .env 読み込みを無効化し、テスト用の環境を注入してください。
- news_nlp / regime_detector の OpenAI 呼び出しは内部でラップされており、ユニットテスト時は該当モジュールの内部関数（例: kabusys.ai.news_nlp._call_openai_api）をモックして外部呼び出しを防げます。
- DuckDB の executemany は空リストを受け付けないバージョンに注意（モジュール側で対応済みの箇所があります）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys
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
  - quality.py
  - news_collector.py
  - calendar_management.py
  - stats.py
  - audit.py
  - (その他 ETL/ユーティリティ)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring / execution / strategy / (パッケージ外のモジュールがあれば同階層で配置)

（上記は本リポジトリに含まれる主要モジュールの概観です。細かいサブモジュールや補助関数は各ファイル内に実装されています。）

---

## 既知の注意点 / 設計方針（要約）

- ルックアヘッドバイアス対策: 多くの関数は date.today() / datetime.today() を直接参照せず、明示的な target_date 引数を受け取ります。バックテストでの利用時は target_date を正しく渡してください。
- 冪等性: J-Quants からの保存処理や ETL の多くは ON CONFLICT DO UPDATE により冪等に設計されています。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時は可能な限りフォールバック（スコア 0.0 など）して処理を続行する設計です。重大エラーはログと ETLResult.errors に記録されます。
- セキュリティ: news_collector は SSRF 対策、XML の安全パース（defusedxml）、受信サイズ制限などを実装しています。

---

ご不明点があれば、使いたい機能（ETL の詳細実行フロー、News/NLP のプロンプト調整、監査スキーマの拡張など）を教えてください。使用例や追加ドキュメントを作成します。