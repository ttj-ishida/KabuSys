# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants や RSS、OpenAI（LLM）を組み合わせてデータ収集（ETL）、ニュース NLP、マーケットレジーム判定、ファクター計算、監査ログ管理などを行います。

---

## 主な機能

- データ ETL（J-Quants 経由）
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの差分取得・保存（DuckDB）
  - 品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（RSS）と前処理（SSRF 対策・トラッキング除去）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコア算出）
- 市場レジーム判定（ETF 1321 の MA とマクロ記事の LLM センチメントを合成）
- 研究用ユーティリティ（モメンタム/ボラティリティ/バリュー等のファクター計算、将来リターン、IC、統計サマリ）
- 監査ログ（シグナル→発注→約定のトレーサビリティを保持する監査テーブル、DuckDB）
- 設定管理（.env 自動読み込み、環境毎設定、ログレベル制御）

---

## 前提 / 必要要件

- Python 3.9+（型注釈や match 等は使用していませんが、typing の新機能を利用）
- 主要依存パッケージ（代表例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS）
- J-Quants のリフレッシュトークン、OpenAI API キー 等の環境変数

（実プロジェクトでは requirements.txt / pyproject.toml をご利用ください）

---

## セットアップ手順（ローカル）

1. リポジトリをクローンし開発用仮想環境を作る
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   # 依存関係をインストール（実際はプロジェクトの requirements を使用）
   pip install duckdb openai defusedxml
   ```

2. パッケージをインストール（開発編集用）
   ```bash
   pip install -e .
   ```

3. 環境変数設定（プロジェクトルートに `.env` を置く）
   - パッケージはプロジェクトルート（.git または pyproject.toml がある階層）を探索して自動的に `.env` / `.env.local` を読み込みます。
   - 自動読み込みを無効化したい場合：
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   - 主要な環境変数（例）:
     ```
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     KABU_API_PASSWORD=...
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PID_FILE_PATH=data/execution.pid
     KILL_FLAG_PATH=data/kill.flag
     KILL_FLAG_CLEAR_ON_START=0
     CPU_THRESHOLD_PCT=90.0
     MEMORY_THRESHOLD_PCT=85.0
     DISK_THRESHOLD_PCT=90.0
     KABUSYS_ENV=development  # development|paper_trading|live
     LOG_LEVEL=INFO
     ```

4. データディレクトリ作成（例）
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的なユースケース）

以下は Python REPL またはスクリプトから呼び出す例です。

- DuckDB に接続して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- OpenAI を使ったニューススコアリング（前日 15:00 JST ～ 当日 08:30 JST のウィンドウ）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書込件数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ用 DB 初期化（別 DB に監査テーブルを作る）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # 以後 conn を利用して監査ログを操作
  ```

- 研究用ファクター計算（モメンタム等）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  ```

- RSS フィードの取得（ニュースコレクタ）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
  ```

注意点:
- OpenAI / J-Quants API のエラー時はフェイルセーフ設計があります（多くの箇所でフォールバック値やスキップを行う）。ログを確認してください。
- 設定は settings オブジェクト経由で参照できます（例: from kabusys.config import settings; settings.duckdb_path）。

---

## ディレクトリ構成（主要ファイル）

概要的なツリー（src/ 以下を表示）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env 自動ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（銘柄別スコア）
    - regime_detector.py         — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py     — 市場カレンダー管理・営業日判定
    - etl.py (pipeline export)   — ETL インターフェース
    - pipeline.py                — 日次 ETL パイプライン（prices/financials/calendar）
    - stats.py                   — 統計ユーティリティ（z-score 等）
    - quality.py                 — データ品質チェック
    - audit.py                   — 監査ログ（テーブル定義・初期化）
    - jquants_client.py          — J-Quants API クライアント + 保存ロジック
    - news_collector.py          — RSS 収集・前処理・SSRF 対策
  - research/
    - __init__.py
    - factor_research.py         — モメンタム/ボラティリティ/バリュー
    - feature_exploration.py     — 将来リターン / IC / 統計サマリ
  - research/...                 — 研究用ユーティリティ群
  - その他（strategy, execution, monitoring 等は __all__ に含まれる想定）

（実際のリポジトリには strategy/execution/monitoring モジュールも含まれる想定です）

---

## 設定と動作ポリシー（重要なポイント）

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` と `.env.local` を読み込みます。
  - 優先順位: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時に有用）。

- 環境（KABUSYS_ENV）
  - 有効値: development, paper_trading, live
  - 設定により is_live / is_paper / is_dev の判定ができます。

- ログレベル
  - LOG_LEVEL 環境変数で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- OpenAI / J-Quants のリトライやフェイルセーフ
  - 多くの外部 API 呼び出しはリトライやフォールバックを備えています（429/5xx の指数バックオフ、API エラー時はスコアを 0 にフォールバック 等）。

- DuckDB 書き込みは冪等（ON CONFLICT）を基本としています。部分失敗時に既存データを不必要に削除しない実装方針が取られています。

---

## トラブルシューティング

- OpenAI 呼び出しで JSON パースに失敗する場合:
  - レスポンスが期待形式でない場合は警告ログが出てスコアはゼロまたはスキップされます。プロンプトやモデル（環境変数 OPENAI_API_KEY の有無）を確認してください。
- J-Quants 認証エラー（401）:
  - jquants_client はリフレッシュトークンから id_token を自動取得し、401 でトークン再取得を試みます。`JQUANTS_REFRESH_TOKEN` が正しく設定されているか確認してください。
- DuckDB ファイルのパーミッション:
  - DUCKDB_PATH の親ディレクトリが存在するか、プロセスに書き込み権限があるか確認してください。
- RSS 取得で接続先がプライベートアドレスと判定される:
  - news_collector は SSRF 対策でプライベート IP / ループバック宛のアクセスを拒否します。正しい公開 RSS URL を利用してください。

---

## 開発上のヒント

- テストや一時的に環境読み込みを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使う。
- OpenAI コール部分はテスト容易性を考慮して内部呼び出し関数をモックできるよう設計されています（unittest.mock.patch で差し替え可能）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード側で空チェックが入っています（互換性に注意）。

---

この README はコードベースの要点と代表的な使い方をまとめたものです。より詳細な API（関数引数、返り値、例外など）は各モジュール（src/kabusys/data/*.py、src/kabusys/ai/*.py、src/kabusys/research/*.py）を参照してください。必要であれば、セットアップのための requirements.txt やサンプル .env.example のテンプレートも作成しますのでお知らせください。