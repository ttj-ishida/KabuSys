# KabuSys

日本株向けのデータプラットフォーム兼自動売買（リサーチ／ETL／監査／AI支援）ライブラリです。  
DuckDB を中心にデータを保持し、J-Quants API からのデータ取り込み、ニュース収集・NLP、ファクター計算、監査ログ管理、ETL の統合処理などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（target_date を明示して処理）
- DuckDB をデータ層に採用（ローカルで高速に分析）
- API 呼び出しはリトライ・レート制御など堅牢に実装
- ETL や監査は冪等（idempotent）に設計

---

## 機能一覧

- データ取得 / ETL
  - J-Quants からの株価日足、財務情報、上場情報、マーケットカレンダー取得（jquants_client）
  - 差分取得・バックフィル・品質チェックを含む日次ETL（data.pipeline.run_daily_etl）
- ニュース収集・NLP
  - RSS フィードからの記事収集・前処理（data.news_collector）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント計測（ai.news_nlp.score_news）
  - マクロニュース＋ETF MA を組み合わせた市場レジーム判定（ai.regime_detector.score_regime）
- リサーチ / ファクター処理
  - モメンタム・バリュー・ボラティリティ等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（情報係数）算出、統計サマリー（research.feature_exploration）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などの検査（data.quality）
- 監査 / トレーサビリティ
  - signal → order_request → execution までの監査テーブル定義・初期化（data.audit）
- 設定管理
  - .env / .env.local / OS 環境変数の自動読み込み（config.Settings）

---

## セットアップ手順

前提：
- Python 3.10+
- system に DuckDB 用のバイナリが入る（pip で duckdb がインストールされます）
- OpenAI API を利用する場合は API キーを用意

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e ".[dev]"   # 依存に extras がある場合。なければ pip install -e .
   ```
   必要な主要ライブラリ（例）：duckdb, openai, defusedxml

2. 環境変数の準備
   プロジェクトルートに `.env`（およびローカル上書き用に `.env.local`）を置くと自動で読み込まれます（config モジュールが .git または pyproject.toml を起点にルートを探索）。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須やデフォルトは実装参照）：
   - JQUANTS_REFRESH_TOKEN （必須）: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD （必須）: kabu ステーション API パスワード
   - OPENAI_API_KEY （AI機能を使う場合必須）: OpenAI API Key
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID （通知などに利用）
   - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH （監視用 DB、デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH（Paper Trading 用設定）
   - PID_FILE_PATH / KILL_FLAG_PATH など監視系設定

3. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な例）

以下はライブラリ内の関数を Python から呼ぶ例です。実行環境では必要な環境変数を設定してください。

- DuckDB 接続を作って ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print("written:", n_written)
  ```

- 市場レジームを判定して market_regime に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査用 DuckDB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- RSS を取得（ニュースコレクタの一部を直接使う）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点：
- AI系（score_news / score_regime）は OpenAI API を用いるため API キーと通信環境が必要です。失敗時はフェイルセーフ（スコア0など）となるよう実装されていますが、API利用制限・料金に注意してください。
- run_daily_etl 等は内部で calendar ETL → prices ETL → financials ETL → 品質チェックの順に実行します。個別実行も可能です（run_prices_etl 等）。

---

## .env と設定の詳細

config.Settings により環境変数を抽象化して取得できます。主要項目（抜粋）：
- jquants_refresh_token: JQUANTS_REFRESH_TOKEN（必須）
- kabu_api_password: KABU_API_PASSWORD（必須）
- kabu_api_base_url: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- line_channel_access_token / line_user_id
- duckdb_path: DUCKDB_PATH（既定 data/kabusys.duckdb）
- sqlite_path: SQLITE_PATH（監視用 DB）
- paper_fill_mode: PAPER_FILL_MODE（instant/partial/never/reject）
- paper_sqlite_path: PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- pid_file_path / kill_flag_path / kill_flag_clear_on_start / cpu/memory/disk thresholds
- KABUSYS_ENV: development / paper_trading / live

自動読み込みの挙動：
- OS 環境 > .env.local > .env の優先順位で読み込まれます。
- プロジェクトルート検出は __file__ を基準に .git または pyproject.toml を探します。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py             — 環境変数 / 設定管理（.env 自動読み込み、Settings）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースのバッチセンチメント（score_news）
    - regime_detector.py  — ETF MA + マクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得・保存関数、レート制御）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult 再エクスポート
    - news_collector.py   — RSS 収集・前処理
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py          — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py            — 監査ログスキーマの初期化 / init_audit_db
    - stats.py            — 汎用統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py  — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - research/ .. other research utilities

各モジュールは docstring に設計方針や処理フローが詳細に書いてあるため、実装の理解や拡張時に参照してください。

---

## 開発・テスト

- テストを行う際は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env 自動読み込みが抑制されテストの再現性を保ちやすくなります。
- OpenAI / J-Quants 呼び出し部分は内部で分離されており、ユニットテストでは各モジュールの `_call_openai_api` や jquants_client の HTTP 呼び出しをモックしてテスト可能です。
- DuckDB の ':memory:' を使うことでインメモリ DB を用いた高速テストが可能です（例: init_audit_db(":memory:")）。

---

## ライセンス / 貢献

リポジトリに LICENSE や CONTRIBUTING.md があればそちらを参照してください。外部 API（J-Quants / OpenAI）利用時は各サービスの利用規約を遵守してください。

---

README の補足や具体的な CLI / CI / サンプルワークフロー（ETL cron、監視、Paper Trading 実行等）が必要であれば、用途に合わせた追加ドキュメントを作成します。どの部分の詳細が必要か教えてください。