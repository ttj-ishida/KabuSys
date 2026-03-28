# KabuSys

日本株向け自動売買／データプラットフォームのライブラリ群です。  
主にデータの ETL、データ品質チェック、ニュース収集・NLP による銘柄センチメント算出、マーケットレジーム判定、リサーチ用ファクター計算、監査（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の量的運用基盤を構成するモジュール群です。主な役割は次の通りです。

- J-Quants API からの市場データ（株価・財務・カレンダー等）の差分取得と DuckDB への永続化（ETL）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（RSS）と前処理、銘柄紐付け
- OpenAI を用いたニュースセンチメント（銘柄別 / マクロ）算出（JSON Mode を利用）
- ETF を用いた市場レジーム判定（MA200 とマクロニュースの混合）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- 監査ログ（signal → order → execution）のスキーマ定義と初期化ユーティリティ

設計上、バックテストでのルックアヘッドバイアスを避けるために「現在時刻」を直接参照しない実装方針が取られています。また、外部 API 呼び出しは再試行・フォールバックを備えた堅牢な実装になっています。

---

## 主な機能一覧

- データETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得＋保存、バックフィル対応）
  - J-Quants クライアント（fetch / save 系関数、認証トークン管理、レート制御、リトライ）
- データ品質
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（品質チェックの集約）
- ニュース処理
  - RSS フィード取得（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - preprocess_text / 記事ID生成 / raw_news 保存ロジック
- AI（OpenAI）連携
  - news_nlp.score_news：銘柄ごとのニュースセンチメントを ai_scores に書き込み（バッチ・JSON Mode）
  - regime_detector.score_regime：ETF 1321 の MA200 乖離とマクロニュースの LLM 評価を合成して market_regime に保存
  - リトライ／フェイルセーフ設計（API 失敗時はスコアを 0 にフォールバックなど）
- リサーチ
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / zscore_normalize 等の統計ユーティリティ
- 監査（Audit）
  - init_audit_schema / init_audit_db：監査用テーブル群（signal_events, order_requests, executions）とインデックスを初期化
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（J-Quants からの差分取得と保存）

---

## 要件（推奨）

- Python 3.10 以上（型注釈で | を使用しているため）
- 必要なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ（urllib, json, datetime, logging 等）

pip でのインストール例（プロジェクトに requirements.txt がある場合はそちらを使用してください）:
```bash
python -m pip install duckdb openai defusedxml
```

（パッケージとして配布している場合は）
```bash
pip install -e .
```

---

## 環境変数（主なもの）

KabuSys は .env ファイルまたは環境変数から設定を読み込みます（自動ロードはプロジェクトルートに .git または pyproject.toml がある場合に行われます）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD     : kabu ステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN       : Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV (development / paper_trading / live) — default: development
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL) — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. Python と依存パッケージをインストール
   - Python 3.10+
   - pip で必要なライブラリをインストール（上記参照）

2. リポジトリをクローン / パッケージをインストール
   - 開発中:
     ```
     git clone <repo>
     cd <repo>
     pip install -e .
     ```
   - あるいは requirements.txt / pyproject.toml に従ってインストール

3. 環境変数設定
   - プロジェクトルートに .env（上記の必須変数を含む）を作成するか、OS 環境変数で設定
   - 自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データベース初期化（監査ログ等）
   - 監査ログ用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     conn.close()
     ```
   - ETL 用の DuckDB は settings.duckdb_path（デフォルト data/kabusys.duckdb）を使用できます

---

## 使い方（抜粋）

以下は代表的なユースケースの簡単な利用例です。実運用ではログ設定やエラーハンドリングを適切に行ってください。

1) 日次 ETL 実行（株価・財務・カレンダー・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

2) ニュースセンチメント算出（特定日）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {written}")
conn.close()
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
conn.close()
```

4) 監査スキーマ初期化（既存 DB に対して）
```python
import duckdb
from kabusys.data.audit import init_audit_schema

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
conn.close()
```

5) ファクター計算（リサーチ）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records))
conn.close()
```

注意点:
- OpenAI コールは JSON Mode を使用して厳密な JSON を期待しています。テストでは内部の _call_openai_api をモックできます（unittest.mock.patch）。
- API キーは score_news / score_regime の api_key 引数で直接渡すこともできます（関数は api_key 引数を優先します）。

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
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
  - etl.py (alias)
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
- research/ ...（その他リサーチユーティリティ）

各モジュールの責務:
- kabusys/config.py: 環境変数と設定管理（.env 自動ロード機能含む）
- kabusys/data/jquants_client.py: J-Quants API クライアント（fetch/save）
- kabusys/data/pipeline.py: ETL パイプラインと run_daily_etl
- kabusys/data/news_collector.py: RSS 取得と前処理
- kabusys/ai/news_nlp.py: 銘柄別ニュース NLP スコア算出
- kabusys/ai/regime_detector.py: 市場レジーム判定
- kabusys/research/*: ファクター計算・統計解析

---

## テスト／デバッグのヒント

- OpenAI API 呼び出しはネットワークに依存するため、ユニットテスト時は内包された _call_openai_api を patch（モック）してください。
  例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api") 等。
- .env の自動読み込みはプロジェクトルート検出に依存します。テスト環境で不要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の接続は軽量なので、テストでは ":memory:" を使うことでインメモリ DB を利用できます（init_audit_db でも対応）。

---

## 運用上の注意

- 実運用（live）環境では KABUSYS_ENV=live を設定し、ログレベルや通知を調整してください。
- 発注ロジック（kabuAPI 等）へ接続する場合は、テスト時に paper_trading モードを使用し、誤発注を防いでください。
- J-Quants や OpenAI のレート／課金仕様に注意し、バッチサイズや呼び出し頻度を適切に設定してください。

---

必要に応じて README の具体的なコマンド例や .env.example のテンプレートを追加します。どの部分をより詳しく記載したいか教えてください。