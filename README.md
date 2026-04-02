# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
J-Quants / kabuステーション / OpenAI 等を組み合わせて、データ取得・品質管理・ニュースの NLP スコアリング・市場レジーム判定・監査ログ管理までを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群をモジュール化して提供する Python ライブラリです。

- データ ETL（J-Quants からの株価・財務・市場カレンダー取得）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と NLP による銘柄別センチメントスコア化（OpenAI）
- 市場レジーム判定（ETF の 200 日移動平均乖離 + マクロニュースセンチメント）
- 研究用途のファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログスキーマ（信号 → 発注 → 約定のトレーサビリティ）
- kabuステーション（ブローカ）や Slack 連携のための設定管理

設計方針として「バックテストでのルックアヘッドバイアス回避」「DuckDB を中心とした軽量な永続化」「API 呼び出しの堅牢性（再試行・バックオフ）」を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（冪等保存）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
  - 品質チェック: check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - ニュース収集: RSS 取得と前処理、raw_news への保存
  - 監査ログスキーマ初期化: init_audit_schema / init_audit_db
  - 汎用統計: zscore_normalize
- ai
  - ニュース NLP スコアリング: score_news（OpenAI を利用）
  - 市場レジーム判定: score_regime（ETF 1321 の MA200 とマクロニュースを融合）
- research
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank
- 設定管理: 環境変数の読み込み・検証（kabusys.config.Settings）

---

## 要件（推奨）

- Python 3.10+
- 主要依存パッケージ（抜粋）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API / OpenAI / RSS 取得先
- J-Quants リフレッシュトークン、OpenAI API キー、kabuステーションのパスワード等の環境変数設定が必要

（実際の requirements.txt / pyproject.toml はプロジェクトルート参照）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. パッケージと依存をインストールします（プロジェクトに合わせて）。
   - 例（開発用）:
     - pip install -e .
     - pip install duckdb openai defusedxml

   ※ 実際には pyproject.toml / requirements.txt を使ってインストールしてください。

3. 環境変数を設定します。プロジェクトルートに `.env` を置くことで自動読み込みされます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。`.env.local` は `.env` を上書きします。

4. 必要なら DuckDB 用のディレクトリを作成します（デフォルトは data/ 配下）。

---

## 必須 / 推奨の環境変数

kabusys.config.Settings で参照される主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD
  - kabuステーション API に接続する際のパスワード
- SLACK_BOT_TOKEN
  - Slack 通知用 BOT トークン
- SLACK_CHANNEL_ID
  - Slack チャネル ID

OpenAI:
- OPENAI_API_KEY
  - OpenAI を利用する ai.score_news / regime_detector で使用（関数呼び出し時に api_key を渡すことも可能）

オプション（デフォルトあり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live) — 設定ミスは例外になる
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

.env のパースは shell の export 形式やクォート・コメントをある程度サポートします。

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトからの利用例です。

- ETL（デイリー ETL）を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースをスコアリングして ai_scores に書き込む:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
print(f"written {n_written} scores")
```

- 市場レジーム判定（market_regime テーブルへ書き込み）:
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
```

- 監査ログ DB を初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブル(signal_events, order_requests, executions) が作成されます
```

- JPX カレンダー差分更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved", saved)
```

注意:
- 上記の多くは外部 API (J-Quants / OpenAI) を呼ぶため、該当 API キー・ネットワーク接続が必要です。
- 関数は Look-ahead バイアスを避けるため内部で date.today() を直接参照しない設計です（target_date を明示的に渡すことを推奨）。

---

## ディレクトリ構成（主要ファイル説明）

（src/kabusys 配下の主要モジュール）

- __init__.py
  - パッケージエントリ。公開サブパッケージを定義。

- config.py
  - 環境変数 / .env の自動読み込みと Settings クラス（J-Quants / kabu / Slack / DB パス等）

- data/
  - jquants_client.py
    - J-Quants API クライアント（取得・保存・認証・レートリミッタ・リトライ）
  - pipeline.py
    - ETL の高レベル制御（run_daily_etl 等）と ETLResult 定義
  - etl.py
    - pipeline から ETLResult を再エクスポート
  - calendar_management.py
    - 市場カレンダー管理・営業日判定・calendar_update_job
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector.py
    - RSS 取得・前処理・SSRF 対策・記事 ID 正規化
  - audit.py
    - 監査ログ（signal_events / order_requests / executions）の DDL と初期化
  - stats.py
    - zscore_normalize 等の統計ユーティリティ

- ai/
  - news_nlp.py
    - 複数銘柄をまとめて OpenAI に投げ、ai_scores テーブルへ保存する処理（JSON Mode, バッチ・リトライ）
  - regime_detector.py
    - ETF (1321) の MA200 とニュースセンチメントを合成して market_regime へ保存

- research/
  - factor_research.py
    - calc_momentum / calc_value / calc_volatility（prices_daily / raw_financials ベース）
  - feature_exploration.py
    - calc_forward_returns / calc_ic / factor_summary / rank
  - __init__.py
    - 研究用 API の集合

---

## 注意点 / 運用上のメモ

- .env 自動読み込み:
  - パッケージインポート時にプロジェクトルート（.git または pyproject.toml を基準）を探索し `.env` / `.env.local` を読み込みます。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。

- API の再試行・バックオフ:
  - J-Quants と OpenAI 呼び出しは再試行と指数バックオフを備えています。429 / 5xx / タイムアウト等に対応。

- Look-ahead バイアス:
  - ファクター計算やニュースウィンドウは target_date に対して過去データのみを参照する設計になっています。バックテストでは target_date を適切に与えてください。

- DuckDB の executemany 空リスト制約:
  - 一部の DuckDB バージョンでは executemany に空リストを渡すと失敗するため、コード内で空チェックを行っています。

---

## 貢献

バグ報告・機能要求は Issue を立ててください。コントリビュートする場合は Pull Request を送ってください。

---

以上が KabuSys の README.md（日本語）です。必要であれば、インストールコマンドや CI / テスト実行手順、具体的な .env.example のテンプレートも追加で作成します。どの情報が必要か教えてください。