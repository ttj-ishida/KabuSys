KabuSys
=======

日本株向けの自動売買／データ基盤ライブラリ（部分実装）。
このリポジトリはデータ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、
市場レジーム判定、ファクター計算、監査ログなどを備えた研究／運用向けのユーティリティ群を提供します。

主な目的
- J-Quants からの株価・財務・カレンダー等の差分ETL
- ニュース記事の収集と LLM を用いた銘柄センチメント評価
- ETF とマクロニュースを組み合わせた市場レジーム判定
- ファクター計算・特徴量探索・IC 等の研究ユーティリティ
- ETL 品質チェック、監査ログ用スキーマの初期化

機能一覧
- 設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可）
  - 必須環境変数の取得ラッパー（settings オブジェクト）
- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API からの差分取得（株価、財務、マーケットカレンダー）
  - レートリミット・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT で更新）
  - run_daily_etl による一括 ETL + 品質チェック
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合などを検出して QualityIssue を返却
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - JPX カレンダーの夜間更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事取得（SSRF対策、サイズ制限、トラッキング除去）
  - 記事ID の生成・前処理ユーティリティ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化関数
  - init_audit_schema / init_audit_db
- AI（kabusys.ai）
  - news_nlp.score_news: 銘柄別ニュースを LLM（gpt-4o-mini 想定）でスコアリングして ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して market_regime に保存
  - OpenAI 呼び出しはリトライやフェイルセーフを備える
- 研究ユーティリティ（kabusys.research）
  - calc_momentum / calc_value / calc_volatility: ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank: 特徴量探索・評価
- 汎用統計（kabusys.data.stats）
  - zscore_normalize（クロスセクション Z スコア正規化）

セットアップ手順（ローカル開発向け）
1. 必要な Python バージョンを用意（推奨: 3.10+）
2. リポジトリをクローンして editable インストール
   - python -m pip install -e .
3. 依存パッケージ（主なもの）
   - duckdb
   - openai
   - defusedxml
   - （その他: 標準ライブラリで実装されている部分が多いですが、requirements.txt があればそちらを利用してください）
4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env と .env.local を自動読み込みします。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時等）。
   - 代表的な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を実行する場合に必要）
     - KABU_API_PASSWORD: kabuステーション API を使う場合のパスワード
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知を行う場合
     - DUCKDB_PATH: デフォルトの DuckDB ファイルパス（data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 sqlite3 DB パス（data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG/INFO/...
   - .env のパースはシェル風（export プレフィックス、引用符、コメント）に対応します。

使い方（簡単なコード例）
- DuckDB に接続して ETL を回す（日次 ETL）
  ```py
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- news_nlp によるニューススコア付与（ai_scores に書き込む）
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from os import environ

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数または関数引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=environ.get("OPENAI_API_KEY"))
  print("scores written:", n_written)
  ```

- 市場レジーム判定
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 研究用ファクター計算
  ```py
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(momentum), "records")
  ```

- 監査ログ DB の初期化
  ```py
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
  ```

注意点 / 前提
- DuckDB スキーマ
  - モジュール群は以下のようなテーブルを前提に動作します（用途により差分あり）:
    - raw_prices, raw_financials, market_calendar（ETL 保存先）
    - prices_daily（研究用に整形された日次価格テーブル。ETL 側で別途作成される前提）
    - raw_news, news_symbols, ai_scores（ニュース収集 / NLP スコア）
    - market_regime（regime_detector の出力）
    - signal_events, order_requests, executions（監査ログ）
  - 実行前に必要なテーブルスキーマが作成されていることを確認してください。audit.init_audit_schema は監査スキーマの初期化を提供します。
- Look-ahead バイアス対策
  - AI スコア・レジーム判定・ETL は日時の扱いでルックアヘッドバイアスを避ける設計（target_date 未満／排他条件や fetched_at の記録）になっています。バックテスト等で使用する際は取り扱いに注意してください。
- OpenAI / ネットワーク呼び出し
  - news_nlp・regime_detector は OpenAI に依存します。API 呼び出しはリトライ・フェイルセーフ（失敗時はスコアを 0 にフォールバックなど）を備えますが、API キーは必須です。
- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動で読み込みます。テストで自動読込を無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                 - パッケージ定義（version 等）
  - config.py                   - 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py               - ニュースの LLM センチメントスコア付与
    - regime_detector.py        - ETF + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py         - J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py               - 日次 ETL パイプライン（run_daily_etl, 個別 ETL）
    - etl.py                    - ETLResult の公開ラッパー
    - news_collector.py         - RSS 取得・前処理ユーティリティ
    - calendar_management.py    - マーケットカレンダー管理・営業日ロジック
    - quality.py                - データ品質チェック（QualityIssue）
    - stats.py                  - 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                  - 監査ログスキーマ初期化（signal/order/execution テーブル）
  - research/
    - __init__.py
    - factor_research.py        - Momentum/Value/Volatility などのファクター計算
    - feature_exploration.py    - forward returns / IC / summary / rank 等
  - (将来的に strategy/execution/monitoring 等のモジュールが追加される想定)

貢献・拡張
- モジュール設計はテストで差し替え可能な内部関数（例: API 呼び出しラッパー）を持つため、ユニットテストの作成やモック差し替えが容易です。
- 実運用での発注（kabu ステーション）や Slack 通知は設定変数を通して統合できます。必要に応じて strategy / execution 層を追加してください。

ライセンス / 著作権
- この README はコードベースの説明を目的としたものであり、実際の運用前に必ずコードの内容、テーブルスキーマ、環境変数や API の利用制限を確認してください。

補足（よくある質問）
- Q: OpenAI のレスポンスパースに失敗したらどうなる？
  - A: 各モジュールは JSON パース失敗や API エラー時に警告を出し、スコアは安全側（0.0 等）にフォールバックするよう設計されています（例外を呼び出し元に投げない処理が基本）。
- Q: .env の書式はどの程度柔軟？
  - A: export プレフィックスやシングル／ダブルクオート、行末コメント（スペース前の #）などを考慮したパーサを実装しています。

以上。必要であれば README に含める具体的な .env.example、SQL スキーマ DDL、または簡単な CLI / サンプルスクリプトのテンプレートを追加します。どの情報を追記しますか？