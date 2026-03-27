# KabuSys

日本株向け自動売買 / データ基盤ライブラリ

概要
- KabuSys は日本株のデータ収集（J-Quants）、ETL、データ品質チェック、特徴量計算、ニュース NLP（LLM を用いたセンチメント）、市場レジーム判定、監査ログなどを備えたパッケージです。
- DuckDB をデータストアに使用し、J-Quants API / RSS / OpenAI（gpt-4o-mini など）を連携して日次バッチや研究用解析を行えます。
- バックテストや本番（paper/live）環境を想定した設計方針（ルックアヘッドバイアス回避、冪等性、フェイルセーフ等）に基づいて実装されています。

主な機能
- データ取得・ETL
  - J-Quants から株価日足・財務データ・市場カレンダーを差分取得・保存（ページネーション対応／リトライ／レート制御）。
  - ETL の一括実行（run_daily_etl）と個別ジョブ（prices / financials / calendar）。
- データ品質チェック
  - 欠損（OHLC）／重複／日付不整合／スパイク検出を行うチェック群と QualityIssue 表現。
- ニュース収集・前処理
  - RSS 取得（SSRF 対策・受信サイズ制限・トラッキングパラメータ除去）、raw_news への永続化補助。
- ニュース NLP（LLM）
  - 銘柄ごとのニュースを LLM でまとめてスコア化し ai_scores に書き込む（score_news）。
  - LLM 呼び出しはバッチ処理・JSON Mode・リトライ・レスポンス検証あり。
- 市場レジーム判定
  - ETF（1321）200 日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム（bull/neutral/bear）を算出・保存（score_regime）。
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター算出、将来リターン計算、IC（Information Coefficient）や統計サマリー、Z スコア正規化等。
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を中心に発注フローを完全にトレースする監査スキーマの初期化（init_audit_schema / init_audit_db）。
- 環境設定
  - .env / .env.local 自動読み込み（プロジェクトルート検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

セットアップ手順（開発向け）
1. Python バージョン
   - Python 3.10+ を推奨（typing 機能を多用）。
2. インストール（ローカル開発）
   - パッケージルートで:
     ```
     python -m pip install -e .
     ```
   - または requirements.txt / pyproject.toml に従って依存をインストールしてください。
   - 主な必須外部依存:
     - duckdb
     - openai (OpenAI SDK)
     - defusedxml
     - （標準ライブラリ以外が必要な場合は pyproject.toml を参照）
3. 環境変数
   - 必須:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN、SLACK_CHANNEL_ID : Slack 通知が必要な場合
     - KABU_API_PASSWORD : kabu ステーション API を使う場合
   - 任意／AI 関連:
     - OPENAI_API_KEY : OpenAI を使う処理（score_news / score_regime 等）
   - システム設定:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - DUCKDB_PATH / SQLITE_PATH : データベースファイルパスの上書き
   - .env 自動ロードについて:
     - パッケージはプロジェクトルート（.git か pyproject.toml）を基に .env と .env.local を自動で読み込みます。
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効にできます（テスト時に便利）。
4. DB 初期化（監査テーブルなど）
   - 監査ログ用に DuckDB を初期化する例:
     ```py
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db

     conn = init_audit_db(settings.duckdb_path)
     ```
   - 他のスキーマ初期化はプロジェクトのスキーマ管理機能に従ってください（data.schema などの補助モジュールがある想定）。

基本的な使い方（例）
- DuckDB 接続を作る:
  ```py
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```
- 日次 ETL を実行する:
  ```py
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```
- ニュースのセンチメントスコア取得（LLM）:
  ```py
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY が環境に設定されていること
  count = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {count} codes")
  ```
- 市場レジーム判定:
  ```py
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```
- 監査スキーマ初期化（トランザクションあり）:
  ```py
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

環境変数の注意点
- 必須の環境変数が未設定の場合、設定参照で ValueError が発生します（settings.jquants_refresh_token 等）。
- .env / .env.local はプロジェクトルートに置き、.env.local は .env をオーバーライドします（ただし OS 環境変数は保護されます）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py (パッケージ情報)
  - config.py (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py (ニュース NLP（score_news）)
    - regime_detector.py (市場レジーム判定（score_regime）)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、取得 & DuckDB への保存)
    - pipeline.py (ETL パイプライン・run_daily_etl 等)
    - etl.py (ETL 型の再エクスポート)
    - calendar_management.py (マーケットカレンダー操作)
    - news_collector.py (RSS 取得・前処理)
    - quality.py (データ品質チェック)
    - stats.py (汎用統計ユーティリティ)
    - audit.py (監査ログスキーマ初期化・init_audit_db)
  - research/
    - __init__.py
    - factor_research.py (calc_momentum / calc_value / calc_volatility)
    - feature_exploration.py (calc_forward_returns / calc_ic / factor_summary / rank)
  - ai/regime_detector.py、ai/news_nlp.py は OpenAI 呼び出しを行います（テスト用に _call_openai_api を差し替え可能）。
  - 他モジュールはドメインロジック（DuckDB SQL 実行）を中心に実装されています。

設計上の重要ポイント（簡易リスト）
- ルックアヘッドバイアス回避: 内部処理は date や接続から明示的に時刻を決め、datetime.now()/today() を直接参照しない設計が基本（関数引数で target_date を受け取る形）。
- 冪等性: ETL / 保存処理は ON CONFLICT DO UPDATE を多用し、部分的な再実行に耐える。
- フェイルセーフ: 外部API失敗時は部分的にスキップして継続する設計（重大エラーのみ上位へ伝播）。
- セキュリティ: RSS 収集での SSRF 対策、defusedxml を用いた XML パース、HTTP レスポンスサイズ制限等を実装。

よくある運用例
- 毎晩のバッチ（cron / Airflow / GitHub Actions 等）で run_daily_etl を実行しデータを補充。
- 研究用に research モジュールでファクターを算出 → zscore_normalize → シグナル生成。
- ニュースの夜間収集 → score_news を回して ai_scores を更新 → 翌朝の戦略で参照。
- score_regime を日次で実行し、市場状況に応じたリスク制御（戦略の切替）を行う。

トラブルシューティング
- .env が読み込まれない場合:
  - プロジェクトルート検出は __file__ の親ディレクトリを上がって `.git` または `pyproject.toml` を探します。配布形態によっては該当が見つからず自動ロードがスキップされることがあります。その場合は明示的に環境変数を設定してください。
  - 自動ロードを無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- OpenAI 関連:
  - API 呼び出しはリトライや 5xx / 429 のバックオフ処理がありますが、API キーが未設定だと ValueError が発生します。テストでは _call_openai_api をモックしてください。
- J-Quants:
  - レート制限や 401 リフレッシュ処理が組み込まれています。JQUANTS_REFRESH_TOKEN を正しく設定してください。

ライセンス / 貢献
- この README はコードベースに含まれた設計情報から生成されています。実際のライセンス・貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。

以上が KabuSys の概要・導入・使い方の要点です。追加でサンプルスクリプトや運用例（Airflow DAG 例、Dockerfile、CI 設定など）をご希望であれば教えてください。