KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買の基盤ライブラリです。  
主な役割は以下の通りです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの ETL
- ニュースの収集・NLP（LLM）によるセンチメントスコア付与
- 市場レジーム判定（MA と マクロセンチメントの融合）
- 研究用のファクター計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック・監査ログ（発注〜約定のトレーサビリティ）
- DuckDB を中心としたローカル DB 操作ユーティリティ

本リポジトリはライブラリ形式で提供され、ETL バッチや研究スクリプト、戦略ロジックの基盤として組み込んで使います。

主な機能
--------
- データ取得・保存
  - J-Quants API クライアント（fetch / save 用の冪等関数）
  - 市場カレンダー・上場銘柄情報取得
- ETL パイプライン
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL ジョブ（prices / financials / calendar）
- ニュース収集・NLP
  - RSS 取得と前処理（SSRF 対策・トラッキング除去）
  - OpenAI（gpt-4o-mini）による銘柄別センチメントスコア付与（score_news）
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離とマクロセンチメントを合成して判定（score_regime）
- 研究用ユーティリティ
  - ファクター計算（momentum, value, volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース）
- 環境設定管理（.env の自動読み込み、必須変数チェック）

セットアップ手順
----------------

前提
- Python 3.10+（PEP 604 の型記法などを使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. インストール
   - pip install -U pip
   - pip install -e ".[dev]"  # 開発用依存を含めてインストールする想定
     （プロジェクト配布の仕方に応じて requirements.txt / pyproject の指定に従ってください）

   最低限必要なライブラリ（主要なもの）
   - duckdb
   - openai
   - defusedxml

   ※ pip install -e . が使えない場合は最低限上記パッケージをインストールしてください。

4. 環境変数のセット
   プロジェクトルートに .env（必要に応じて .env.local）を作成します。主な変数:

   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - OPENAI_API_KEY=<your_openai_api_key>
   - KABU_API_PASSWORD=<kabu_station_password>
   - SLACK_BOT_TOKEN=<slack_bot_token>
   - SLACK_CHANNEL_ID=<slack_channel_id>
   - DUCKDB_PATH=data/kabusys.duckdb  # 任意
   - SQLITE_PATH=data/monitoring.db    # 任意
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   補足:
   - .env.local は .env を上書きして読み込まれます（OS 環境変数は上書きされません）。
   - 自動で .env を読み込みたくない場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（簡易ガイド）
------------------

基本的な DB 接続例（DuckDB）:
- 例: ETL を実行するスクリプト内で

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

ニュースセンタメントの実行（score_news）
- raw_news と news_symbols が整備されている前提

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込み銘柄数: {n_written}")

市場レジーム判定（score_regime）
- ETF 1321 の MA とマクロニュースでレジーム判定

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))

監査ログ DB の初期化
- 発注/約定の監査テーブルを独立 DB として初期化する例

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以降 conn を使って監査テーブルに書き込み可能

設定の利用
- 環境変数は kabusys.config.settings 経由でアクセスできます:

  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)

ログ・環境
- KABUSYS_ENV は development / paper_trading / live のいずれか。
- LOG_LEVEL でログレベルを制御。

注意点・テスト時の便利機能
- 自動 .env 読み込みはプロジェクトルート（.git or pyproject.toml の存在するディレクトリ）を基準に行われます。テスト時に自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API 呼び出し部分は内部でリトライやフェイルセーフ（失敗時は 0 にフォールバック）を行いますが、API キーが未設定だと例外になります。score_news/score_regime に api_key 引数を渡すことで明示的にキーを指定できます。

ディレクトリ構成（主要ファイル）
----------------------------

src/kabusys/
- __init__.py
- config.py                         : 環境変数と設定の読み込み管理
- ai/
  - __init__.py
  - news_nlp.py                     : ニュースの集約・LLM によるセンチメント付与（score_news）
  - regime_detector.py              : 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py               : J-Quants API クライアント（fetch / save / 認証 / rate limiter）
  - pipeline.py                     : ETL パイプライン（run_daily_etl 等）および ETLResult
  - etl.py                          : ETL インターフェース再エクスポート（ETLResult）
  - news_collector.py               : RSS 収集・前処理・保存ユーティリティ
  - calendar_management.py          : マーケットカレンダーロジック（営業日判定など）
  - stats.py                        : zscore 正規化などの統計ユーティリティ
  - quality.py                      : データ品質チェック
  - audit.py                        : 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py              : momentum / value / volatility の計算
  - feature_exploration.py          : 将来リターン, IC, 統計サマリー 等

各モジュールの説明（概略）
- config.py: .env 読み込みロジック（クォートやコメント処理、.env.local の上書き、OS 環境保護）
- jquants_client.py: レート制限、トークン自動リフレッシュ、ページネーション対応、DuckDB への冪等保存
- pipeline.py: ETL の orchestrator（カレンダー → 株価 → 財務 → 品質チェックまでを一括で実行）
- news_collector.py: RSS フィード安全取得（SSRF 対策、gzip / サイズ上限、トラッキング除去）
- news_nlp.py / regime_detector.py: OpenAI（gpt-4o-mini）を JSON mode で呼び、レスポンスのバリデーション・リトライを実装
- research/*: バックテストやファクターレポート作成時に使える計算ユーティリティ

運用上の留意点
--------------
- 本ライブラリは実際の発注を行う機能を含む運用設計を想定しています。live 環境での使用は十分なテストと監査（監査DB、Slack 通知、障害時のフォールバック）を必ず行ってください。
- OpenAI / J-Quants の API キー・トークンは厳重に管理してください。ログにキーを出力しないよう注意してください。
- DuckDB ファイルは共有ストレージで同時アクセスすると整合性問題になることがあります。複数プロセスで同じ DB を扱う場合は運用ルールを設けてください。

貢献と開発
-----------
- コードベースはユニットテストを想定した設計（モック差し替え可能な内部関数、API 呼び出しの抽象化）になっています。テストを書く際は適宜 unittest.mock.patch 等を利用してください。
- 変更を加える場合は README やドキュメント内の設定例も合わせて更新してください。

ライセンス / その他
-------------------
- 本プロジェクトの LICENSE ファイルに従ってください（プロジェクト配布時に付与されているはずです）。

お問い合わせ
----------
不明点や実運用に関する質問があれば、リポジトリの Issue を立てるか内部ドキュメント（Design Docs: DataPlatform.md / StrategyModel.md 等）を参照してください。

以上。README の補足や実行サンプルの追加を希望する場合は、どの操作（ETL、ニュース処理、レジーム判定、監査 DB 初期化、等）について詳しく知りたいか教えてください。