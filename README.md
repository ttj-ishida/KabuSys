# KabuSys — 日本株自動売買基盤 (README)

概要
---
KabuSys は日本株のデータ収集、品質管理、機械学習/ファクター研究、ニュース NLP、そして市場レジーム判定や監査ログ管理までを含むオールインワンの自動売買基盤ライブラリです。DuckDB をデータレイヤに使い、J-Quants / RSS / OpenAI（LLM）など外部データソースと連携して、ETL → 品質チェック → 研究 → 実行/監視までのワークフローを提供します。

主な設計方針
- ルックアヘッドバイアス防止（内部で datetime.today() を不適切に参照しない）
- DuckDB ベースで高パフォーマンスな SQL 処理
- 外部 API 呼び出しに対する堅牢なリトライ／フェイルセーフ設計
- 冪等性（ETL / 保存処理は ON CONFLICT / upsert により安全）
- テスト容易性（API 呼び出し部の差し替えが可能）

機能一覧
---
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（無効化可能）
  - 必須変数チェックと型変換ユーティリティ
- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants からの株価・財務・マーケットカレンダー差分取得（ページネーション対応）
  - DuckDB への冪等保存（save_* 関数）
  - ETL の集約エントリ（run_daily_etl）と ETL 結果オブジェクト（ETLResult）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集、前処理、raw_news への保存（SSRF 対策・サイズ制限・トラッキング除去）
- NLP（kabusys.ai.news_nlp）
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント化し ai_scores に保存
  - バッチ、チャンク処理、頑健なレスポンス検証およびリトライ
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の MA200 乖離とマクロニュースセンチメントを合成して日次レジーム判定
  - LLM 呼び出しのリトライとフェイルセーフ設計
- 研究ユーティリティ（kabusys.research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン、IC（Spearman）計算、統計サマリー、Zスコア正規化
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査トレースのためのDDL・インデックスを冪等に作成
- その他ユーティリティ
  - 統計関数（zscore_normalize）、マーケットカレンダー補助、news window 計算など

セットアップ手順
---
1. リポジトリをクローン / ソースを入手

2. Python 環境を準備（推奨: venv / poetry 等）
   - 例（venv）:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```

3. 依存ライブラリをインストール（最小限の想定）
   - 必要な主要パッケージ（プロジェクト内で使用）:
     - duckdb
     - openai (または openai の互換ライブラリ)
     - defusedxml
   - 例:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 実運用では他に requests 等が必要な場合があります。requirements.txt があればそちらを利用してください。

4. 環境変数 / .env を用意
   - プロジェクトルート（.git や pyproject.toml のある階層）に .env を置くと自動ロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=your_slack_bot_token
     SLACK_CHANNEL_ID=your_slack_channel_id
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PID_FILE_PATH=data/execution.pid
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 説明:
     - JQUANTS_REFRESH_TOKEN: J-Quants 認証用リフレッシュトークン
     - OPENAI_API_KEY: OpenAI（LLM）API キー
     - KABU_API_PASSWORD / KABU_API_BASE_URL: kabu ステーション API 用
     - Slack 関連: モニタリング通知用
     - DUCKDB_PATH / SQLITE_PATH: データベースファイルパス
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: ログレベル

5. データベース（DuckDB）を準備
   - ETL や監査DB初期化用に親ディレクトリを作成しておくとスムーズです（init 関数は自動生成も行います）。

基本的な使い方
---
- 設定参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- DuckDB 接続作成（デフォルトファイルを使用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（全体パイプライン）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（news_nlp）
  ```python
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  num_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote ai_scores for {num_written} codes")
  ```

- 市場レジーム判定（regime_detector）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # 監査用テーブルが作成されます
  ```

- ETL 内部ユーティリティ（個別ジョブ）
  - run_prices_etl, run_financials_etl, run_calendar_etl があり、個別に呼べます。

注意点 / トラブルシューティング
---
- 環境変数の自動ロード
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込みます。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- OpenAI / J-Quants の API キー未設定は ValueError を投げます（各関数の冒頭でチェック）。
- ネットワークや API のエラーは各モジュールでリトライやフェイルセーフになっていますが、ログを確認してください。
- テスト時は外部 API 呼び出し部分（例: kabusys.ai.news_nlp._call_openai_api, kabusys.ai.regime_detector._call_openai_api, kabusys.data.news_collector._urlopen 等）をモックしてください。モジュール内から直接差し替え可能です。

ディレクトリ構成（抜粋）
---
リポジトリの主要モジュール構造（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                           # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                        # ニュース NLP（センチメント）
    - regime_detector.py                 # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                  # J-Quants API クライアント & 保存ロジック
    - pipeline.py                        # ETL パイプライン（run_daily_etl 等）
    - etl.py                             # ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py                  # RSS ニュース収集
    - quality.py                         # データ品質チェック
    - calendar_management.py             # 市場カレンダー管理 / 営業日判定
    - stats.py                           # 統計ユーティリティ（zscore_normalize）
    - audit.py                           # 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py                 # ファクター計算（momentum/value/volatility）
    - feature_exploration.py             # 将来リターン, IC, summary
  - research/..., ai/... (その他ユーティリティやモジュール)

- pyproject.toml (想定)
- .env.example (想定)

ライセンス / 貢献
---
本 README はコードベースの概要説明です。実際の運用や再配布にあたってはプロジェクトの LICENSE を確認してください。バグ報告や改善提案は Issue / PR を通じてお願いします。

補足
---
この README はソースコードに基づく概要です。各関数・モジュールの詳細はソース内の docstring を参照してください。必要であれば使い方の具体的な CLI スクリプトやサンプル notebook を追加できます — 希望があれば指示してください。