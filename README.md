# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュース収集・NLP（OpenAI を利用したセンチメント）、市場レジーム判定、リサーチ向けファクター計算、監査ログ（約定トレース）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムや研究プラットフォーム向けに設計された Python モジュール群です。主な用途は次の通りです。

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を用いたデータ保存（冪等保存）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と NLP による銘柄別センチメントスコア算出（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュースの組合せ）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 市場カレンダー管理・営業日判定
- 様々な安全対策（SSRF 防止、API レート制御、リトライロジック等）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
  - pipeline: 日次 ETL 実行（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 収集（SSRF 対策、前処理、冪等保存）
  - calendar_management: JPX カレンダー管理・営業日判定
  - audit: 監査ログスキーマ初期化・監査 DB 初期化
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出（OpenAI）
  - regime_detector.score_regime: 市場レジーム判定（ETF MA + マクロニュース）
- research/
  - factor_research: 各種ファクター計算（momentum/value/volatility）
  - feature_exploration: 将来リターン計算、IC、統計サマリー等

---

## 動作要件

- Python 3.10+
- 必要な外部パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ: urllib, json, logging 等）

※ 実際の requirements.txt はプロジェクト側で管理してください。上記は最低限の依存例です。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - もし requirements.txt があれば:
     ```
     pip install -r requirements.txt
     ```
   - 最低限（例）:
     ```
     pip install duckdb openai defusedxml
     ```

4. パッケージをインストール（開発モード）
   ```
   pip install -e .
   ```

5. 環境変数 / .env の準備  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` として設定を置くと自動ロードされます（OS 環境変数が優先）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数（.env 例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
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
   KABUSYS_ENV=development   # development|paper_trading|live
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な API）

以下はライブラリの主要 API の使い方例です。DuckDB コネクション（duckdb.connect）を作成して渡します。

- 設定を参照する
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続を作って ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY or api_key 引数）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続を返す
  ```

- リサーチ用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  ```

---

## 実装上の注意点 / ヒント

- .env 自動ロード挙動: OS 環境変数 > .env.local > .env の順で読み込まれます。テスト等で自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Look-ahead bias の防止: AI スコアリング / レジーム判定 / ETL などは内部で date 引数を使い、date.today() に直接依存しないように設計されています。バックテスト用途でも日付制御しやすくなっています。
- 冪等性: J-Quants からの保存処理（raw_prices、raw_financials、market_calendar）は ON CONFLICT DO UPDATE の冪等実装になっています。
- エラー処理: API 呼び出しはリトライ（指数バックオフ）やフォールバック（例: LLM の失敗時は中立スコア）を実装しています。ログを確認して運用判断してください。
- セキュリティ: news_collector では SSRF 対策、defusedxml による XML パース防護、レスポンスサイズ制限などを備えています。

---

## ディレクトリ構成

（提供コードに基づく主要ファイル・ディレクトリ）

- src/
  - kabusys/
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
      - quality.py
      - news_collector.py
      - calendar_management.py
      - stats.py
      - audit.py
      - (その他: audit 初期化、etl ヘルパ等)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/（別モジュール群）...
- pyproject.toml / setup.cfg / requirements.txt （プロジェクトルート）※存在する想定

各モジュールは概ね以下の責務で分離されています：
- data: データ取得・保存・品質管理・カレンダー・監査
- ai: ニュース NLP と市場レジーム判定（OpenAI）
- research: ファクター計算・探索的解析
- config: 環境変数と設定の集中管理

---

## ロギング / モニタリング

- 設定は環境変数 `LOG_LEVEL` で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- 実行監視に関する設定は `PID_FILE_PATH`, `KILL_FLAG_PATH`, `CPU_THRESHOLD_PCT` 等でカスタマイズできます。

---

## 参考（よくある操作）

- .env の自動ロードを検証したい場合は、パッケージにアクセスして settings を参照してください。
- OpenAI を使う処理は API キーが必須（引数で上書き可）。テストでは内部の _call_openai_api をモックして代替できます。
- DuckDB のスキーマ初期化・監査テーブル初期化は `init_audit_db` / `init_audit_schema` を利用してください。

---

## ライセンス / 貢献

（本テンプレートでは具体的なライセンス、コントリビューション規程は含まれていません。プロジェクトに合わせて LICENSE ファイルや CONTRIBUTING を追加してください。）

---

この README はコードベースに含まれる主要モジュールと使用例をまとめたものです。詳細な API や追加の実行スクリプトがある場合は、プロジェクトルートのドキュメント（例: docs/）やモジュールの docstring を参照してください。何か補足や特定の使い方（例: デプロイ手順、CI 設定）を README に追加したい場合は教えてください。