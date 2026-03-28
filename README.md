# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants API からのデータ取得、DuckDB ベースの ETL、ニュースの NLP スコアリング（OpenAI）、研究用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などの機能を提供します。

主な設計方針は「ルックアヘッドバイアス対策」「冪等性」「フェイルセーフ（API障害時は部分的にフォールバック）」「外部サービス呼び出しのリトライ/レート制御」です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（サンプル）
- 環境変数（.env 例）
- ディレクトリ構成
- 備考 / 実装上のポイント

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・特徴量生成・AI ニュース評価・市場レジーム判定・監査ログの初期化や管理を行うモジュール群を含む Python パッケージです。バックテストや自動売買システムの基盤（Data Platform / Research / Strategy / Execution / Monitoring）として利用することを想定しています。

- データ取得元: J-Quants API（株価・財務・市場カレンダーなど）
- DB: DuckDB（ローカルファイル or :memory:）
- AI: OpenAI（gpt-4o-mini を JSON mode で利用）
- ニュース収集: RSS → raw_news テーブルへ保存（SSRF対策、トラッキング除去等）

---

## 機能一覧

主要機能（モジュール別）
- kabusys.config
  - .env 自動ロード（プロジェクトルート検出）
  - 環境変数ラッパ（settings オブジェクト）
- kabusys.data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch/save、トークン自動リフレッシュ、レート制御、リトライ）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS 取得・正規化・SSRF 対策・raw_news 保存ロジック）
  - 品質チェック（欠損、重複、スパイク、日付整合性）
  - 監査ログ初期化（監査テーブル DDL / インデックス / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄別に集約して LLM でセンチメント算出 → ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定 → market_regime に保存
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

主要な設計特徴
- DuckDB ベースで SQL と Python を併用
- ETL は差分取得＋バックフィルで後出し修正を吸収
- OpenAI 呼び出しは JSON モードを使いレスポンス検証・リトライあり
- ニュース収集は URL 正規化・トラッキング除去・SSRF 対策・サイズ上限などを実装
- 監査ログは冪等・トレーサビリティ重視（UUID ベースの階層）

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意
2. 依存パッケージをインストール（例: pip）
   - 必須例:
     - duckdb
     - openai
     - defusedxml
   - 開発環境や packaging に応じて requirements.txt / pyproject.toml を使ってください。

例（ローカル開発としてソースを install する場合）:
```bash
pip install -e .[dev]
# または最低限
pip install duckdb openai defusedxml
```

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env/.env.local を置くと自動ロードされます。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB ファイルや監査 DB の初期化（必要に応じて）
   - 監査 DB を新規で作成する例:
     - Python REPL:
       from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/audit.duckdb")
   - 既存の DuckDB 接続を用いて監査スキーマのみ初期化する:
       from kabusys.data.audit import init_audit_schema
       import duckdb
       conn = duckdb.connect("data/kabusys.duckdb")
       init_audit_schema(conn, transactional=True)

注意: DuckDB のテーブル群（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime など）は ETL または schema 初期化用の別モジュールで作成する想定です（このコードベースの一部は保存関数・ETL を含みますが、全スキーマ定義が別にある可能性があります）。監査スキーマは data.audit で定義済みです。

---

## 使い方（サンプル）

- 設定の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

- DuckDB 接続作成
```python
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（J-Quants の id_token は settings.jquants_refresh_token を使用して内部で取得されます）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を指定可
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI API キーは env.OPENAI_API_KEY または api_key 引数）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20))
print("scored", count)
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
count = score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（Research）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

- 監査 DB 初期化（別 DB を使う例）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/monitoring_audit.duckdb")
# これで監査用テーブルが作成されます
```

---

## 環境変数（.env 例）

主要な環境変数（settings で参照されるもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（任意, デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

.example (.env.example) の例:
```env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- プロジェクトルートを自動検出して .env/.env.local をロードします（CWD に依存しません）。
- テストや明示的な制御が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。

---

## ディレクトリ構成（主要ファイル）

パッケージは src/kabusys 以下に実装されています。主要なファイルを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                       # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    # ニュース NLP スコアリング（score_news）
    - regime_detector.py             # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
    - jquants_client.py              # J-Quants API クライアント + 保存関数
    - news_collector.py              # RSS 収集・前処理
    - calendar_management.py         # 市場カレンダー管理・判定関数
    - quality.py                     # データ品質チェック
    - stats.py                       # zscore_normalize 等
    - audit.py                       # 監査ログ DDL / init_audit_db
    - etl.py                         # ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py             # ファクター計算（momentum/value/volatility）
    - feature_exploration.py         # forward returns / IC / summary / rank

（上記以外に strategy / execution / monitoring モジュールが __all__ に含まれる可能性がありますが、本リストは提供ソースの中核部分を示しています。）

---

## 備考 / 実装上のポイント

- ルックアヘッドバイアス回避:
  - 多くの関数で date 引数を明示的に受け取り、内部で datetime.today() を参照しない設計になっています（バックテストでの誤用を防止）。
- 冪等性:
  - J-Quants から取得したデータは save_* 関数で ON CONFLICT DO UPDATE を用いて冪等保存されます。
- エラー耐性:
  - OpenAI 呼び出し・外部 API 呼び出しはリトライやフォールバック（ゼロスコアなど）でフェイルセーフ化されています。
- セキュリティ:
  - RSS 収集は SSRF 対策（ホスト検査、リダイレクト検査）、XML の defusedxml 使用、最大受信サイズ制限などを行っています。
- ロギング:
  - 各モジュールは logging を利用。LOG_LEVEL 環境変数で制御できます。

---

何か特定の機能の README 部分を詳しく（例: ETL 実行例、ニュース収集バッチ、監査テーブルのスキーマ詳細、OpenAI の応答形式の期待仕様など）追記したい場合は教えてください。必要に応じて使用例や運用手順（cron や Airflow に組み込む例）も追加します。