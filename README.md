# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants からのデータ取得・ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（audit）などを備えたモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータプラットフォームと研究・運用ワークフローのためのツールセットです。主要機能は次の通りです。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL（レート制御・リトライ・トークン自動更新対応）
- DuckDB を用いた永続化と品質チェック（データ欠損、スパイク、重複、日付不整合）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去、受信制限）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースの統合）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ）と特徴量解析ユーティリティ
- 監査ログ（signal_events / order_requests / executions）スキーマと初期化ユーティリティ
- 設定管理：.env / .env.local / OS 環境変数の自動読み込み（任意で無効化可能）

設計方針として、バックテストでのルックアヘッドバイアスを避けること、外部 API 呼び出しの障害に対するフェイルセーフ、DuckDB を中心とした軽量で移植性の高い実装を重視しています。

---

## 機能一覧（主要 API）

- 設定
  - `kabusys.config.settings`：環境変数ベースの設定アクセス（JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY など）
  - 自動 .env ロード：プロジェクトルート（.git または pyproject.toml 基準）から `.env` / `.env.local` を読み込み

- データ ETL / データ品質
  - `kabusys.data.pipeline.run_daily_etl(conn, target_date=...)`：日次 ETL（calendar / prices / financials / quality checks）
  - `kabusys.data.jquants_client`：J-Quants との通信・保存 (`fetch_*`, `save_*` 等)
  - `kabusys.data.quality`：各種品質チェック（欠損・重複・スパイク・日付不整合）
  - `kabusys.data.calendar_management`：市場カレンダー判定と更新ジョブ

- ニュース収集 / NLP
  - `kabusys.data.news_collector.fetch_rss(...)`：RSS 取得・前処理
  - `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`：銘柄別ニューススコアを `ai_scores` テーブルへ書込
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`：市場レジーム判定（bull/neutral/bear）を `market_regime` テーブルへ書込

- 研究（Research）
  - `kabusys.research.calc_momentum/ calc_volatility/ calc_value`：ファクター計算
  - `kabusys.research.calc_forward_returns/ calc_ic/ factor_summary/ rank`：特徴量探索・評価
  - `kabusys.data.stats.zscore_normalize`：Zスコア正規化ユーティリティ

- 監査ログ（Audit）
  - `kabusys.data.audit.init_audit_db(db_path)`：監査ログ用 DuckDB DB 初期化（テーブル・インデックス作成）
  - `kabusys.data.audit.init_audit_schema(conn, transactional=False)`：既存接続へスキーマ追加

---

## セットアップ手順

必要な Python バージョン: 3.10 以上を推奨（型ヒントに | が使用されています）。

1. リポジトリをクローン、あるいはパッケージとしてインストール
   - 開発環境で編集する場合:
     - git clone ...
     - pip install -e .

2. 必要パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - そのほか標準ライブラリ以外の依存がある場合は requirements.txt を参照してください（プロジェクトに合わせて管理してください）。

   例（最低限）:
   pip install duckdb openai defusedxml

3. 環境変数 / .env の設定
   - プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化したい場合は環境変数をセット:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主な環境変数（README 用の抜粋）:
   - JQUANTS_REFRESH_TOKEN（必須）: J-Quants 用リフレッシュトークン
   - OPENAI_API_KEY（必須 for NLP）: OpenAI API キー
   - KABU_API_PASSWORD（必須）: kabuステーション API パスワード
   - KABU_API_BASE_URL（任意）: デフォルト http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須 if Slack 通知を使う場合）
   - DUCKDB_PATH（任意）: デフォルト data/kabusys.duckdb
   - SQLITE_PATH（任意）: デフォルト data/monitoring.db
   - KABUSYS_ENV（development|paper_trading|live）: 環境
   - LOG_LEVEL（DEBUG|INFO|...）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-xxxxxx
   KABU_API_PASSWORD=xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な使い方例）

以下は簡単なコードスニペット（Python REPL / スクリプト）です。実行前に環境変数を適切に設定してください。

- DuckDB 接続を開いて日次 ETL を実行する:
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- ニューススコアリングを実行（OpenAI API が必要）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))  # api_key を直接渡すことも可
  print("written scores:", written)
  ```

- 市場レジーム判定を実行:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAIキーは環境変数を使用
  ```

- 監査ログ用 DuckDB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 返却された conn を使って audit テーブルへ書き込み等を行う
  ```

- 研究用ファクター計算:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  mom = calc_momentum(conn, d)
  val = calc_value(conn, d)
  vol = calc_volatility(conn, d)
  ```

注意点:
- OpenAI を使う関数は api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants クライアントは rate limit（120 req/min）とトークン自動更新を実装しています。長時間のページネーションや大量取得でも制御されます。

---

## ディレクトリ構成（概要）

プロジェクトの主要ファイル・モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                # 環境変数・.env の読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLP（銘柄別スコア）
    - regime_detector.py     # 市場レジーム判定
  - data/
    - __init__.py
    - etl.py                 # ETL の公開インターフェース（ETLResult）
    - pipeline.py            # 日次 ETL パイプライン（prices/financials/calendar）
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - news_collector.py      # RSS ニュース収集・正規化
    - quality.py             # データ品質チェック
    - calendar_management.py # 市場カレンダーの管理・判定・更新ジョブ
    - stats.py               # 統計ユーティリティ（zscore 等）
    - audit.py               # 監査ログスキーマ初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     # Momentum / Value / Volatility 等の計算
    - feature_exploration.py # forward returns / IC / summary / rank

（上記は主なモジュール。詳細はソースツリーを参照してください）

---

## 運用上の注意・設計上のポイント

- ルックアヘッドバイアス対策:
  - 多くの関数は内部で datetime.today() / date.today() を参照せず、明示的な `target_date` 引数を使ってデータ抽出を行います。バックテストや再現性のため、target_date を明示することが推奨されます。
- フェイルセーフ:
  - OpenAI API や J-Quants API の失敗時には、フェイルセーフ（0.0 にフォールバック、ログ出力）で処理を継続する設計の箇所が多くあります。ただし、致命的な DB 書き込みエラー等は例外として伝播します。
- .env の自動読込:
  - プロジェクトルートが検出される場合、自動で `.env` と `.env.local` を読み込みます（OS 環境変数を保護）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- J-Quants の認証:
  - `get_id_token()` はリフレッシュトークンから ID トークンを取得します。モジュール内部でトークンをキャッシュし、401 を受けた場合は自動でリフレッシュしてリトライします。

---

## 貢献・拡張

- 新しい ETL 対象、ニュースソース、研究指標を追加する際は DuckDB による保存の冪等性や品質チェックの影響を考慮してください。
- OpenAI のプロンプトやモデルは定期的に評価・更新してください（レスポンス形式の厳格化が必要）。

---

以上。詳細な API や内部仕様は各モジュールのドキュメント（ソース内 docstring）を参照してください。質問や追加の README 内容（例: .env.example の完全なテンプレート、Dockerfile、CI 手順など）が必要であれば教えてください。