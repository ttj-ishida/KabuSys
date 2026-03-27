# KabuSys

日本株向けの自動売買およびデータ基盤ライブラリです。J-Quants からのデータ ETL、ニュース収集・NLP による銘柄別スコアリング、ファクター研究、監査ログ（発注→約定トレース）、および市場レジーム判定等の機能を提供します。

主な用途
- 日次 ETL（株価・財務・市場カレンダーの差分取得・保存・品質チェック）
- RSS ニュース収集と OpenAI を用いた銘柄別センチメント算出
- マーケットレジーム判定（ETF MA + マクロ記事センチメント）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ）と統計ユーティリティ
- 監査ログ（signal → order_request → executions）の管理（DuckDB）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- ディレクトリ構成（概観）
- 環境変数一覧・注意事項

---

プロジェクト概要
- 名前: KabuSys
- 想定対象: 日本株のデータ基盤・リサーチ・自動売買ワークフロー
- データストア: DuckDB（ローカルファイル）
- 外部 API:
  - J-Quants（株価・財務・市場カレンダー等）
  - OpenAI（ニュースのセンチメント解析 / market regime）
  - kabuステーション（発注） — 設定箇所あり
  - Slack（通知）
- 設計方針:
  - ルックアヘッドバイアス回避（バックテスト用に日付扱いに注意）
  - 冪等性重視（DB 保存は ON CONFLICT などで上書き）
  - フェイルセーフ（API エラー時はスキップやデフォルト値で継続）

---

機能一覧
- データ（kabusys.data）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save / 認証・リトライ・レート制御）
  - カレンダー管理（営業日判定・next/prev/get_trading_days・calendar_update_job）
  - ニュース収集（RSS → raw_news、SSRF 対策、前処理）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化・DB（signal_events / order_requests / executions）
- AI（kabusys.ai）
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) MA とマクロ記事センチメントを合成して market_regime に書き込む
- 研究（kabusys.research）
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
- 共通ユーティリティ
  - 設定管理（kabusys.config.settings）
  - 統計ユーティリティ（zscore_normalize）

---

セットアップ手順（ローカル開発向け）
前提
- Python 3.10 以上（typing の union 表記や annotations の利用を想定）
- ネットワークアクセス（J-Quants / OpenAI）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows (PowerShell)
   ```

3. 必要パッケージをインストール
   （実プロジェクトでは requirements.txt / pyproject.toml を用意してください。以下は主要依存の例）
   ```
   pip install duckdb openai defusedxml
   pip install -e .
   ```
   - duckdb: データ保存・SQL 処理
   - openai: OpenAI API 呼び出し（gpt-4o-mini 等）
   - defusedxml: RSS パースの安全化

4. 環境変数 / .env を準備
   プロジェクトルートに .env を作成すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   必須の環境変数（例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   ```
   任意・デフォルト
   ```
   KABUSYS_ENV=development           # development | paper_trading | live
   LOG_LEVEL=INFO
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. DuckDB（監査用など）初期化例
   ```py
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # audit 用 DB を作成してスキーマを初期化
   conn.close()
   ```

---

使い方（主要機能の簡単な例）

- 設定値を取得
  ```py
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- 日次 ETL を実行
  ```py
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  conn.close()
  ```

- ニュースセンチメント算出（ai.score_news）
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None => OPENAI_API_KEY を参照
  print("scored codes:", count)
  conn.close()
  ```

- 市場レジーム判定（ai.regime_detector）
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  conn.close()
  ```

- 研究用ファクター（例: momentum）
  ```py
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records))
  conn.close()
  ```

- カレンダー判定（例）
  ```py
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  conn.close()
  ```

- RSS フェッチ（ニュース収集の低レベルユーティリティ）
  ```py
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["title"], a["datetime"])
  ```

---

環境変数一覧（主要）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY (必須 for AI functions): OpenAI API キー
- KABU_API_PASSWORD (必須 if using kabu API): kabuAPI のパスワード
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (必須 if using Slack notifications)
- DUCKDB_PATH: デフォルトの duckdb ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（挙動制御）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化します（テスト等で便利）。

---

注意事項 / 運用上のポイント
- OpenAI 呼び出しは API レートやコストがかかります。API キー管理は厳重に行ってください。
- J-Quants API はレート制限があり、クライアント側で固定間隔のスロットリングとリトライを行っています。大量取得は注意。
- DuckDB の executemany はバージョン差異に依存する挙動があるため、空パラメータの実行を避ける実装になっています（pipeline 等のコード参照）。
- 監査ログは削除しない想定です。schema 初期化や移行は慎重に行ってください。
- ルックアヘッドバイアス防止のため、各モジュールは明示的に target_date を受け取り、内部で date.today() を安易に参照しない設計になっています。バックテストではこの点に注意して使用してください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                - パッケージ定義、バージョン
  - config.py                  - 環境変数 / 設定管理（自動 .env 読込）
  - ai/
    - __init__.py
    - news_nlp.py              - ニュースの OpenAI によるスコアリング pipeline
    - regime_detector.py       - 市場レジーム判定（ETF MA + マクロ記事）
  - data/
    - __init__.py
    - jquants_client.py        - J-Quants API クライアント（fetch/save, 認証）
    - pipeline.py              - 日次 ETL パイプライン（run_daily_etl 等）
    - etl.py                   - ETL 型の再エクスポート（ETLResult）
    - news_collector.py        - RSS 収集・前処理・SSRF 対策
    - calendar_management.py   - 市場カレンダー・営業日判定
    - quality.py               - データ品質チェック
    - stats.py                 - zscore_normalize 等の統計ユーティリティ
    - audit.py                 - 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py       - momentum/value/volatility ファクター計算
    - feature_exploration.py   - 将来リターン / IC / 統計要約
  - monitoring/ (存在する場合: モニタリング関連)
  - execution/ (発注関連: kabu 連携等。コードベースの別モジュールと想定)

各モジュールは docstring に設計方針・処理フロー・フェイルセーフ動作の説明が書かれています。実装の利用時は docstring を参照してください。

---

開発・拡張のヒント
- テスト時は環境変数の自動読み込みを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化し、モックを使って API 呼び出しを差し替えてください。
- OpenAI 呼び出し部分は _call_openai_api をモック可能な設計（unittest.mock.patch 対応）になっています。
- J-Quants の ID トークンはモジュール内でキャッシュされ、401 時に自動リフレッシュされます。テストでは get_id_token を差し替えるとよいです。

---

ライセンスやその他のメタ情報はリポジトリのルートにあるファイル（LICENSE / pyproject.toml / .github 等）を参照してください。

何か特定の利用例（例: バックテストとの連携、kabu API 呼び出しフロー、Slack 通知の実装例）を README に追記したい場合は、用途を教えてください。必要に応じてサンプルコードを追加します。