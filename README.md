# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、ファクター計算、監査ログ（注文〜約定のトレーサビリティ）、市場レジーム判定などを含むモジュールセットを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買および研究プラットフォームを想定した Python パッケージです。  
主な用途は以下です。

- J-Quants API を使ったデータ取得（株価日足、財務、JPX カレンダー）
- DuckDB を使ったデータ管理（ETL・品質チェック・監査ログ）
- RSS ベースのニュース収集と OpenAI を用いたニュースセンチメント分析
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- 市場レジーム判定（ETF MA とマクロニュースの LLM スコアを合成）
- 発注/約定に関する監査スキーマ初期化機能

設計上の特徴として、ルックアヘッドバイアス対策（外部日時を参照しない等）、冪等処理（DB 保存の ON CONFLICT / DO UPDATE）、API リトライ・レート制御、通信やパース失敗時のフォールバック（例: LLM 呼び出し失敗時のゼロフォールバック）などを備えています。

---

## 主な機能一覧

- config: 環境変数自動読み込み（.env / .env.local）と Settings クラス
- data:
  - jquants_client: J-Quants API クライアント／保存ユーティリティ（fetch/save）
  - pipeline: 日次 ETL 実行（run_daily_etl, run_prices_etl 等）
  - news_collector: RSS 収集（SSRF 対策・トラッキング除去・正規化）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - audit: 監査ログ用スキーマ作成・監査 DB 初期化
  - stats: 汎用統計ユーティリティ（Z スコア正規化）
- research:
  - factor_research: モメンタム/バリュー/ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー等
- ai:
  - news_nlp: ニュースの LLM ベースセンチメントスコアリング（ai_scores への書き込み）
  - regime_detector: ETF MA とマクロニュースを組み合わせた市場レジーム判定
- monitoring / execution / strategy / その他（パッケージ初期化で公開されるモジュール群）

---

## 動作要件（想定）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - typing-extensions（必要に応じて）
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

※ 実際にはプロジェクトに requirements.txt / pyproject.toml を用意してインストールしてください。

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（プロジェクトの requirements に合わせて）
   ```bash
   pip install duckdb openai defusedxml
   # または
   pip install -r requirements.txt
   ```

4. 環境変数の設定  
   プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local は上書き）。  
   自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時等）。

   必須の環境変数（Settings で要求されるもの）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID
   - OPENAI_API_KEY（AI モジュールを使う場合）

   任意 / デフォルト:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

   例: `.env` の最小例
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベースの準備（監査ログ DB の初期化例）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # これで監査テーブルが作成されます
   ```

---

## 使い方（主な API 例）

※ ここで示す例は Python スクリプトや REPL 内で実行する想定です。

- 設定読み取り
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path object
  ```

- 日次 ETL を実行する（DuckDB 接続を渡す）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付け（AI モジュール）  
  OpenAI API キーが環境変数 `OPENAI_API_KEY` にあるか、引数で渡してください。
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマの初期化（既存接続に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- J-Quants の生 API 呼び出し（クライアントを直接利用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  data = fetch_daily_quotes(date_from=date(2026, 3, 1), date_to=date(2026, 3, 20))
  ```

- ニュース収集（RSS 1 ソースをフェッチ）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  source, url = "yahoo_finance", DEFAULT_RSS_SOURCES["yahoo_finance"]
  articles = fetch_rss(url, source)
  ```

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要ファイル一覧（src/kabusys 下）。実際のツリーに合わせてください。

- src/kabusys/
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
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（その他ファイル）
  - monitoring/（未表示のモジュール群）
  - strategy/（戦略レイヤー）
  - execution/（発注/ブローカー連携）
  - monitoring/（監視・アラート）

各モジュールはドキュメント文字列と詳細な設計方針・挙動を含んでおり、関数レベルで引数説明・副作用（DB を書き換える等）を注記しています。

---

## 注意点 / 運用メモ

- ルックアヘッドバイアス対策のため、多くの関数は内部で `date.today()` / `datetime.today()` を参照せず、呼び出し側が明示的に `target_date` を渡す設計です。バックテストや再現性のあるバッチ処理では必ず `target_date` を明示してください。
- OpenAI（LLM）呼び出しは外部サービスに依存します。API レートや費用に注意してください。AI 呼び出し失敗時はフェイルセーフ（ゼロスコア等）で継続する実装です。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml が基準）から行われます。CI やテストで自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用してください。
- DuckDB のバージョン依存（executemany の空リスト処理など）に注意しています。運用する DuckDB バージョンでの互換性検証を推奨します。
- jquants_client は API レート制限（120 req/min）を内部で守る実装になっていますが、プロダクション運用ではさらに周辺のレート管理を行うことを検討してください。

---

## 貢献 / テスト

- 追加機能や修正は PR を通してください。
- テストでは環境変数の切り替えと外部 API 呼び出しのモック化（unittest.mock.patch）を推奨します。AI 呼び出しやネットワーク IO はモックして単体テストを行うのが安全です。

---

必要であれば、この README をベースに具体的な requirements.txt / quickstart スクリプト / example notebook を追加します。どのドキュメントを優先して作成しますか？