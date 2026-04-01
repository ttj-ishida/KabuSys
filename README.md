# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
価格データのETL、ニュース収集・NLPスコアリング、ファクター計算、監査ログ（オーディット）、市場カレンダー管理、J-Quants API クライアント、LLM を用いた市場レジーム判定等、システム全体の基盤的処理を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の用途を想定したモジュール群をまとめたパッケージです。

- J-Quants API からのデータ取得（株価、財務、カレンダー等）と DuckDB への冪等保存
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS）と前処理、記事 → 銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントスコアリング（銘柄単位）とマクロセンチメントによる市場レジーム判定
- 研究用ファクター計算（Momentum / Volatility / Value 等）と特徴量解析ユーティリティ
- 市場カレンダー管理（営業日判定等）
- 監査ログ（signal → order_request → executions のトレース用テーブル群）
- 環境変数／設定管理（.env 自動読み込み等）

設計上、ルックアヘッドバイアス（将来情報参照）を避ける実装方針が採られており、ETL／スコアリング関数は明示的な target_date を受け取る形になっています。

---

## 主な機能一覧

- 環境設定
  - .env / .env.local 自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数検査と設定アクセス（kabusys.config.settings）
- データ取得・保存
  - J-Quants API クライアント（認証・ページネーション・リトライ・レート制御）
  - DuckDB へ冪等保存（raw_prices, raw_financials, market_calendar 等）
- ETL
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の一括実行
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 実行結果を表す ETLResult
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合チェック（QualityIssue）
- ニュース処理
  - RSS フィード取得（SSRF 対策、サイズ制限、トラッキング除去）
  - テキスト前処理、記事ID の冪等化
  - OpenAI を利用した銘柄別ニュースセンチメント（score_news）
- AI（LLM）
  - news_nlp.score_news: 銘柄単位の ai_score 書き込み
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースの LLM 評価を合成して市場レジーム（bull/neutral/bear）を算出・保存
- 研究用ユーティリティ
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- 監査ログ（Audit）
  - signal_events, order_requests, executions テーブルの DDL、初期化 helper（init_audit_schema / init_audit_db）

---

## 必要条件（推奨）

- Python 3.10+
  - 型注記で X | None などを使用しているため Python 3.10 以上を推奨します。
- 依存パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は requirements.txt にまとめてください）

pip 例:
```bash
pip install duckdb openai defusedxml
```
（実際のプロジェクトでは requirements.txt / pyproject.toml を用いてインストールしてください）

---

## 環境変数（主なもの）

以下はコード内で参照される主要な環境変数です。必須項目は README で明示しています。

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API のパスワード
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news / score_regime の api_key を省略した場合に参照）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタ）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視関連
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化します。

注意: config モジュールはプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動ロードします。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または最低限: pip install duckdb openai defusedxml

4. 環境変数を設定
   - .env を作成（.env.example を参考に）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
   - OpenAI を使う場合は OPENAI_API_KEY を設定

5. DuckDB データベースの準備（任意）
   - デフォルトは data/kabusys.duckdb
   - 監査ログ専用 DB を作る場合:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 基本的な使い方（サンプル）

- DuckDB 接続を作成して日次 ETL を実行する例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーを環境変数に設定してから）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジームスコア計算:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

- 監査ログ DB を初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続。必要に応じてアプリ側で監査ログ書き込み処理を実装。
```

---

## 注意事項・設計上のポイント

- ルックアヘッドバイアス回避:
  - 多くの関数は内部で datetime.today() を参照せず、明示的な target_date を受け取ります。
  - ETL やスコアリングは target_date 未満／以前のデータのみを参照するよう設計されています。
- 冪等性:
  - J-Quants から取得したデータは DuckDB へ ON CONFLICT DO UPDATE で保存され、再実行に対して冪等です。
- リトライ / フェイルセーフ:
  - 外部 API 呼び出し（OpenAI / J-Quants）はリトライ戦略を持ち、致命的な失敗があってもシステム全体が停止しないようログとフェールバック値を返す実装になっています（LLM の失敗時は 0.0 にフォールバックする等）。
- セキュリティ対策:
  - news_collector は SSRF 対策、XML DoS 対策（defusedxml）、受信サイズ制限等を実施しています。
- レート制御:
  - J-Quants API は固定間隔（120 req/min）でのスロットリングが組み込まれています。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧と簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 自動読み込み、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news: ニュースを LLM で銘柄別にスコアリングして ai_scores に保存
    - regime_detector.py
      - score_regime: ETF(1321) の MA200 乖離 + マクロニュース LLM を合成して market_regime に保存
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証・fetch/save 関数）
    - pipeline.py
      - run_daily_etl, 個別 ETL ジョブ、ETLResult クラス
    - etl.py
      - ETLResult の再エクスポート
    - calendar_management.py
      - market_calendar 管理、営業日判定、calendar_update_job
    - news_collector.py
      - RSS 取得・前処理・raw_news への保存
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ DDL、init_audit_schema / init_audit_db
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_value, calc_volatility
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank

（上記は開発中の機能やファイルのサマリです。詳細は各モジュールの docstring を参照してください）

---

## 開発 / テスト

- 環境変数自動読み込みをテスト時に無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI / J-Quants 呼び出し箇所はモック可能な設計になっています（内部の _call_openai_api や jquants_client._request 等を patch して単体テストを行うことを推奨）。

---

## 最後に

この README はコードベースの関数・モジュール概観をまとめたものです。各モジュールの詳細な利用方法や運用手順（cron / バッチ実行、監視・アラート設定、Slack 通知のフロー等）は運用ドキュメントとして別途整備してください。

不明点や追加したいサンプル（例: docker 化、systemd サービス構成、CI 設定など）があれば教えてください。README を拡張します。