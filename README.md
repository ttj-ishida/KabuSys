# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants）、ニュース収集、AI によるニュース/市場レジーム解析、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）など、トレーディングシステムで必要な機能群を提供します。

## プロジェクト概要
- データ取得: J-Quants API から株価日足・財務データ・JPX カレンダー等を差分取得して DuckDB に保存する ETL パイプラインを実装。
- ニュース: RSS ベースのニュース収集と前処理、銘柄紐付けを行うニュースコレクタ。
- AI: OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント（ai_scores）と市場レジーム判定（market_regime）モジュール。
- 研究用ユーティリティ: ファクター計算、将来リターン、IC（Information Coefficient）などを提供。
- 品質管理: データ品質チェック（欠損、重複、スパイク、日付不整合）。
- 監査ログ: シグナル → 発注 → 約定 までのトレーサビリティ用テーブル・初期化ユーティリティ。

## 主な機能一覧
- dataパッケージ
  - ETL（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants API クライアント（取得 + DuckDB への冪等保存）
  - market_calendar 操作・営業日判定（is_trading_day, next_trading_day 等）
  - news_collector（RSS 取得・前処理・保存）
  - quality（データ品質チェック）
  - audit（監査テーブルの初期化 / init_audit_db）
  - stats（zscore_normalize 等）
- aiパッケージ
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
- researchパッケージ
  - factor_research（calc_momentum, calc_value, calc_volatility）
  - feature_exploration（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - Settings（環境変数をラップ。settings オブジェクト経由でアクセス）
  - 自動 .env ロード（プロジェクトルートの `.env` / `.env.local` を読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）

## セットアップ手順（開発/利用者向け）
以下は推奨手順の例です。プロジェクトのパッケージ配布状態により適宜調整してください。

1. Python 環境を用意
   - Python 3.9+ を推奨

2. 必要パッケージをインストール
   - 最低限の依存（コード中で利用されている主なライブラリ）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

3. 環境変数 / .env の用意
   - 必須（config.Settings により参照／必須とされているもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード（発注等で使用）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必要に応じて）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必要に応じて）
   - 推奨/オプション
     - OPENAI_API_KEY — OpenAI API キー（ai モジュールで利用、関数呼び出し時に api_key を渡すか本環境変数を設定）
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - KABUSYS_ENV — {development, paper_trading, live}（デフォルト development）
     - LOG_LEVEL — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト INFO）
   - 簡単な .env.example（プロジェクトルートに置くと自動ロードされます）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動ロードはプロジェクトルート（.git または pyproject.toml が存在）基準で .env → .env.local の順で実行されます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. データベース初期化（監査テーブルなど）
   - 監査ログ専用 DB を初期化する例:
     ```python
     import duckdb
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db

     # settings.duckdb_path は Path オブジェクト
     conn = init_audit_db(settings.duckdb_path)  # または別パスを指定
     ```
   - 注意: init_audit_db はデータベースファイルの親ディレクトリを自動作成します（":memory:" も可）。

## 使い方（代表的な API）
以下は簡単な利用例です。すべての API は duckdb.DuckDBPyConnection を受け取る設計です。

1. DuckDB 接続を作る
   ```python
   import duckdb
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   ```

2. 日次 ETL を実行（カレンダー／株価／財務の差分取得と品質チェック）
   ```python
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn, target_date=None)  # target_date を指定可能
   print(result.to_dict())
   ```

3. ニュースセンチメントスコアを取得して ai_scores に書き込む
   ```python
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   # api_key を直接渡すか、OPENAI_API_KEY 環境変数を設定
   written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
   print(f"書き込み銘柄数: {written}")
   ```

4. 市場レジーム判定（ma200 と マクロニュース（LLM）を合成）
   ```python
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
   # market_regime テーブルに結果が保存されます
   ```

5. ファクター計算 / 研究用ユーティリティ
   ```python
   from datetime import date
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

   t = date(2026, 3, 20)
   mom = calc_momentum(conn, t)
   val = calc_value(conn, t)
   vol = calc_volatility(conn, t)
   fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
   ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
   ```

6. データ品質チェック
   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=None)
   for it in issues:
       print(it)
   ```

## よく使う設定 / 環境変数
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（ai の使用時）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH / SQLITE_PATH: データベースパス（defaults: data/kabusys.duckdb, data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

## ディレクトリ構成（抜粋）
src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/*：ファクター計算・特徴量探索ユーティリティ

各モジュールの役割は上記「主な機能一覧」を参照してください。

## 注意事項 / 実運用上のポイント
- Look-ahead バイアス対策
  - 多くのモジュールが datetime.today()/date.today() を内部で参照せず、関数呼び出し時に target_date を明示することでバックテストでのルックアヘッドを避ける設計です。
- OpenAI 呼び出し
  - ai モジュールは OpenAI API を呼びます。API キーの取り扱いやレート制限に注意してください。API 呼び出しはリトライやフォールバック（失敗時は 0.0 など）を組み込んで安全側で動作します。
- J-Quants API
  - レート制限（120 req/min）を守るため RateLimiter を実装しています。get_id_token が必要です（JQUANTS_REFRESH_TOKEN を設定）。
- DuckDB 互換性
  - 一部の SQL バインド / executemany の挙動は DuckDB バージョン差に依存する可能性があります（空リストの executemany 等）。
- セキュリティ
  - news_collector は SSRF 対策、XML の DefusedXML、レスポンスサイズ上限などを実装しています。

## サポート / 拡張
- 新しいデータソースやモデルを追加する場合、既存の ETL / save_* 関数と同様に「取得 → 変換 → 保存（冪等）」のパターンに従うことを推奨します。
- テスト時: 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。OpenAI 呼び出し等は unittest.mock で差し替え可能なように設計されています（内部の _call_openai_api をモックするなど）。

---

何か特定のモジュールについて詳しい使い方やサンプル（例: ETL スケジュール、ニュース収集パイプライン、監査テーブル設計に関する運用指針）を追加で作成しましょうか？