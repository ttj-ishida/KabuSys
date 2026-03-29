# KabuSys

日本株向けの自動売買 / データプラットフォームのライブラリです。  
ETL（J-Quants）、ニュース収集・NLP、研究用ファクター計算、監査ログ、マーケットカレンダー管理、ならびに市場レジーム判定やAIベースのニューススコアリング等を含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python モジュール群です。

- J-Quants API からの株価・財務・カレンダー等の差分取得（ETL）と DuckDB への冪等保存
- RSS ベースのニュース収集と記事の前処理・銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄単位）とマクロセンチメント（市場レジーム）評価
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）と関連ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 取引フローの監査ログ（signal → order_request → execution のトレース用スキーマ）
- JPX カレンダー管理（営業日判定、next/prev_trading_day 等）

設計の共通方針として「ルックアヘッドバイアスを避ける」「冪等性」「ネットワーク/API の堅牢性（リトライ・バックオフ）」を重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（認証・ページネーション・保存関数）
  - News collector（RSS 取得・前処理・raw_news への保存）
  - Calendar 管理（is_trading_day / next_trading_day / get_trading_days）
  - Data quality チェック（欠損・重複・スパイク・日付整合性）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュースNLP（score_news）
  - 市場レジーム判定（score_regime）
  - LLM 呼び出しは OpenAI SDK（JSON mode）を想定、リトライ・フォールバック実装あり
- research/
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量解析・IC・統計サマリ（calc_forward_returns / calc_ic / factor_summary / rank）
- config.py
  - 環境変数管理（.env 自動読み込み、必須値チェック、KABUSYS_ENV 等）
- audit / monitoring / execution / strategy 等（エントリポイントとしてパッケージ公開）

---

## 必要条件

- Python 3.10+
- 推奨主要依存（例）
  - duckdb
  - openai
  - defusedxml
- （ネットワークアクセス：J-Quants API、RSS フィード、OpenAI API）

実際のプロジェクトでは requirements.txt / pyproject.toml に依存管理情報を置いてください。

---

## 環境変数

主に以下が利用されます（必須は README 内に明記）。環境変数はプロジェクトルートの `.env` / `.env.local` と OS 環境変数から自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化）。

必須（Settings._require により取得）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API と連携する場合のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID

任意 / デフォルトあり:
- KABUSYS_ENV — application mode: `development`（デフォルト）, `paper_trading`, `live`
- LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト `INFO`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — SQLite 監視 DB（デフォルト `data/monitoring.db`）
- OPENAI_API_KEY — OpenAI を使う関数に必要（引数で API キー注入可能）

注意: config.py はプロジェクトルート（.git または pyproject.toml）を起点に .env を自動ロードします。配布後やテスト時に自動読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定ください。

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境作成 & 有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（プロジェクト側に requirements.txt / pyproject.toml がある想定）
   ```
   pip install -r requirements.txt
   ```
   最低限:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数ファイルを用意
   - プロジェクトルートに `.env` を作成し、必要なキーを設定してください。例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABUSYS_ENV=development
     ```
   - 機密値は `.env.local` に置き、`.gitignore` に追加するのが良いです。

5. データベース用ディレクトリ作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な API と実行例）

以下は主要なユースケースの最小サンプルです。各関数は duckdb 接続を受け取り DuckDB 上のテーブルを参照・更新します。

- DuckDB 接続準備（デフォルトパスを settings.duckdb_path から取得）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定しないと today が使われます
  result = run_daily_etl(conn, target_date=None, id_token=None)
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄単位）を算出して ai_scores に書き込む
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"wrote {written} scores")
  ```
  - api_key を与えない場合は環境変数 OPENAI_API_KEY を参照します。
  - タイムウィンドウは前日 15:00 JST 〜 当日 08:30 JST（内部で UTC 換算）です。

- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB の初期化（監査専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター（モメンタム等）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

ログレベルや動作モードは環境変数 KABUSYS_ENV / LOG_LEVEL で調整します（development / paper_trading / live）。

---

## 注意点と設計上の留意事項

- ルックアヘッドバイアス対策
  - 多くの処理は内部で date.today() 等を直接参照せず、target_date を明示的に受け取るか ETL 呼び出し時の今日を使用します。バックテスト用途での利用では過去時点でのデータのみを用いる運用を厳守してください。
- 冪等性
  - DuckDB への保存は ON CONFLICT（UPSERT）や INSERT … ON CONFLICT DO NOTHING を使い冪等性を担保しています。
- OpenAI / J-Quants 呼び出し
  - リトライ/バックオフ/フェイルセーフ（失敗時はスコアを 0.0 にする等）を実装していますが、API レートや料金には注意してください。
- セキュリティ
  - News collector は SSRF 対策、受信サイズ制限、defusedxml 使用等の対策を施しています。ただし外部入力を扱う部分は運用時に監査を行ってください。

---

## ディレクトリ構成（抜粋）

（リポジトリのルートに README.md、pyproject.toml 等がある想定）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数設定読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py — ETL パイプライン（run_daily_etl 等） / ETLResult
    - etl.py — ETLResult 再エクスポート
    - news_collector.py — RSS 取得・前処理・保存
    - calendar_management.py — JPX カレンダー管理（is_trading_day 等）
    - quality.py — データ品質チェック（QualityIssue）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査スキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - ai, research, data の各モジュールは unit-test 用の差し替えフック（内部 _call_openai_api 等）を意図的に用意

---

## 開発・テスト

- テストは各モジュールの外部依存（ネットワークや OpenAI 呼び出し）をモックして実行することを推奨します。多くの内部関数は unittest.mock.patch による差し替えを想定した作りになっています（例: kabusys.ai.news_nlp._call_openai_api をモック）。
- 自動 .env 読み込みはテスト時に副作用となる場合があるため、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

---

## 補足

- README では主要な使い方を示しましたが、各モジュールには詳細な docstring を含んでいます。関数／クラスの引数・返り値・副作用はソースの docstring を参照してください。
- 実運用や本番接続（paper_trading / live）に移行する際は、特に発注周り（execution / order_requests）の監査と二重発注防止ロジック、ならびに Slack 通知やログの外部連携を慎重に検証してください。

---

もし README に追加したいサンプル（より詳しい ETL スケジュール例、CI 設定、requirements.txt の中身、.env.example のテンプレート等）があれば、必要に応じて追記します。