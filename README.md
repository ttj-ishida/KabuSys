# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。J-Quants や RSS、OpenAI（LLM）等を組み合わせ、データ取得（ETL）、データ品質チェック、ニュースセンチメント、ファクター計算、戦略リサーチ、監査ログなどを提供します。

---

## 主な特徴

- J-Quants API を用いた株価（OHLCV）／財務データ／市場カレンダーの差分取得・保存（DuckDB 互換）
- ニュース収集（RSS）→ raw_news 保存、銘柄紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（銘柄別 ai_scores）およびマクロセンチメントによる市場レジーム判定
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（信号→発注→約定のトレーサビリティ）用のスキーマ作成ユーティリティ
- 設定は環境変数 / .env ファイルから読み込み（プロジェクトルート自動検出）

---

## 目次

- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数（主要）
- 使い方（代表的な API 例）
- ディレクトリ構成

---

## 必要条件

- Python 3.10+
- DuckDB
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全化）
- その他（urllib, datetime 等は標準ライブラリ）

（パッケージ依存は setup / pyproject によります。開発環境では仮想環境推奨）

---

## インストール（開発環境例）

1. リポジトリをクローン
   ```
   git clone <repo_url>
   cd <repo_dir>
   ```

2. 仮想環境作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 依存のインストール（例）
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトの pyproject / requirements.txt に従う
   ```

4. パッケージを編集可能モードでインストール（任意）
   ```
   pip install -e .
   ```

---

## 環境変数（主要）

KabuSys は環境変数（またはプロジェクトルートの `.env` / `.env.local`）から設定を読み込みます。自動読み込みはデフォルトで有効です。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主なキー:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (既定: http://localhost:18080/kabusapi)
- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（score_news / regime 用）。関数呼び出し時に明示的に渡すことも可能
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB パス（デフォルト）
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB デフォルト: data/monitoring.db)
- 監視 / PID
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)
- 実行環境
  - KABUSYS_ENV (development / paper_trading / live) — デフォルト development
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト INFO

設定は kabusys.config.settings 経由で参照できます（例: settings.duckdb_path）。

---

## 使い方（代表例）

以下は代表的なモジュール呼び出し例。関数は look-ahead bias を防ぐ設計（内部で date.today() を直接参照しない）になっています。OpenAI キー等は環境変数または引数で指定できます。

- DuckDB 接続準備（例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（prices / financials / calendar と品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  # target_date は date オブジェクト（省略時は今日）
  result = run_daily_etl(conn, target_date=None)
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別 ai_scores へ書き込み）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OpenAI API キーを env に設定しておくか、api_key に渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  print("結果:", res)
  ```

  - score_regime の内部は ETF 1321 の 200 日 MA とマクロニュースの LLM センチメントを 70% / 30% で合成して 'bull'/'neutral'/'bear' を判定します。

- 監査ログスキーマ初期化（監査用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルとインデックスが作成されます
  ```

- カレンダー関係（営業日判定）
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  moment = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  ```

注意:
- OpenAI 呼び出しはネットワークリトライやレスポンスバリデーション実装済みです。不安定時は部分的にスキップして継続する設計です（フェイルセーフ）。
- ETL / データ保存関数は冪等（ON CONFLICT DO UPDATE 等）を意識して実装されています。

---

## .env 自動読み込みについて

- プロジェクトルート（このパッケージのファイル位置から親方向で .git または pyproject.toml を基準に探索）にある `.env` と `.env.local` が自動読み込みされます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - `.env.local` は既存環境を上書き（override）しますが、OS 環境を保護するため既存 OS 環境変数は上書きされません。
- 自動読み込みを無効にする場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings 管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（銘柄別 ai_scores 生成）
    - regime_detector.py — マクロ＋ETF 200 日 MA を合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック含む）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult 再エクスポート
    - calendar_management.py — 市場カレンダー管理（営業日判定、カレンダー更新ジョブ）
    - news_collector.py — RSS 収集 → raw_news 保存ロジック
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー ファクター
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - ai, research, data などのモジュールが公開 API を提供

（実際のリポジトリでは tests、scripts、docs などが追加で存在することが一般的です）

---

## 注意事項 / ベストプラクティス

- OpenAI API キーや J-Quants のリフレッシュトークンは機密情報のため、.gitignore に .env を含める等してソース管理に含めないでください。
- ETL やモデル推論処理は長時間かかる場合があります。運用ではジョブ管理（cron / Airflow / systemd など）で監視することを推奨します。
- ニュース収集／LLM 呼び出しは API レート制限に注意してください（jquants_client はレート制御済み、OpenAI は適宜リトライ実装がありますが運用での制御も必要です）。
- DuckDB スキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar 等）は ETL 実行前に作成しておく必要があります。スキーマ初期化ユーティリティが別途ある場合はそれを使用してください（リポジトリ外の schema 初期化処理を参照）。

---

## サポート / 開発

- 開発中に環境を固定したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、明示的に環境変数を注入してください。
- テストでは OpenAI/J-Quants 呼び出し部分をモックする設計になっています（関数単位で差し替え可能）。

---

この README はリポジトリ内のコード（config / data / ai / research モジュール）を元にした概要・使用方法をまとめたものです。詳細な API リファレンスやスキーマ定義はソース内の docstring を参照してください。