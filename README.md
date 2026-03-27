# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ「KabuSys」のリポジトリ README（日本語）。

この README ではプロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、ETL パイプライン、ニュースセンチメント解析（OpenAI）、市場レジーム判定、監査ログ（発注→約定トレーサビリティ）などを統合した内部ツールキットです。  
目的は次の通りです。

- J-Quants API を用いた株価・財務・カレンダーデータの差分取得と DuckDB への冪等保存
- RSS ベースのニュース収集と LLM を用いた銘柄ごとの NLP スコアリング
- 市場レジーム判定の自動化（ETF MA + マクロニュース）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution）のスキーマと初期化ユーティリティ
- 研究用モジュール（ファクター計算・特徴量探索）を提供

設計方針は「ルックアヘッドバイアスを避ける」「冪等性」「外部呼び出しの堅牢なリトライ/フェイルセーフ」「DuckDB を中心に軽量に動作」などです。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants からの daily quotes、financial statements、market calendar の差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE 相当）
  - ETL パイプライン（run_daily_etl）と個別 ETL ジョブ（run_prices_etl 等）

- データ品質チェック
  - 欠損値検出、スパイク検出（前日比閾値）、重複チェック、日付整合性チェック
  - QualityIssue オブジェクトでレポート

- ニュース収集・NLP
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去、gzip 上限）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメントスコアリング（score_news）
  - マクロニュースと ETF MA を合成した市場レジーム判定（score_regime）

- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、Z-score 正規化ユーティリティ

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等のスキーマ定義
  - 監査データベース初期化ユーティリティ（init_audit_db / init_audit_schema）

- 環境設定
  - .env / .env.local 自動読み込み（プロジェクトルート検出）と Settings API（kabusys.config.settings）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込み無効化

---

## 必要条件 / 依存

- Python >= 3.10（typing の | 表記を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai (OpenAI Python SDK v1系想定)
  - defusedxml
  - その他標準ライブラリ（urllib 等）

（プロジェクトの pyproject.toml / requirements.txt により正確な依存は管理してください）

---

## 環境変数（主な必須設定）

以下は本ライブラリの利用に最低限必要となる環境変数の例です（.env ファイルに記述してプロジェクトルートに置くことができます）。本コードは自動的にプロジェクトルートを探索して `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（省略時 data/monitoring.db）
- KABUSYS_ENV: one of {development, paper_trading, live}（省略時 development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env の例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env の行パースはシェル風の export/quote/comment に対応（内部実装を参照）。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存インストール
   - pip install -e ".[dev]" など、プロジェクトの pyproject/requirements に従ってください。
   - 最低限:
     - pip install duckdb openai defusedxml

4. 環境変数を用意
   - リポジトリルートに `.env` を作成し、上記の必須変数を設定してください。
   - テスト用に自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. データベース・監査スキーマ初期化（必要に応じて）
   - Python REPL などから:
     ```py
     import duckdb
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db

     conn = init_audit_db(settings.duckdb_path)  # または init_audit_db("data/audit.duckdb")
     ```

---

## 基本的な使い方（コード例）

以下は主要なユースケースの呼び出し例です。すべて DuckDB 接続（duckdb.connect）を渡して利用します。

- DuckDB 接続取得（設定ファイルの path を利用）
```py
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（ETL パイプライン）
```py
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア付け（OpenAI 必要）
```py
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026,3,20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジームの判定
```py
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))  # OpenAI API KEY は環境変数 or api_key 引数で指定
```

- 研究用ファクター計算
```py
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, columns=["mom_1m","mom_3m","mom_6m","ma200_dev"])
```

- 監査 DB 初期化（専用 DB）
```py
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 自動 .env 読み込みの挙動

- プロジェクトルートの検出は現在のファイルパスから `.git` または `pyproject.toml` を探索して行います。これによりワーキングディレクトリに依存せずパッケージ配布後も正しく動作します。
- 読み込み順序: OS 環境変数 > .env.local > .env
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます（テスト等で使用）。

.env パースは shell ライクな export/quote/comment を考慮して行われます。詳しい挙動は kabusys.config の実装参照。

---

## ログ設定 / 環境

- KABUSYS_ENV の有効値: `development`, `paper_trading`, `live`
- LOG_LEVEL の有効値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

settings オブジェクト（kabusys.config.settings）を通じて設定値を参照できます。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内部の主要モジュール構成（src/kabusys 以下）です。細かなモジュールは README で省略していますが、主要機能は網羅しています。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースを集約して OpenAI で銘柄ごとにスコアリング
    - regime_detector.py            — ETF MA とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - etl.py                        — ETL インターフェース再エクスポート
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py             — J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py             — RSS 収集（SSRF 対策等）
    - quality.py                    — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                      — 汎用統計ユーティリティ（zscore_normalize）
    - calendar_management.py        — 市場カレンダー管理・営業日判定・更新ジョブ
    - audit.py                      — 監査ログ（テーブル定義と初期化）
    - pipeline.py                   — ETL パイプライン、ETLResult 定義
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — 将来リターン, IC, 統計サマリー 等

---

## 開発上の注意 / 設計上の考慮点

- ルックアヘッドを避けるため、内部ロジックは date.today() / datetime.today() の直接参照を避け、呼び出し側から target_date を渡す設計が多くなっています。バッチ的に過去日付を与えて再現性のある処理が可能です。
- OpenAI / J-Quants 呼び出しはリトライとフェイルセーフを備えています。API エラー時はデフォルトでスコアを 0 にする等のフォールバックがあるため、ETL 全体が停止しない設計です。
- DuckDB の executemany に対する互換性（空リスト不可）など実環境の制約に配慮した実装です。
- news_collector は SSRF 対策、受信サイズ制限、XML パースの防御を実装しています（defusedxml を利用）。

---

## よくある操作（FAQ）

- Q: OpenAI API を使いたくない / テストで差し替えたい  
  A: news_nlp._call_openai_api / regime_detector._call_openai_api 等はテストで patch して差し替えられるように分離されています。

- Q: 自動で .env を読み込んでほしくない  
  A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Q: DuckDB スキーマはどこで定義される？  
  A: 各モジュール（audit.init_audit_schema 等）は自身の DDL を持ち、初期化ユーティリティで作成します。ETL の前に必要なスキーマを初期化してください。

---

## 貢献 / 開発フロー

- 新しい機能追加やバグ修正は Pull Request を通して行ってください。
- 単体テスト・統合テストを追加する際は API 呼び出しやネットワーク I/O をモックするなどして外部依存を分離してください（既存コードはその点を想定して設計されています）。

---

以上が KabuSys の概要と基本的な使い方です。細かい API（各関数の引数・戻り値）については各モジュールの docstring を参照してください。必要であれば README を拡張して各ユースケースの詳細サンプルや運用手順（cron / Airflow / systemd 連携など）を追加できます。