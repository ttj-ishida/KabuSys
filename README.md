# KabuSys

日本株向け自動売買／データ基盤ライブラリ KabuSys の README。  
このリポジトリはデータ ETL、ニュース NLP（LLM）、ファクター計算、監査ログなどを備えた日本株の研究・自動売買基盤向けモジュール群を含みます。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API を使った株価・財務・カレンダー等の差分 ETL と DuckDB への保存
- RSS ベースのニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini など）を使ったニュースセンチメント解析（銘柄別 ai_score / マクロセンチメント）
- 市場レジーム判定（ETF MA 乖離 + マクロセンチメントの合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）および特徴量探索ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴：
- ルックアヘッドバイアスに配慮（内部で date.today()/datetime.now() を安易に参照しない実装方針）
- DuckDB を中心としたローカルデータベース設計（ETL は冪等性を重視）
- 外部 API 呼び出しにはリトライ／バックオフとフェイルセーフ（失敗時はスキップ等）を導入
- OpenAI 呼び出しは JSON Mode を活用し厳格なレスポンス検証を実施

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch_ / save_ 系）
  - カレンダー管理（営業日判定、next/prev_trading_day）
  - ニュース収集（RSS → raw_news 保存）
  - データ品質チェック（missing / spike / duplicates / date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema, init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュースセンチメント（score_news）
  - マーケットレジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数管理（Settings クラス）
  - プロジェクトルートの .env / .env.local 自動ロード（無効化可能）

---

## 前提 / 必要環境

- Python 3.10 以上（型注釈の `|` 構文を使用しているため）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他、標準ライブラリ以外の小さな依存がある場合あり。requirements.txt を用意している場合はそれを使用してください）

推奨開発環境（例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# 必要なパッケージをインストール（プロジェクトに requirements.txt があればそれを使う）
pip install duckdb openai defusedxml
# ローカル開発用に editable install（パッケージ化されている場合）
pip install -e .
```

---

## 環境変数 / 設定

プロジェクトはルートの .env / .env.local を自動読み込みします（検出条件: .git または pyproject.toml が存在するディレクトリがプロジェクトルートと見なされます）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（Settings から参照されるもの）:

- JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime 実行時に必要）
- KABU_API_PASSWORD : kabu ステーション（発注）用パスワード
- KABU_API_BASE_URL : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID
- DUCKDB_PATH : デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 実行環境 (development|paper_trading|live) （デフォルト: development）
- LOG_LEVEL : ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

.env のサンプル（例）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- 自動ロード時の優先順位: OS 環境変数 > .env.local > .env（.env.local は .env を上書き）
- .env ファイルのパースは多数のシェルスタイルをサポート（export 句、クォート、コメント処理 等）

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成と有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存ライブラリのインストール
   - requirements.txt があれば:
     ```bash
     pip install -r requirements.txt
     ```
   - なければ主要パッケージを個別に:
     ```bash
     pip install duckdb openai defusedxml
     pip install -e .  # パッケージとしてインストール可能なら
     ```

4. プロジェクトルートに .env を作成して必要な環境変数を設定

5. DuckDB データベースの初期化（必要なスキーマがある場合は別途 schema 初期化ロジックを用意してください）
   - 監査ログ専用 DB を作る例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（主な利用例）

以下は Python REPL / スクリプトから利用する簡単な例です。適宜ログ設定や例外処理を追加してください。

- ETL（日次 ETL を実行）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（score_news）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に置くか、api_key 引数にキーを渡す
written = score_news(conn, target_date=date(2026,3,20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（score_regime）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査 DB 初期化（監査スキーマ作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を利用して監査ログに書き込む処理を実装
```

- 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は dict のリスト。さらに zscore_normalize などを適用可能
```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。API キーの設定（環境変数 OPENAI_API_KEY または api_key 引数）が必須です。
- J-Quants API を利用する ETL 実行には JQUANTS_REFRESH_TOKEN の設定が必要です。
- run_daily_etl 等は内部で ETL の各ステップを個別に try/except しているため、一部失敗しても処理は継続します。戻り値の ETLResult で詳細を確認してください。

---

## ディレクトリ構成

代表的なファイル／モジュール構成（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュース NLP（score_news）
    - regime_detector.py             -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント（fetch / save）
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - etl.py                         -- ETLResult 再エクスポート
    - calendar_management.py         -- マーケットカレンダー管理
    - stats.py                       -- zscore_normalize 等
    - quality.py                     -- 品質チェック（missing/spike/duplicates/date_consistency）
    - news_collector.py              -- RSS 取得 / 前処理
    - audit.py                       -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py             -- calc_momentum, calc_value, calc_volatility
    - feature_exploration.py         -- calc_forward_returns, calc_ic, factor_summary, rank

（上記以外に execution / monitoring / strategy 等のサブパッケージが想定されますが、現行コードベースの主要モジュールは上記です。）

---

## 開発者向けメモ / 実装上の注意

- .env 自動読み込み
  - プロジェクトルートが .git または pyproject.toml により特定される場合、ルートの .env を自動で読み込みます。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化可能。
- DuckDB との互換性
  - 一部の場所で executemany に空リストを渡すとエラーになる DuckDB バージョンを想定し、空チェックを行っています。
- 外部 API のリトライ
  - J-Quants / OpenAI 呼び出しはそれぞれリトライ・バックオフ・エラーハンドリングを実装しています。API の失敗は最終的にスキップ（または 0 値にフォールバック）する設計が多く含まれています。
- ルックアヘッドバイアス回避
  - バックテストや研究用途で誤った未来情報を使わないように、関数は target_date を明示的に受け取り内部で現在日時を参照しない実装方針です。

---

## サポート / 貢献

- バグ報告や改善提案は Issues にてお願いします。  
- 開発に貢献する場合は PR を送り、ユニットテストと簡潔な説明を添えてください。

---

README の内容はコードベースの現状に基づく概略です。実運用に入れる前に、環境変数・API キー・DB スキーマ・権限周りを十分に確認してください。