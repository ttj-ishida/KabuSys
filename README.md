# KabuSys

KabuSys は日本株向けのデータ基盤・研究・AI評価・監査ログ・ETL を備えた自動売買システムのライブラリ群です。本リポジトリは以下の主要機能を提供します。

- J-Quants API 経由の株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いた ETL パイプライン（差分取得・冪等保存・品質チェック）
- ニュースの収集・前処理（RSS）と OpenAI を用いた記事/銘柄別センチメントスコアリング
- 市場レジーム判定（ETF の MA 乖離 + マクロニュース LLM センチメント）
- 研究用ファクター計算（モメンタム/ボラティリティ/バリュー 等）と統計ユーティリティ
- 監査ログテーブル（signal → order_request → execution のトレーサビリティ）
- 設定管理（.env / 環境変数の読み込み・検証）

設計方針として、バックテストでのルックアヘッドバイアスを防ぐ処理、外部 API 呼び出し失敗時のフェイルセーフ、DuckDB を中心とした冪等保存・トランザクション制御が採用されています。

---

## 主な機能一覧

- data:
  - jquants_client: J-Quants API ラッパー（取得・保存・認証、ページネーション、レート制御、リトライ）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS からニュース収集と前処理（SSRF 対策・サイズ制限）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: JPX カレンダー管理（営業日判定、next/prev_trading_day 等）
  - audit: 監査ログ（シグナル／発注／約定テーブルのDDLと初期化）
  - stats: 汎用統計ユーティリティ（zscore 正規化等）
- ai:
  - news_nlp.score_news: ニュースを OpenAI で解析し ai_scores を作成
  - regime_detector.score_regime: ETF MA とマクロニュース LLM を合成して market_regime を生成
- research:
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config:
  - Settings クラス: 環境変数読み込み（自動でプロジェクトルートの .env/.env.local を読み込み）

---

## 依存関係（主なもの）

推奨インストールパッケージ（最低限）:
- Python 3.9+
- duckdb
- openai
- defusedxml

実際の環境では requirements.txt を用意している想定ですが、存在しない場合は上記パッケージを pip でインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトする。

2. 仮想環境を作成して依存をインストールする（上記参照）。

3. 環境変数を設定する
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` および（ローカル専用設定なら）`.env.local` を配置すると、自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途）。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を利用する場合）
   - KABU_API_PASSWORD: kabuステーション用パスワード（必要に応じて）
   - その他（任意/デフォルトあり）:
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — default: INFO

例: `.env`（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要 API の例）

以下はライブラリを直接インポートして使う例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す接続）を引数として受け取ります。

- ETL（日次パイプライン）の実行:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（OpenAI）で ai_scores を生成:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written {n_written} scores")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB の初期化（専用 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブル群が作成されます
```

- 研究用ファクター計算:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records: list[dict] の形式
```

- 設定の取得（環境変数アクセス）:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env)
```

注意点:
- score_news / score_regime は OpenAI の API を利用します。API 呼び出しの失敗時はフェイルセーフでスコア 0.0 にフォールバックする（ログ出力）実装になっていますが、API キーが未設定だと ValueError を返します。
- ETL や保存処理は冪等設計（ON CONFLICT DO UPDATE 等）なので、再実行による上書きが安全に行われます。

---

## 監査ログ（audit モジュール）

- init_audit_schema(conn, transactional=False): 既存の DuckDB 接続に監査テーブルを追加します。
- init_audit_db(db_path): 監査用の DuckDB を作成して接続を返します（タイムゾーンを UTC に設定）。

監査テーブルは signal_events, order_requests, executions を含み、order_request_id / broker_execution_id 等でトレーサビリティを保証します。

---

## 自動 .env 読み込み動作

- config.py はパッケージ読込時に自動でプロジェクトルート（.git または pyproject.toml を探索）を探し、`.env` → `.env.local` の順で読み込みます。
- OS 環境変数が優先され、`.env.local` は上書きフラグ（override=True）で読み込まれます。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用に便利）。

.env ファイルのパースはシェル風の形式（export も可、クォートやコメント処理あり）に対応しています。

---

## ディレクトリ構成

主要ファイル／モジュールの一覧（src/kabusys 以下の抜粋）:

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
    - pipeline.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - ai/__init__.py

（上記はコードベースで提供されている主なモジュールを列挙しています。実際のリポジトリではさらにテストや CLI、ドキュメント等が含まれる可能性があります。）

---

## 実運用上の注意・設計ポリシー

- Look-ahead bias を防ぐため、各 AI/研究モジュールは内部で datetime.today()/date.today() を参照せず、必ず target_date を外部から与えるインタフェースを採用しています。
- J-Quants クライアントはレート制限（120 req/min）・トークン自動更新・リトライを備えています。
- ニュース収集には SSRF 対策、XML 攻撃対策（defusedxml）、受信サイズ制限が組み込まれています。
- OpenAI 呼び出しはリトライ・パースエラーのハンドリングを行い、失敗時はスコアを 0.0 にフォールバックします（例外を上げない設計）。
- DuckDB に対する書き込みは可能な限り冪等（ON CONFLICT）で行い、ETL はトランザクションを活用して整合性を保ちます。

---

## テスト & 開発者向けメモ

- OpenAI API 呼び出し部分は内部関数（_kabusys.ai.news_nlp._call_openai_api 等）をモックしやすい設計になっています（unittest.mock.patch を想定）。
- `.env` の自動読み込みはプロジェクトルート探索に基づくため、パッケージ配布後も安定して動作するよう作られています。
- DuckDB のバージョン依存（executemany に空リストを与えられない等）に配慮した実装が随所にあります。

---

README の内容は実装の概要に基づく要約です。より詳細な API 仕様や動作保証、追加の CLI / 管理スクリプトが必要であれば、対象モジュールごとに README を分割して補完できます。必要であればサンプルの .env.example や requirements.txt の草案も作成します。どの情報を優先して追加しますか？