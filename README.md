# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL・データ品質チェック・マーケットカレンダー管理・ニュース収集・AIベースのニュースセンチメント評価・市場レジーム判定・リサーチ用ファクター群・監査ログ（トレーサビリティ）などの機能を備えています。

---

## プロジェクト概要

KabuSys は日本株の運用基盤・研究プラットフォーム向けに設計された Python モジュール群です。主な目的は以下です。

- J-Quants API を用いた日次データ ETL（株価、財務、カレンダー）
- DuckDB を使ったデータ保存と効率的な SQL 処理
- ニュース記事の収集と前処理（RSS）
- OpenAI（gpt-4o-mini 等）を用いたニュースの NLP スコアリング（銘柄別 ai_score、マクロセンチメント）
- ETF の 200 日移動平均乖離と LLM センチメントを組み合わせた市場レジーム判定
- 研究用ファクター（モメンタム・ボラティリティ・バリュー等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）を保持するスキーマ初期化ユーティリティ

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（認証・リトライ・ページネーション・保存関数）
  - ニュース収集（RSS フェッチ・前処理・SSRF 対策）
  - カレンダー管理（営業日判定、next/prev/get_trading_days）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化 等）
- ai/
  - ニュース NLP（銘柄別スコア: score_news）
  - 市場レジーム判定（ma200 + マクロセンチメント合成: score_regime）
  - OpenAI 呼び出しはリトライ・フォールバック付きで安全に設計
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・将来リターン計算・IC 計算・統計サマリ

---

## 要件

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- （任意）テスト・デバッグ用に logging 等

インストール例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

requirements.txt がある場合はそれを使ってください。

---

## セットアップ手順

1. リポジトリをクローン／配置する。
2. 必要パッケージをインストール（上記参照）。
3. 環境変数を設定するか、プロジェクトルートに `.env` / `.env.local` を置く。

自動的に読み込まれる条件:
- パッケージは起点ファイルからプロジェクトルートを探索し、`.git` または `pyproject.toml` がある親ディレクトリをプロジェクトルートと判定します。
- プロジェクトルートに `.env` と `.env.local` があれば自動で読み込みます（OS 環境変数優先）。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨する主要環境変数（.env の例）:

J-Quants / API
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

OpenAI
- OPENAI_API_KEY=your_openai_api_key

kabu API（必要な場合）
- KABU_API_PASSWORD=your_kabu_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi

その他（デフォルト値あり）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development         # development | paper_trading | live
- LOG_LEVEL=INFO

注意: 本番（live）モードで実行する場合は、API キーやパスワード管理に十分注意してください。OpenAI の利用は課金が発生します。

---

## 初期化（監査ログ DB 例）

監査ログ用の DuckDB を初期化する例:

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# ファイル DB を初期化（必要な親ディレクトリは自動作成）
conn = init_audit_db(settings.duckdb_path)  # settings.duckdb_path は Path オブジェクト
# conn は duckdb.DuckDBPyConnection
```

init_audit_db は UTC タイムゾーン固定や DDL の作成（冪等）を行います。

---

## 使い方（代表的なユースケース）

- 日次 ETL の実行（データ取得・保存・品質チェックの一括実行）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（銘柄別 ai_scores へ書き込む）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
print(f"scored {count} codes")
```

- 市場レジームのスコアリング（日次）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使用
```

- 市場カレンダー更新ジョブ:

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
saved = calendar_update_job(conn)
print(f"saved {saved} calendar records")
```

- 研究用ファクター計算例:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records))
```

---

## 環境変数・設定の詳細

- 設定は `kabusys.config.settings` 経由でアクセスできます。例: `settings.jquants_refresh_token`、`settings.duckdb_path`、`settings.env` など。
- 自動 `env` ロードは `.env` / `.env.local` から行われます（プロジェクトルートが検出された場合）。`.env.local` は `.env` の値を上書きします。
- `KABUSYS_ENV` は `development` / `paper_trading` / `live` のいずれかで、`settings.is_live` 等で判定できます。
- `LOG_LEVEL` は `DEBUG|INFO|WARNING|ERROR|CRITICAL` のいずれかを指定します。

---

## 注意事項 / ベストプラクティス

- OpenAI 呼び出しや外部 API 呼び出しはコストやレート制限があるため、本番実行前に負荷・コストを把握してください。
- J-Quants API にはレート制限と認証フローがあり、モジュールは自動リトライ・トークンリフレッシュを実装しています。リフレッシュトークンは機密情報として扱ってください。
- DuckDB のファイルパスはデフォルト `data/kabusys.duckdb` です。必要に応じて `.env` で変更してください。
- ETL / AI 処理は「ルックアヘッドバイアス」を避ける設計になっています（target_date を明示し、当日以降のデータを参照しない等）。

---

## ディレクトリ構成

（src/kabusys 配下の主要ファイル／モジュール）

- kabusys/
  - __init__.py
  - config.py                     # .env 自動読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py                  # 銘柄別ニュース NLP（score_news）
    - regime_detector.py           # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント + DuckDB 保存
    - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
    - etl.py                       # ETL 型の再エクスポート（ETLResult）
    - news_collector.py            # RSS ニュース収集・前処理
    - calendar_management.py       # JPX カレンダー管理・営業日判定
    - quality.py                   # データ品質チェック
    - stats.py                     # 汎用統計ユーティリティ
    - audit.py                     # 監査ログスキーマ / init_audit_db
  - research/
    - __init__.py
    - factor_research.py           # モメンタム・バリュー・ボラティリティ等
    - feature_exploration.py       # 将来リターン・IC・統計サマリなど

---

## 開発・テストに関する補足

- モジュール内の外部 API 呼び出しはテスト時にモック可能な作り（関数差し替え）になっています（例: OpenAI 呼び出し部分に _call_openai_api をラップ）。
- .env の自動ロードはテストの際に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- DuckDB を用いているため、ローカルでの単体テストはメモリ DB（":memory:"）やテスト用ファイルで容易に実行できます。

---

必要であれば、README に以下の追加を作成できます:
- 具体的な .env.example（テンプレート）
- CI / デプロイ手順（systemd / cron / Airflow などでスケジュールする例）
- よくあるトラブルシュート集（OpenAI・J-Quants のエラー対応）

希望があれば上記のいずれかを追記します。