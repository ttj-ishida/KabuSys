# KabuSys

日本株向け自動売買／データプラットフォームライブラリ KabuSys（v0.1.0 相当）の README です。本リポジトリはデータの ETL、ニュース NLP、ファクター計算、監査ログ、JPX カレンダー管理、J-Quants / kabu ステーション連携、そして簡易な市場レジーム判定までを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の研究・自動売買システム向けに設計された Python モジュール群です。主な目的は次のとおりです。

- J-Quants API からの株価・財務・カレンダー等データの差分取得（ETL）
- RSS ニュースの収集と OpenAI を用いた銘柄単位の NLP センチメントスコアリング
- ETF（1321）200日移動平均とマクロニュースを融合した市場レジーム判定
- 研究（factor / feature）用ユーティリティ（モメンタム・ボラティリティ・バリュー等）
- データ品質チェック、監査ログ（シグナル→発注→約定のトレーサビリティ）
- DuckDB を中心としたローカルデータ格納

設計上の留意点：
- ルックアヘッドバイアスを避けるため、内部処理では date.today()/datetime.today() に依存しない実装方針が採られています（関数に target_date を明示的に渡す）。
- OpenAI（LLM）呼び出しにはリトライやフェイルセーフが組み込まれています。API キー未設定時は例外を投げます。
- ETL / 保存処理は冪等（idempotent）に設計されています（ON CONFLICT DO UPDATE 等）。

---

## 主な機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須/推奨設定のプロパティアクセス（kabusys.config.settings）
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl: カレンダー・株価・財務の差分取得と品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別 ETL
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch / save 系関数（daily_quotes, financial_statements, market_calendar 等）
  - レート制限、リトライ、トークン自動リフレッシュ対応
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、SSRF 対策、raw_news への冪等保存想定
- ニュース NLP（kabusys.ai.news_nlp）
  - gpt-4o-mini を用いた銘柄別センチメント scoring（ai_scores への書込）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニューススコアを合成して regime を判定
- 研究用ファクター（kabusys.research）
  - calc_momentum, calc_volatility, calc_value 等
  - forward returns / IC（Information Coefficient）計算、統計サマリー
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合などのチェックを実行
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を含む監査スキーマ初期化ユーティリティ

---

## セットアップ手順

以下は開発用の簡易手順です。実運用ではプロジェクトに付随する pyproject.toml / requirements.txt を参照してください。

1. Python 仮想環境を作成・有効化（例: Python 3.9+ 推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml

   追加で必要なパッケージがあればプロジェクトの要件ファイルを参照してください。

3. パッケージを editable インストール（リポジトリルートで）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます。
   - 自動読み込みを無効にするには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

必須（または重要）な環境変数例：
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須、ETL・API 呼び出し用）
- OPENAI_API_KEY: OpenAI API キー（AI スコアリング / レジーム判定で必須）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（発注連携時）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite ファイル（デフォルト: data/monitoring.db）
- その他監視／ログ設定（PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT 等）

.env の例（プロジェクトルートに .env を作成）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下はライブラリを使ってよく使う処理を行う簡単な例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続の作成例:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイル名は settings.duckdb_path と合わせても良い
```

- 日次 ETL を実行する:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を明示的に渡す（None なら今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（ai_scores へ書き込む）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n = score_news(conn, target_date=date(2026,3,20))
print(f"scored {n} codes")
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key=None)  # api_key を None にすると OPENAI_API_KEY を参照
```

- 監査ログ DB 初期化（監査専用 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

- ファクター計算（研究用）:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄の辞書リスト
```

注意点:
- OpenAI 呼び出しは実際に外部 API を叩きます（料金・レートに注意）。
- 各関数は target_date を外部から渡す設計になっており、ルックアヘッドバイアス防止が意識されています。
- ETL や保存処理は DuckDB スキーマが事前に作成されていることを前提にしています（スキーマ初期化ロジックは別途用意する想定）。

---

## ディレクトリ構成（ハイレベル）

以下は提供されているモジュールの主なファイルと役割です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの LLM スコアリング（ai_scores 書込）
    - regime_detector.py     — ETF MA + マクロニュースで market_regime を判定
  - data/
    - __init__.py
    - calendar_management.py — JPX カレンダー管理・営業日判定
    - etl.py                 — ETL インターフェース再エクスポート
    - pipeline.py            — 日次 ETL パイプラインの実装（run_daily_etl 等）
    - stats.py               — z-score 正規化などの統計ユーティリティ
    - quality.py             — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py               — 監査ログ用スキーマ初期化（signal/order/execution）
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - news_collector.py      — RSS 収集・前処理・保存ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility の計算
    - feature_exploration.py — forward returns, IC, factor summary, rank

---

## 運用上の注意 / 補足

- 設定読み込み:
  - .env / .env.local はプロジェクトルート（.git または pyproject.toml があるディレクトリ）から自動検出されます。
  - テスト時など自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI:
  - news_nlp / regime_detector は OpenAI の Chat API（gpt-4o-mini 想定）を使用します。API レスポンスは JSON モードでパースされますが、失敗時はフェイルセーフ（0.0 等）にフォールバックします。
- J-Quants:
  - API レート制限、トークン刷新（401 時）や 429/5xx のリトライ処理が組み込まれています。
- DuckDB:
  - 既存のスキーマを前提とする関数が多くあります。初期スキーマや監査スキーマは必要に応じて init_audit_schema / init_audit_db を使用して作成してください。
- セキュリティ:
  - news_collector は SSRF 対策、受信サイズ上限、XML パースの安全ライブラリ（defusedxml）を使用しています。

---

必要であれば、README に含める .env.example、requirements.txt、あるいは具体的な DB スキーマ初期化スクリプトのサンプルを作成します。どの部分をより詳しく記述しましょうか？