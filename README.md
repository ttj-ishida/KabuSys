# KabuSys

日本株向けの自動売買 / データ基盤ユーティリティ群です。  
ETL（J-Quants）・ニュース収集・LLMによるニュースセンチメント・ファクター計算・監査ログなど、トレーディングシステムやリサーチ用途で必要な機能を提供します。

---

## プロジェクト概要

KabuSys は以下の領域をカバーするモジュール群を含むライブラリです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集（raw_news）と前処理
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 / マクロ）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）
- リサーチ用のファクター計算・統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）用スキーマ初期化ユーティリティ
- 環境変数/設定管理（.env 自動読込のサポート）

パッケージは `src/kabusys` 配下に実装されています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API からの取得・DuckDB への冪等保存（レートリミット・リトライ・トークン自動更新）
  - pipeline: 日次 ETL パイプライン（calendar / prices / financials / 品質チェック）
  - news_collector: RSS 取得、前処理、raw_news への保存（SSRF 対策・サイズ制限）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログテーブルの DDL / 初期化
  - calendar_management: JPX カレンダーの管理・営業日判定ユーティリティ
  - stats: 汎用統計ユーティリティ（z-score 正規化）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出（OpenAI）
  - regime_detector.score_regime: マクロセンチメント + ETF MA200 乖離で日次市場レジーム判定
- research/
  - factor_research: Momentum / Value / Volatility 等の定量ファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー等
- config:
  - Settings: 環境変数からの設定読み込み（.env/.env.local の自動読み込みをサポート）

---

## 動作環境 / 前提

- Python 3.10 以上（型注釈で `|` ユニオンを使用）
- 主要依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス:
  - J-Quants API（id token / refresh token が必要）
  - OpenAI API（OPENAI_API_KEY）

必要なパッケージはプロジェクト側で requirements を用意している想定です。最低限のインストール例:

```
python -m pip install duckdb openai defusedxml
```

（プロジェクト配布時に `pip install -e .` や `requirements.txt` を使うことを推奨します）

---

## 環境変数（主なもの）

以下は本システムで参照される主要な環境変数です（.env/.env.local をサポート）。`.env.example` を参考に作成してください。

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（取引実行系で使用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: デフォルトデータベースパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視・プロセス管理用
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視しきい値
- KABUSYS_ENV: environment = development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を起点に `.env` を読み込みます。
- 読み込み順: OS 環境変数（優先）→ .env.local（上書き）→ .env（未設定のみ）
- 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## セットアップ手順（開発環境向け）

1. Python と仮想環境の準備（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージのインストール
   ```
   python -m pip install --upgrade pip
   python -m pip install duckdb openai defusedxml
   ```

   ※ プロジェクト配布時に `setup.py` / `pyproject.toml` があれば `pip install -e .` を推奨。

3. 環境変数を用意する
   - プロジェクトルートに `.env` または `.env.local` を作成し、上記の必須キーを設定。
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxxx
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データディレクトリの作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は典型的な利用例です。DuckDB 接続を作成し、ETL やニューススコアリング、レジーム判定、監査スキーマ初期化などを呼び出します。

- DuckDB に接続して ETL を実行する（日次 ETL）

```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を省略すると今日が対象
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を算出して ai_scores に書き込む

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム（日次）を判定して market_regime に保存する

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化する

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ファイルがなければ親ディレクトリを作成
```

- リサーチ関数（ファクター計算）使用例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
recs = calc_momentum(conn, target_date=date(2026, 3, 20))
# recs は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]
```

注意点:
- LLM を呼ぶ関数（score_news, score_regime）は OPENAI_API_KEY を使用します。引数 api_key を与えて上書きすることも可能です。
- J-Quants API は JQUANTS_REFRESH_TOKEN が必要です。jquants_client.get_id_token() を自動で使用します。
- 関数はルックアヘッドバイアスを避ける設計になっており、内部で date.today() を参照しない／呼び出し日付を明示する等の方針を採用しています。

---

## よく使う API 参照（抜粋）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult class

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None) -> int (書き込み銘柄数)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None) -> int (成功フラグ)

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token(refresh_token=None)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成（主なファイル）

以下は src 配下の主なファイル構成の抜粋です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - etl.py
    - pipeline.py
    - jquants_client.py
    - news_collector.py
    - quality.py
    - stats.py
    - calendar_management.py
    - audit.py
    - (その他)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (パッケージ名が __all__ に含まれる想定)
  - strategy/ (戦略レイヤー: 実装は別途)
  - execution/ (実行／ブローカー連携: 実装は別途)

---

## 注意事項 / ベストプラクティス

- 本ライブラリはデータ取得・解析・監査などのユーティリティを提供します。実際の取引（live）モードで使用する際は、パラメータ・リスク管理コード・ログ監視・運用手順を十分に整備してください。
- OpenAI や J-Quants 呼び出しはレート上限や課金に関わります。API キーの取り扱いに注意してください。
- .env 自動読み込みはプロジェクトルートを基準に行われますが、CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して明示的に環境を制御することを推奨します。
- DuckDB のバージョン差異により挙動が変わる箇所（executemany の空リスト扱い等）があるため、本ライブラリを使用する環境では DuckDB の互換性に注意してください。

---

この README は現行コードベース（src/kabusys 以下）に基づいて作成しています。追加の実行スクリプトや CLI、テスト、デプロイ手順等は別途プロジェクト方針に合わせて整備してください。