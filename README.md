# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ KabuSys のコードベース用 README。

この README はリポジトリ内の実装（src/kabusys）を元に、プロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買（アルゴリズム取引）およびデータプラットフォーム向けの内部ライブラリです。  
主に以下を提供します。

- J-Quants API からのデータ取得（株価・財務・カレンダー）および DuckDB への ETL
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント分析（銘柄別 ai_score）やマクロセンチメントを用いた市場レジーム判定
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を保存する監査スキーマ
- 設定管理（.env 自動ロード）と実行環境判定

設計上、バックテストでのルックアヘッドバイアスを防ぐために日時取得や DB クエリに注意が払われています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch/save daily_quotes, financials, market_calendar）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days）
  - ニュース収集（RSS を安全に取得・正規化し raw_news に保存する）
  - データ品質チェック（missing_data, spike, duplicates, date_consistency）
  - 監査ログテーブルの初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp: 銘柄ごとのニュースを統合して AI にセンチメント評価を依頼し ai_scores に書き込む（score_news）
  - regime_detector: ETF（1321）MA200乖離とマクロニュースセンチメントを合成して市場レジーム判定（score_regime）
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）計算、ファクターサマリ等
- config.py
  - .env ファイルの自動読み込み（プロジェクトルート検知）と Settings オブジェクトによる環境変数アクセス
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可

その他：DuckDB を中心に設計されており、監視用 DB（SQLite）等のパスは設定で指定可能。

---

## セットアップ手順

以下は開発環境での一般的な導入手順の例です。

1. リポジトリを取得（例）:
   git clone <repo-url>

2. Python 仮想環境を作成・有効化:
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール（requirements ファイルがある場合はそちらを使用してください）。代表的な依存例:
   pip install duckdb openai defusedxml

   ※ 実プロジェクトでは additional dependency（requests 等）がある場合があります。requirements.txt があればそちらを使用してください。

4. 環境変数（.env）を用意する
   リポジトリルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

   必須となる主な環境変数（コード中で _require によって参照されるもの）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード（発注連携がある場合）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack 通知先チャネル ID

   任意 / デフォルト付き:
   - KABUSYS_ENV (development | paper_trading | live) — default: development
   - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
   - DUCKDB_PATH — default: data/kabusys.duckdb
   - SQLITE_PATH — default: data/monitoring.db
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, LOG_LEVEL 等

   サンプル .env（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB データベース初期化（任意）
   監査ログ用 DB 初期化例は下記「使い方」を参照してください。

---

## 使い方（基本例）

以下は Python スクリプト / インタラクティブでの利用例です。利用前に必要な環境変数（JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY など）を設定してください。

- 共通: DuckDB 接続を作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行 (価格・財務・カレンダーの差分取得と品質チェック)
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定しなければ今日が対象（内部で営業日調整を実施）
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースの AI スコア付与（ai_scores への書き込み）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OpenAI API キーは環境変数 OPENAI_API_KEY を使うか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB 初期化（監査テーブルを別 DB に分けたい場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn をアプリケーションの監査処理で使う
  ```

- 監査スキーマを既存接続に追加
  ```python
  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn, transactional=True)
  ```

- ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  recs = calc_momentum(conn, target_date=date(2026,3,20))
  # recs は [{"date": ..., "code": "xxx", "mom_1m": ..., ...}, ...]
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意: 上記の多くは外部 API（J-Quants、OpenAI）、RSS フィード、ネットワーク等に依存します。実行前にそれらの資格情報とネットワーク接続が必要です。

---

## 環境変数自動読み込みについて

- config.py はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、そのルートにある `.env` と `.env.local` を自動で読み込みます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

---

## ディレクトリ構成（抜粋）

リポジトリの主要モジュール構造（src/kabusys 配下）:

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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - (その他: モジュール毎に ETL / 保存 / ユーティリティを提供)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (コードベースに含まれる場合は監視関連モジュール)
  - strategy/ (戦略・シグナル生成の実装を置く想定)
  - execution/ (ブローカー接続・発注ロジックを置く想定)
  - data/（上で示した ETL / clients 等）

（実際のツリーはリポジトリの内容に依存します。上は主要ファイルの抜粋です）

---

## 開発上の注意点 / 設計上のポイント

- ルックアヘッドバイアス対策: 各種関数は date / target_date を引数に取り、内部で現在日時を参照しないように設計されています。バックテストや再現性に配慮しています。
- DuckDB を中心に設計: データは DuckDB に保存され、SQL と Python を組み合わせて効率的に処理します。
- 冪等性: J-Quants の保存処理や監査テーブルの初期化、AI スコアの書き込み等は冪等化（ON CONFLICT / DELETE→INSERT による差し替え）されています。
- ネットワーク安全対策: RSS 収集時の SSRF 防止、受信サイズ検査、defusedxml を使った XML パース等の安全対策が実装されています。
- 外部 API 呼び出しにはリトライ・バックオフ・レートリミットが組み込まれています。

---

## よくある操作例（チェックリスト）

- ETL を定期実行するには:
  - 必要な環境変数（JQUANTS_REFRESH_TOKEN 等）を設定
  - cron / systemd timer などでスクリプトを日次実行。run_daily_etl を呼び出す。
- OpenAI を使う処理（score_news, score_regime）を動かすには:
  - OPENAI_API_KEY を環境変数に設定（または関数引数で渡す）
- 監査ログを有効にするには:
  - init_audit_schema を実行して監査用テーブルを作成

---

## ライセンス・貢献

この README はコードベースの説明用に自動生成された要約です。実際の利用・配布に関してはリポジトリに含まれる LICENSE ファイルや貢献ガイドライン（CONTRIBUTING.md）があればそちらに従ってください。

---

README の補足や、特定モジュール（例: jquants_client の使い方、news_collector の RSS ソース追加方法、監査テーブルのスキーマ詳細）について詳しい説明を希望される場合は、どのセクションを掘り下げるか教えてください。