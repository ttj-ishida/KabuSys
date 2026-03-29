# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ集です。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログなど、運用に必要な主要コンポーネントをモジュール化して提供します。

---

## 目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（サンプル）
- 環境変数一覧（.env）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は以下の機能群を持つ Python パッケージです。

- J-Quants API と連携して株価・財務・マーケットカレンダーを取得・保存する ETL パイプライン
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去、重複回避）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄単位）とマクロセンチメント評価
- ETF（1321）の 200 日移動平均乖離とマクロセンチメントを合成して市場レジーム（bull/neutral/bear）を判定
- 研究用ファクター計算（Momentum / Value / Volatility 等）、特徴量探索ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 発注〜約定までの監査ログ（監査テーブルの初期化・管理）
- DuckDB を中心としたローカル DB に保存（冪等挿入、fetched_at の記録で look-ahead を防止）

設計上の方針として、バックテストやモデル研究での「ルックアヘッドバイアス」を意識しており、内部実装は可能な限りターゲット日付より先のデータを参照しないようになっています。また、外部 API 呼び出しはリトライ・バックオフ等の堅牢化が組み込まれています。

---

## 主な機能一覧
- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS fetch_rss、前処理、DB保存）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news: 銘柄別センチメントを ai_scores に書き込み）
  - レジーム判定（score_regime: ma200 とマクロセンチメントの合成）
- research/
  - Factor 計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索・IC 計算（calc_forward_returns / calc_ic / factor_summary / rank）
- config.py
  - 環境変数読み込みヘルパー（.env 自動ロード・必須チェック・設定オブジェクト）

---

## セットアップ手順（開発環境）
以下は一般的な手順です。プロジェクトルートには `pyproject.toml` 等がある想定です。

1. ソースを取得
   - git clone など

2. Python 仮想環境を作成・有効化（例）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - requirements.txt / pyproject.toml があればそれに従ってください。
   - 開発時は最低限以下が必要になります（サンプル）:
     - duckdb
     - openai (openai v1 SDK を想定)
     - defusedxml
   - 例:
     - pip install -r requirements.txt
     - あるいは pip install duckdb openai defusedxml

4. パッケージをインストール（開発モード）
   - pip install -e .

5. .env を用意
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（※自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須変数は下記の「環境変数一覧」を参照してください。

6. データディレクトリ作成（必要に応じて）
   - デフォルトの DuckDB パスは `data/kabusys.duckdb`（設定で変更可）。必要なら `mkdir -p data`。

---

## 簡単な使い方サンプル

以下はインタラクティブに KabuSys の主要機能を使う簡単な例です。Python REPL やスクリプトから実行できます。

1) DuckDB 接続を作成して日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを算出（OpenAI API キーが必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("scored:", count)
```

3) 市場レジーム判定（ETF 1321 の MA + マクロセンチメント）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

5) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# または既存接続にテーブルを追加する
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn_existing, transactional=True)
```

---

## 環境変数（.env）一覧
下記はコード内で参照される主要な環境変数です。プロジェクトルートの `.env` / `.env.local` に設定してください（自動ロードあり。既存の OS 環境変数は上書き保護されます）。

必須:
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD
  - kabuステーション API を使う場合のパスワード
- SLACK_BOT_TOKEN
  - Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID
  - Slack 通知送信先チャンネル ID

任意（デフォルトを持つ／挙動を制御）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) (default: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)
- OPENAI_API_KEY
  - OpenAI を使うモジュール（news_nlp, regime_detector）で使用。各関数でも明示的に渡せます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 値を `1` にすると自動的な .env の読み込みを無効化（テスト用）

簡易 .env 例（機密情報は適切に管理してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- パーサはシェルスタイルの `export KEY=val`、シングル/ダブルクォート、コメント行をサポートしています。
- 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を読み込みます。

---

## 実装上の注意点（運用／開発者向け）
- OpenAI 呼び出しはリトライとバックオフを組み込んでいます。APIキーは環境変数か関数引数で与えてください。
- J-Quants クライアントは ID トークンを自動取得・キャッシュし、401 が返された場合はトークンを自動リフレッシュします。レートリミットはモジュール内で厳守されています（120 req/min）。
- DuckDB への保存は基本的に冪等（ON CONFLICT / DO UPDATE）で実装されています。
- データ品質チェックは Fail-Fast ではなく、全チェック結果を収集して呼び出し元が判断する設計です。
- ルックアヘッドバイアス防止のため、各モジュールは target_date を明示的に受け取り、内部で date.today() を不用意に参照しないよう設計されています。

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - (その他: jquants_client の補助関数等)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

各モジュールの役割は上記「主な機能一覧」を参照してください。必要に応じて module-level docstring をご確認ください（コード内に詳細な設計メモがあります）。

---

## よくある質問 / トラブルシュート
- .env が読み込まれない
  - プロジェクトルート検出は __file__ から親階層を探索して `.git` または `pyproject.toml` を探します。CI 等で別の CWD を使用している場合、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し手動で環境変数を読み込んでください。
- OpenAI 呼び出しが失敗する（429 等）
  - モジュールは自動リトライを行いますが、連続失敗時はスコアをフェイルセーフに 0.0 にフォールバックします。API レートやキーの有効性を確認してください。
- ETL 実行でデータが書き込まれない
  - run_daily_etl の戻り値 ETLResult に fetched / saved / quality_issues / errors が含まれます。エラーメッセージを確認してください。

---

以上です。必要であれば README に運用例（cron / Airflow タスク定義）、CI 設定、より具体的な .env.example ファイル、または API 仕様の抜粋（SQL スキーマ）を追加で作成します。どの情報を優先して追加しますか？