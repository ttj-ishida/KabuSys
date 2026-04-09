# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J‑Quants / kabuステーション / OpenAI（LLM）等を組み合わせ、データ取得（ETL）・品質チェック・ニュースNLP・市場レジーム判定・リサーチ用ファクター計算・監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のアルゴリズム取引／リサーチ基盤向けのモジュール群をまとめたパッケージです。主に以下の役割を持ちます。

- J‑Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL
- raw_news の収集・前処理・銘柄紐付け（RSS ベース）
- ニュースを LLM（OpenAI）でスコアリングし ai_scores に保存する処理
- ETF（1321）を中心とした移動平均乖離とマクロニュースから市場レジーム（bull/neutral/bear）判定
- ファクター計算（Momentum / Volatility / Value 等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用テーブル初期化ユーティリティ
- 設定管理（.env 自動ロード、環境変数管理）

設計上の特徴として「ルックアヘッドバイアスを避ける」「フェイルセーフ（API失敗時はスキップ or 中立で継続）」「DuckDB を用いた冪等保存」「外部 API 呼び出しはリトライ・レート制御付き」などを重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J‑Quants クライアント（fetch / save 系関数、トークンリフレッシュ、レート制御）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS 取得、前処理、SSRF対策、raw_news 保存）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - 監査ログ（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news）：銘柄ごとに LLM でセンチメントを算出し ai_scores に書き込み
  - レジーム判定（score_regime）：ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して market_regime に保存
- research/
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - .env 自動読み込み（プロジェクトルート判定 .git または pyproject.toml）
  - Settings オブジェクト経由の設定取得（JQUANTS_REFRESH_TOKEN 等）
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 必要条件

- Python 3.10 以上（型ヒントで `|` を使用しているため）
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 本パッケージを編集モードでインストールする場合
pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

---

## 環境変数 / .env

プロジェクトルート（.git または pyproject.toml のある階層）に `.env` / `.env.local` を置くと自動で読み込まれます（テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須): J‑Quants のリフレッシュトークン
- OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: paper_trading 用の注文模擬挙動（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）

簡易的な `.env` の例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

注意: Settings クラスは必須の環境変数が未設定だと ValueError を送出します。

---

## セットアップ手順（推奨）

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   # もし pyproject.toml / requirements.txt があればそれを利用
   ```

4. プロジェクトルートに `.env` を作成（上記の例を参照）

5. DuckDB ファイルやデータディレクトリを作成
   ```bash
   mkdir -p data
   ```

6. 監査用 DB の初期化（任意）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()
   ```

---

## 使い方（主要な API 例）

- DuckDB 接続準備（ETL / スコアリングで共通）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行（市場カレンダー取得 → 株価・財務の差分取得 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア計算（ai_scores に書き込み）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("written codes:", n_written)
```

- 市場レジーム判定（market_regime に書き込み）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
volatility = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

- 監査スキーマの初期化
```python
from kabusys.data.audit import init_audit_schema
# 既存の duckdb 接続に対して実行
init_audit_schema(conn, transactional=True)
```

ログレベルなどは環境変数 `LOG_LEVEL` や Settings を通して制御します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主なファイルと役割の一覧です（抜粋）。

- src/kabusys/__init__.py
- src/kabusys/config.py
  - Settings, .env 自動ロード
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py         — ニュース NLP スコアリング（score_news）
  - regime_detector.py  — 市場レジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py   — J‑Quants API クライアント（fetch / save / get_id_token）
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py              — ETLResult 再エクスポート
  - news_collector.py   — RSS 取得・前処理・保存
  - calendar_management.py — 市場カレンダー管理
  - quality.py          — データ品質チェック
  - stats.py            — 統計ユーティリティ（zscore_normalize）
  - audit.py            — 監査ログスキーマ初期化 / init_audit_db
- src/kabusys/research/
  - __init__.py
  - factor_research.py  — Momentum / Volatility / Value の計算
  - feature_exploration.py — forward returns, IC, summary, rank

（上記以外にも strategy / execution / monitoring 等のサブパッケージが想定されるエクスポート箇所があります）

---

## 設計上の注意点 / ベストプラクティス

- ルックアヘッドバイアス防止:
  - 各処理は target_date を明示的に受け取り、datetime.today() を直接参照しない実装方針です。バックテストでは必ず過去の target_date を渡してください。
- API キー:
  - OpenAI / J‑Quants の API キーは外部から注入（引数）または環境変数にて提供してください。テスト時は関数をモック化できます（モジュール内の _call_openai_api 等を patch）。
- ETL の耐障害性:
  - 各ステップは独立して例外ハンドリングされ、1ステップ失敗でも他ステップを継続します。ETLResult にエラー／品質問題が記録されます。
- DuckDB への書き込みは冪等化されており、ON CONFLICT / executemany を多用しています。

---

## 付録: よく使う関数一覧（抜粋）

- ETL / data
  - run_daily_etl(conn, target_date, id_token=None, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - get_last_price_date(conn), get_last_financial_date(conn)
- AI
  - score_news(conn, target_date, api_key=None)
  - score_regime(conn, target_date, api_key=None)
- Research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons=[1,5,21])
  - calc_ic(factors, forwards, factor_col, return_col)
- Data quality
  - run_all_checks(conn, target_date=None, reference_date=None)
- Audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

ご不明点や README に追加したい利用シナリオ（例: CI 向けセットアップ、Docker イメージ化、サンプル ETL ジョブスケジューラ）などがあれば教えてください。必要に応じて具体的なコマンドやサンプルスクリプトを追記します。