# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得・DuckDB 保存）、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ管理などの機能群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質管理・特徴量計算・AI を用いたニュースセンチメント評価・市場レジーム判定・監査ログ管理を行うためのモジュール群です。  
主な利用シーンは以下です。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する日次 ETL
- RSS からのニュース収集と raw_news / news_symbols への保存
- OpenAI によるニュースセンチメント（銘柄別）とマクロセンチメントの算出
- ETF（1321）を利用した市場レジーム（bull / neutral / bear）判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究用ユーティリティ
- 監査ログ（signal_events, order_requests, executions）テーブルの初期化・管理
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上の注意点として、「ルックアヘッドバイアスの排除」を重視しており、内部実装は日付参照の扱いや API 呼び出しのリトライ / フェイルセーフに配慮されています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・保存：save_daily_quotes 等）
  - market_calendar 管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - ニュース収集（RSS の正規化・SSRF 対策・前処理・raw_news への保存）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログ初期化（init_audit_schema, init_audit_db）
  - 汎用統計（zscore_normalize）
- ai/
  - ニュース NLP（score_news: 銘柄別センチメント算出 → ai_scores テーブルへ書き込み）
  - 市場レジーム判定（score_regime: ma200 + マクロセンチメント → market_regime テーブルへ書き込み）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - .env 自動ロード（.env / .env.local）と Settings オブジェクト（環境変数アクセスの集中化）
  - KABUSYS_ENV / LOG_LEVEL 検証（development, paper_trading, live）

---

## 必要条件（依存パッケージの例）

この README はソースを基にした概要です。実行には下記の主要パッケージが必要です（プロジェクト側で requirements.txt がある場合はそちらを利用してください）。

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他: 標準ライブラリ（urllib, datetime, json 等）

例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# もしパッケージ化されていれば:
# pip install -e .
```

---

## 環境変数 / 設定

config.Settings によりアプリケーション設定を取得します。自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。

主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用のリフレッシュトークン
- OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー（score_news / score_regime）
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知に使用
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

例（.env）:
```dotenv
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン:
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール:
   - プロジェクトに requirements.txt があればそれを利用
     ```bash
     pip install -r requirements.txt
     ```
   - ない場合は最低限:
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数を設定（`.env` を作成）:
   - レポジトリルートに `.env`（必要なキーを含む）を作成します。上の例を参照。

5. DuckDB データベース初期化（必要に応じてスキーマ用 SQL を実行するユーティリティが別にあればそれを利用）:
   - 監査ログ専用 DB を初期化する例（Python REPL）:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn を使ってテーブルが作成されたことを確認できます
     ```

---

## 使い方（主要な API とサンプル）

以下はライブラリの主要関数の使い方例です。実行時は settings（環境変数）を正しく設定しておいてください。

- DuckDB 接続:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別スコア付与）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は環境変数かapi_key引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {n_written} scores")
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- 設定値参照:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点:
- AI 功能（score_news / score_regime）は OpenAI API を使います。OPENAI_API_KEY が必要です。
- J-Quants 関連の ETL は JQUANTS_REFRESH_TOKEN を必要とします（settings が自動で get_id_token を呼びます）。
- ETL は外部 API（J-Quants）にアクセスするため、ネットワーク接続と有効な認証情報が必要です。

---

## ディレクトリ構成

主要なソースツリー（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（銘柄別）
    - regime_detector.py             — 市場レジーム判定（ETF 1321 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - pipeline.py                    — ETL パイプラインと run_daily_etl
    - etl.py                         — ETL 便利 API（ETLResult 再エクスポート）
    - news_collector.py              — RSS 収集と前処理
    - calendar_management.py         — market_calendar / 営業日判定
    - quality.py                     — データ品質チェック
    - stats.py                       — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Value / Volatility
    - feature_exploration.py         — forward returns, IC, ranking, summary
  - ai/ (上記)
  - research/ (上記)

ファイルとモジュールは機能別に整理されており、ETL / data platform 周りは data/*、AI 関連は ai/*、研究系は research/* にまとまっています。

---

## 運用上の注意・実装上の特徴

- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を探索して `.env` と `.env.local` を読み込みます。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを抑止できます（テスト用）。
- AI 呼び出しはリトライを備えています。API 失敗時は多くのケースで安全側のデフォルト（スコア 0.0）にフォールバックします。
- J-Quants クライアントはレート制限（120 req/min）に準拠するための簡易 RateLimiter と、401 自動リフレッシュ・ページネーション対応を備えています。
- DuckDB への保存は冪等に設計（ON CONFLICT DO UPDATE）されています。
- 日付・時間は原則 UTC または naive date を想定して取り扱われ、ルックアヘッドバイアスを避ける実装になっています。
- news_collector は SSRF 防止、XML Bomb/defusedxml、受信サイズ制限 などセキュリティ対策あり。

---

## 貢献・拡張

- 新しい ETL ソースの追加は `kabusys.data.jquants_client` に倣って実装してください（ページネーション・トークン管理・保存の設計を参考に）。
- AI モデルやプロンプト調整は `kabusys.ai.news_nlp` / `kabusys.ai.regime_detector` を編集して行います。テスト用に _call_openai_api をモック可能です。
- スキーマや監査ログは `kabusys.data.audit` 内にあり、冪等に初期化できます。

---

## 参考 / トラブルシューティング

- OpenAI API のレスポンスで JSON パースが失敗する可能性があるため、パーサは前後の不要テキストを拾って JSON 部分を抽出する処理があります。しかし想定外のレスポンスが来た場合はログを確認してください。
- DuckDB の executemany は空リストを受け付けないバージョンの挙動に依存する箇所があります（実装内にチェックあり）。
- J-Quants API の 401 は自動で refresh トークンから id_token を取得して再試行されます。トークンが無効・期限切れの場合は設定値を再確認してください。

---

README はここまでです。より詳細な使用例・運用手順（CI / cron による ETL スケジュール、Slack 通知の統合、kabu ステーションとの発注実装など）が必要であれば、利用ケースに合わせた追加ドキュメントを作成します。