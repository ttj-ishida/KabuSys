# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants / kabu API クライアント等を含み、バックテスト・研究・実運用のための共通基盤機能を提供します。

主な目的
- J-Quants からの株価・財務・カレンダー取得と DuckDB への ETL
- RSS ニュース収集と LLM（OpenAI）による銘柄センチメント評価
- 市場レジーム判定（MA200 と マクロニュースの合成）
- ファクター計算・特徴量探索（research 用ユーティリティ）
- 監査ログ（signal → order → execution の完全トレーサビリティ）

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（fetch / save: 日足、財務、上場銘柄、カレンダー）
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
  - ニュース収集（RSS、前処理、raw_news への冪等保存）
- NLP / AI
  - news_nlp.score_news: ニュースから銘柄ごとの ai_score を算出して ai_scores に格納
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成し market_regime を更新
- 研究用ユーティリティ
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank
  - 統計ユーティリティ: zscore_normalize
- データ品質管理
  - 欠損・スパイク・重複・日付不整合検出（quality モジュール）
- 監査ログ
  - 監査テーブル定義・初期化（init_audit_schema / init_audit_db）
- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）と Settings API（kabusys.config.settings）

---

## 要件

- Python 3.10+
- 必要なライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- （標準ライブラリの urllib 等を使用しており、requests は不要）

プロジェクト配布時に requirements.txt / pyproject.toml を用意する想定ですが、上記ライブラリを事前にインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを入手）:
   - git clone ... / pip install -e .（パッケージ化されている場合）

2. 仮想環境を作成して依存をインストール:
   - python 3.10+ を使用
   - pip install duckdb openai defusedxml

3. 環境変数の設定:
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を作成します。
   - 自動ロードは OS 環境変数 > .env.local > .env の優先順位で行われます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（Settings で参照されるもの）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL 用）
  - KABU_API_PASSWORD: kabu API パスワード（注文送信等）
- 任意 / デフォルトあり
  - OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector）
  - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
  - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH: デフォルト "data/monitoring.db"
  - PID_FILE_PATH: デフォルト "data/execution.pid"
  - KILL_FLAG_PATH: デフォルト "data/kill.flag"
  - KILL_FLAG_CLEAR_ON_START: "1" で起動時に kill flag をクリア
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
  - KABUSYS_ENV: "development" / "paper_trading" / "live"（既定 "development"）
  - LOG_LEVEL: "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

`.env.example` を参照して `.env` を作成することを推奨します（README 内で参照する旨がコードにも書かれています）。

---

## 使い方（サンプル）

以下のコードは一例です。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）を設定してください。

- DuckDB 接続を作り日次 ETL を回す:
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニューススコアリングを実行（指定日）:
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", written)
```

- 市場レジーム判定を実行:
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB の初期化:
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにアクセス可能
```

- ファクター計算例（研究用）:
```
from datetime import date
import duckdb
from kabusys.research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄の辞書リスト
```

---

## 自動 .env ロードの挙動

- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）を探索し、`.env` と `.env.local` をロードします。
- 読み込み優先順位（高い順）:
  1. OS 環境変数
  2. .env.local（上書き）
  3. .env（既存値を上書きしない）
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- .env のパースはシェル風の `export KEY=VAL`, クォート、インラインコメント等に対応しています。

---

## ディレクトリ構成（主なファイル）

（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 他）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS 収集・前処理
    - calendar_management.py — 市場カレンダー管理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py     — momentum / value / volatility
    - feature_exploration.py — forward returns, IC, summary, rank
  - ai、data、research などのモジュールが相互に利用しますが、LLM API 呼び出し等はリトライ・フォールバックを考慮して設計されています。

---

## 運用上の注意点

- Look-ahead バイアス防止: 多くの関数が内部で datetime.today() を直接参照しないように設計されています。バックテストでは明示的に target_date を渡すことを推奨します。
- OpenAI API 呼び出し:
  - API キーは OPENAI_API_KEY（引数経由でも可）
  - レスポンス検証・リトライを行うが、API エラー時は安全側（スコア=0 等）で継続する設計です
- J-Quants API:
  - トークンリフレッシュ・レートリミット遵守・再試行ロジックを実装済み
- DuckDB の executemany で空リストを渡すとエラーになるバージョンがあるため、空チェックを行ってから実行しています
- ニュース収集の SSRF 対策・XML パース防御（defusedxml）等のセキュリティ対策を実装しています

---

## 貢献 / テスト（簡易）

- 開発環境を整え、ユニットテストやモックを使ったテストを作成してください。
- 環境依存部分（外部 API 呼び出し）はモックしてテスト可能です（コード中に差し替えしやすい設計あり）。

---

必要があれば README に以下を追加できます：
- requirements.txt / pyproject.toml のサンプル
- .env.example の雛形
- 具体的な CLI スクリプト例（cron / systemd 用）
- サンプル DB スキーマ（CREATE TABLE 文の抜粋）
ご希望があれば追記します。