# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants）、ニュース収集・NLP（OpenAI）、ファクター計算・リサーチ、監査ログ／約定トレーサビリティなどを含むモジュール群で構成されています。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ
- 使い方（代表的なユースケース）
- 環境変数 / 設定
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けの研究 / 本番運用を想定した下位ライブラリ群です。主な役割は以下です：

- J-Quants API からの株価・財務・カレンダー等の差分ETL（rate-limit / retry考慮）
- RSS によるニュース収集と前処理（SSRF対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別 ai_score）およびマクロセンチメントによる市場レジーム判定
- 監査（signal → order_request → executions）用のテーブル定義・初期化ユーティリティ（DuckDB）
- ファクター計算・特徴量探索・統計ユーティリティ（DuckDBベース）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計方針の特徴：
- ルックアヘッドバイアス防止（関数内で date.today()/datetime.today() を直接参照しない）
- DuckDB を中心としたローカル永続化（ETL / 監査用）
- 冪等性を重視（INSERT ON CONFLICT / UUID-based idempotency）
- 外部API呼び出し時はフェイルセーフ／リトライを実装

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save / get_id_token、レートリミット／リフレッシュ対応）
  - カレンダー管理（営業日判定・next/prev/get_trading_days、calendar_update_job）
  - ニュース収集（RSS パーシング・前処理・SSRF 対策）
  - 品質チェック（missing_data, spike, duplicates, date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None) — 銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime(conn, target_date, api_key=None) — マクロ + ETF MA200 乖離から市場レジーム判定
- research/
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

その他：
- settings 管理（環境変数自動ロード、.env / .env.local の読み込み。無効化フラグあり）

---

## セットアップ

前提：
- Python 3.9+（typing 機能の使用を想定）
- DuckDB が動作する環境
- OpenAI API キー（ニュース NLP / レジーム判定で使用）
- J-Quants のリフレッシュトークン（ETL で使用）

1. リポジトリをクローンしてインストール（開発モード推奨）
   - pip を使う例：
     ```
     pip install -e .
     ```
   - 必要な追加パッケージ（主な外部依存）
     - duckdb
     - openai
     - defusedxml
     - （標準 HTTP ライブラリ urllib を使用、追加は不要）

2. 環境変数を設定
   - プロジェクトルート（pyproject.toml または .git のあるフォルダ）に `.env` / `.env.local` を置くと自動で読み込みます（起動時に settings がロード）。
   - 自動ロードを無効にする場合：
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. 必須の環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注周り）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用（必要な場合）
   - （任意）DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - （任意）SQLITE_PATH（monitoring 用、デフォルト: data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（代表的な例）

すべての操作は DuckDB 接続を渡して行います。以下は Python インタプリタやスクリプトでの利用例です。

1) DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの NLP スコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("scored:", n_written)
```
- api_key を省略すると環境変数 OPENAI_API_KEY を参照します。

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査DB（監査用 DuckDB）初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は監査用 DuckDB 接続（TimeZone は UTC に設定済）
```

5) J-Quants ID トークンを直接取得する
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

6) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄について mom_1m / mom_3m / mom_6m / ma200_dev を含む dict のリスト
```

---

## 環境変数 / 設定の詳細

- 自動ロード:
  - 起動時、プロジェクトルート（.git または pyproject.toml の所在）を探索し `.env` → `.env.local` の順で読み込みます。
  - OS 環境変数が優先され、.env.local は上書き可能。
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Settings（コードで参照可能）
  - settings.jquants_refresh_token → JQUANTS_REFRESH_TOKEN（必須）
  - settings.kabu_api_password → KABU_API_PASSWORD（必須）
  - settings.kabu_api_base_url → KABU_API_BASE_URL（省略時: http://localhost:18080/kabusapi）
  - settings.slack_bot_token / slack_channel_id → SLACK_*（必須）
  - settings.duckdb_path → DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - settings.sqlite_path → SQLITE_PATH（デフォルト data/monitoring.db）
  - settings.env → KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - settings.log_level → LOG_LEVEL（DEBUG/INFO/...）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数/.env 管理
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュース NLP スコアリング（score_news）
    - regime_detector.py           -- マクロ + ETF MA200 合成で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（fetch/save/get_id_token）
    - pipeline.py                  -- ETL pipeline (run_daily_etl, run_prices_etl, ...)
    - etl.py                       -- ETLResult 再エクスポート
    - news_collector.py            -- RSS フェッチ・前処理（SSRF 対応）
    - calendar_management.py       -- 市場カレンダー管理（is_trading_day 等）
    - quality.py                   -- データ品質チェック
    - stats.py                     -- zscore_normalize 等
    - audit.py                     -- 監査スキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py           -- Momentum / Value / Volatility 等
    - feature_exploration.py       -- forward returns / IC / summaries
  - ai/__init__.py
  - research/__init__.py

（README 用の抜粋：各モジュールはソース内に詳細な docstring と設計意図が記述されています）

---

## 運用上の注意 / ベストプラクティス

- OpenAI 呼び出しや外部 API 呼び出しは料金・レート制限が発生します。ローカルテスト時はモックを利用してください（各モジュールではテスト差し替えのために内部呼び出しを抽象化してあります）。
- ETL 実行前に DuckDB のスキーマが揃っていることを確認してください（初回は ETL の一部でテーブルを作成することもありますが、監査テーブルは init_audit_schema で明示的に初期化することを推奨します）。
- 本ライブラリは「データ取得・前処理・分析・監査」にフォーカスしており、実際の売買執行ロジック（kabu への発注フロー）は別モジュールで実装する想定です。発注・実行処理は必ず冪等キー（order_request_id）を用いて行ってください。
- 研究／バックテスト環境では Look-ahead バイアスに注意して、必要な過去のデータのみを DB にロードしてから解析を行ってください。

---

もし README に追加してほしい例（CI のセットアップ、docker-compose、テスト実行方法、具体的なスキーマ定義抜粋など）があれば教えてください。必要に応じて追記します。