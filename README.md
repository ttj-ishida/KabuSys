# KabuSys

日本株向けのデータプラットフォーム & 自動売買基盤のライブラリです。  
DuckDB を中心としたデータ ETL、ニュース NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などのユーティリティを含みます。

## 主な特徴
- J-Quants API との差分 ETL（株価・財務・マーケットカレンダー）
- DuckDB に対する冪等保存（ON CONFLICT / upsert 実装）
- ニュースの収集・前処理（RSS）と LLM を用いた銘柄別センチメント分析
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM スコアを合成）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → execution の完全トレーサビリティ）
- 環境変数自動ロード機能（プロジェクトルートの .env / .env.local を自動読み込み）

---

## 要求環境（推奨）
- Python 3.10+
- 必要な主要パッケージ（例）:
  - duckdb
  - openai (v1 SDK を想定)
  - defusedxml
  - その他標準ライブラリ（urllib, json, datetime, typing 等）

例（pip）:
pip install duckdb openai defusedxml

（プロジェクトを配布する際は pyproject.toml / requirements.txt を参照してください）

---

## 環境変数 / 設定
このライブラリは環境変数 / .env ファイルから設定を読み込みます。自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。自動ロードを無効化するには環境変数を設定します:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / 既定値:
- KABUSYS_ENV — development / paper_trading / live（default: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（default: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 で自動ロード無効化
- DUCKDB_PATH — DuckDB のデフォルトパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（default: data/monitoring.db）
- OPENAI_API_KEY — OpenAI API キー（news/LLM 関数で使用）

例 (.env):
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## セットアップ手順（ローカル開発向け）
1. Python 3.10+ を用意する
2. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml
   （必要に応じてテスト用に pytest などを追加）
4. プロジェクトルートに .env を作成して必要な環境変数を設定
5. DuckDB ファイルや出力ディレクトリを作成（必要なら）
   mkdir -p data

（パッケージ化されている場合は pip install -e . でインストールしてください）

---

## 使い方（代表的な関数 / 例）

以下は典型的な呼び出し例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() の戻り値）を受け取ります。

- 日次 ETL を走らせる（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（前日15:00〜当日08:30 JST ウィンドウ）のスコアを生成
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 を用いた MA200 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
```

- 監査ログ用 DB 初期化（監査専用 DB ファイルを作る）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルに対する INSERT/SELECT を行えます
```

- ファクター計算（研究用）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意点:
- OpenAI を使う関数は api_key 引数を受け取ります。渡さない場合は環境変数 OPENAI_API_KEY を参照します。未設定だと ValueError が発生します。
- ETL / API 周りはレート制限やリトライを実装していますが、API キーやネットワークエラーで処理がスキップされる場合があります（フェイルセーフ設計）。

---

## 主要モジュールと機能一覧

- kabusys.config
  - 環境変数の自動ロード・検証（.env / .env.local の読み込み、必須キーチェック）
- kabusys.data
  - jquants_client: J-Quants API の取得・保存ロジック（fetch / save）
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - news_collector: RSS 取得、前処理、raw_news への保存ロジック
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマの初期化 / init_audit_db
  - stats: zscore_normalize 等
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM で銘柄別にスコアリング
  - regime_detector.score_regime: 市場レジームを判定し market_regime テーブルへ保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## ディレクトリ構成（主要ファイル）
（この README は提供されたコードベースに基づく構成概要です）

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
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
    - (その他の研究用モジュール)
  - research/__init__.py
  - data/__init__.py

各モジュールは DuckDB 接続を受け取って処理する設計で、バックテストや本番処理の両方で使えるようにルックアヘッドバイアス対策（date 引数ベース）等が施されています。

---

## 開発・テストのヒント
- 自動 env 読み込みはプロジェクトルートの .env / .env.local を探します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自前で環境を制御すると便利です。
- OpenAI 呼び出しやネットワーク関数は各モジュールで内部呼び出しをラップしているため、unittest.mock.patch で差し替えやすくなっています（例: kabusys.ai.news_nlp._call_openai_api のモック）。
- DuckDB による executemany は空リストを渡すとエラー（バージョン依存）になるため、コード中で事前に空チェックが行われています。テスト時も空リスト扱い注意。

---

もし README に追記したい「具体的な CLI」「サンプル .env.example」「テーブルスキーマ」などがあれば、必要に応じて追加で作成します。