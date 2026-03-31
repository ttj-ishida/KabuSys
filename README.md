# KabuSys

日本株向け自動売買 / データプラットフォーム用のライブラリ群です。  
ETL（J-Quants からの市場データ取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（DuckDB）などのユーティリティをまとめて提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ（API障害時の安全なフォールバック）」です。

---

## 機能一覧

- 環境変数 / .env 管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の検証（Settings クラス）
- データ ETL（J-Quants）
  - 株価日足（raw_prices）取得と DuckDB 保存（差分更新、ページネーション対応、リトライ）
  - 財務データ取得と保存（raw_financials）
  - 市場カレンダー取得と保存（market_calendar）
  - ETL の一括実行（run_daily_etl）と ETLResult レポート
- データ品質チェック
  - 欠損（OHLC）検出、重複、スパイク（急騰/急落）、日付整合性チェック
  - QualityIssue を返却し、ETL 実行側が判定可能
- ニュース収集（RSS）
  - RSS フィードの取得、前処理、SSRF 対策、トラッキングパラメータ除去、raw_news/ news_symbols への保存想定
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に投げ、センチメント（ai_scores）を生成（gpt-4o-mini、JSON mode）
  - リトライ・バリデーション・スコアクリップ
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成し、`bull/neutral/bear` を判定
  - OpenAI 呼び出しはフェイルセーフ（失敗時は 0.0）
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（DuckDB）
  - 監査用のインデックスと初期化関数（init_audit_schema / init_audit_db）
- リサーチ用ユーティリティ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー、Zスコア正規化

---

## セットアップ手順

以下はローカル開発用の最小セットアップ手順です。

前提:
- Python 3.10+（型注釈に union 型等を使用）
- DuckDB を利用するためのネイティブ拡張が必要な場合は環境に応じた準備

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（例: pip）
   必要な主要パッケージ（プロジェクトに合わせて requirements を用意してください）
   ```
   pip install duckdb openai defusedxml
   ```
   - duckdb：データベース
   - openai：LLM 呼び出し（gpt-4o-mini 等）
   - defusedxml：RSS パースの安全化
   - （必要なら）他に requests 等を追加

4. 環境変数 / .env の準備  
   プロジェクトルート（.git や pyproject.toml を含むディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（読み込みは os 環境変数 > .env.local > .env の順）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   最低限設定が必要な環境変数（README 用の例）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabu API（発注などを使う場合）
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack（通知等に使用）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456

   # DB パス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   Settings クラスで必須項目が未設定だと ValueError を送出します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。

---

## 使い方（主要なユーティリティ例）

以下は Python REPL やスクリプト内での利用例です。DuckDB 接続は `duckdb.connect(<path>)` を使用します。

- 環境設定の取得
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  ```

- 日次 ETL の実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（ai スコア）の実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))  # 戻り値: 書込み銘柄数
  print("written:", written)
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # returns 1 on success
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events/order_requests/executions テーブルが作成されます
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  ```

注意点:
- LLM（OpenAI）の呼び出しには `OPENAI_API_KEY` が必要です。API 障害時はフェイルセーフでスコア 0 を採用する設計箇所がありますが、API キー未設定だと関数が ValueError を投げます。
- J-Quants API 呼び出しはレート制限・リトライ・トークン自動更新を備えていますが、JQUANTS_REFRESH_TOKEN の設定は必須です。

---

## ディレクトリ構成

概要（主なファイル/モジュール）:

- src/kabusys/
  - __init__.py
  - config.py
    - Settings: 環境変数読み込み・検証、.env 自動ロード機能
  - ai/
    - __init__.py
    - news_nlp.py          : ニュースの LLM スコアリング（ai_scores 書込）
    - regime_detector.py   : 市場レジーム判定ロジック（ma200 + macro sentiment）
  - data/
    - __init__.py
    - jquants_client.py    : J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py          : ETL パイプライン（run_daily_etl 等）
    - etl.py               : ETLResult 再エクスポート
    - quality.py           : データ品質チェック
    - stats.py             : 共通統計ユーティリティ（zscore_normalize）
    - calendar_management.py: 市場カレンダー管理（営業日判定, next/prev 等）
    - news_collector.py    : RSS 収集・前処理・SSRF 対策
    - audit.py             : 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py   : モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py: 将来リターン, IC, サマリー等
  - ai、data、research などの内部ユーティリティ群がモジュール化されています。

---

## 補足・運用メモ

- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を探索）を起点に `.env` と `.env.local` を読み込みます。
  - 読み込み順: OS 環境 > .env.local > .env
  - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。

- テストとモック
  - OpenAI 呼び出しや外部ネットワークアクセス部は、内部関数をモックできるよう設計されています（例: news_nlp._call_openai_api、regime_detector._call_openai_api、news_collector._urlopen など）。

- 安全性・堅牢性
  - RSS の取得では SSRF 対策（ホストのプライベート判定、リダイレクト検査）やレスポンスサイズ制限を実装しています。
  - J-Quants クライアントはレート制御とリトライ、401 時の token refresh を備えています。
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）を可能な限り採用しています。

---

この README はコードベースの主要機能と使い方の概要を示します。詳細な API 仕様やスキーマ定義は各モジュールの docstring を参照してください。必要であれば、導入向けのサンプルスクリプトや docker-compose / systemd サービスの設定例も作成できます。ご希望があれば教えてください。