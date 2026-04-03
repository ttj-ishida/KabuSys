# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォームと自動売買・リサーチ用ライブラリ群です。J-Quants API からのデータ取得（ETL）、ニュース収集とAIによるセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）などを提供します。設計上、ルックアヘッドバイアスの回避、ETLの冪等性、API呼び出しのリトライ・レート制御、安全なRSS取得（SSRF対策）などに配慮しています。

主な特徴
- J-Quants API との連携（差分取得、ページネーション、トークン自動リフレッシュ、レート制御）
- DuckDB を用いた ETL / 永続化（raw_prices / raw_financials / market_calendar 等）
- ニュース収集（RSS）と前処理（URL除去・正規化・ID生成）および銘柄マッピング
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別 ai_scores, マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ（Zスコア等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ（signal / order_request / executions）と初期化ユーティリティ
- 設定管理モジュール（.env 自動読み込み、環境変数取得ラッパー）

サポートする想定環境
- Python 3.10 以上（| 型注釈、標準ライブラリの型仕様などを利用）
- DuckDB、OpenAI（openai パッケージ）、defusedxml など（詳細は下記）

機能一覧（概要）
- data.jquants_client: J-Quants API 取得/保存（daily quotes, financials, market calendar, listed info）
  - レート制御、リトライ、401 のトークンリフレッシュ対応
  - save_* 関数は DuckDB に冪等保存（ON CONFLICT）
- data.pipeline: 日次 ETL パイプライン（run_daily_etl）と個別 ETL（prices/financials/calendar）
  - ETLResult に処理サマリを返す
- data.quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
- data.news_collector: RSS 取得・前処理・記事ID生成・raw_news 保存補助
  - SSRF 対策、受信サイズ制限、XML パースの安全化（defusedxml）
- data.calendar_management: JPX カレンダー管理・営業日判定・next/prev_trading_day 等
- data.audit: 監査ログスキーマ定義と初期化（init_audit_schema / init_audit_db）
- data.stats: 汎用統計ユーティリティ（zscore_normalize）
- ai.news_nlp: ニュースの銘柄別センチメント生成（score_news）
- ai.regime_detector: ETF 1321 の MA とマクロニュースから市場レジームを判定（score_regime）
- research.*: ファクター計算・特徴探索（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic 等）
- config: .env 自動読み込み、必須環境変数の検査、設定プロパティ（settings オブジェクト）

セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール
   依存はプロジェクトによって変わりますが、主に以下を想定しています。
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

4. 環境変数の設定
   プロジェクトルートの .env / .env.local（推奨）に必要な値を設定します。config モジュールはプロジェクトルート（.git または pyproject.toml のある場所）を起点に自動で .env を読み込みます。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例 (.env):
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

   # OpenAI (score_news / score_regime)
   OPENAI_API_KEY=sk-...

   # kabuステーション API（利用する場合）
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # 実行環境
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO

   # DBパス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # オプション: LINE 通知
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```

   注意:
   - 必須の環境変数（呼び出す機能に依存）:
     - JQUANTS_REFRESH_TOKEN（J-Quants 連携）
     - OPENAI_API_KEY（AI スコアリングを使う場合）
     - KABU_API_PASSWORD（kabuステーションAPIを利用する場合）
   - settings オブジェクトは properties で値を取得するため、実行時に未設定だと ValueError を送出します。

使い方（基本例）

- DuckDB 接続と日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（1日分）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
  print("scored:", written)
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- ファクター計算（例: momentum）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records))
  ```

- 監査ログDBの初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- RSS の取得（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

設計・実装上の主な注意点
- ルックアヘッドバイアス回避：多くの関数は内部で現在時刻を直接参照せず、呼び出し元が target_date を明示します。
- 冪等性：ETL・保存処理はできる限り ON CONFLICT / DELETE→INSERT の形で冪等に実装されています。
- フェイルセーフ：AIや外部API呼び出しの失敗は通常フォールバック（0.0 やスキップ）して処理を継続します。ログで警告/エラーが出ます。
- セキュリティ：news_collector は SSRF 対策や defusedxml を用いた安全な XML パース、受信サイズ制限を実装しています。
- レート制御とリトライ：J-Quants クライアントは固定間隔のスロットリングと指数バックオフリトライ、401 のトークン自動リフレッシュを行います。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの銘柄別 AI スコアリング（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save 関数群）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS 収集・前処理・保存補助
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
- pyproject.toml / setup.cfg 等（プロジェクトに含まれる場合）
- .env.example（存在する場合は参考にしてください）

テスト・デバッグ
- OpenAI / J-Quants など外部 API 呼び出しはモック可能な設計（内部の _call_openai_api や HTTP呼び出しをパッチすることで単体テスト実行が容易です）。
- 設定管理は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます（テスト環境で便利）。

ライセンス / 貢献
- 本 README にライセンス情報が無い場合はリポジトリルートの LICENSE を参照してください。貢献はプルリクエスト & Issue を通じてお願いします。

補足
- この README はコードベース（src/kabusys 配下）を基に作成しています。追加の CLI、サンプルスクリプト、CI 設定や requirements.txt / pyproject.toml があればそれに応じてセットアップ手順を更新してください。

必要であれば、具体的な利用シナリオ（ETL の cron ジョブ化、戦略層からの発注フロー例、監視・アラート設定例）や、よく使う SQL スキーマの一覧・テーブル定義（raw_prices / raw_financials / market_calendar / ai_scores / market_regime / audit テーブル等）を README に追記します。どの情報を優先して追加しますか？