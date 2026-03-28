KabuSys
=======

日本株向けのデータプラットフォーム & 自動売買支援ライブラリ。  
J-Quants / RSS / OpenAI など外部データを取り込み、ETL・品質チェック・特徴量計算・ニュースNLP・市場レジーム判定・監査ログ初期化などを提供します。

本 README はソースツリー（src/kabusys）に含まれるモジュール群を対象とした導入・利用ガイドです。

概要
----
KabuSys は以下の機能を備えた Python パッケージです。

- J-Quants API 経由での株価・財務・カレンダー取得（jquants_client）
- DuckDB を用いた差分ETLパイプライン（data.pipeline.run_daily_etl 等）
- データ品質チェック（data.quality）
- ニュース収集（RSS）と前処理（data.news_collector）
- ニュースの LLM によるセンチメント解析（ai.news_nlp）
- マクロ + テクニカルを組み合わせた市場レジーム判定（ai.regime_detector）
- 研究用ファクター計算・探索ユーティリティ（research）
- 監査ログ（signal → order → execution）用スキーマ初期化ユーティリティ（data.audit）
- 環境変数 / 設定読み込み（config）

主な機能一覧
--------------
- ETL
  - run_daily_etl: 市場カレンダー・日足・財務の差分取得＋品質チェック
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks: 全チェック実行
- ニュース
  - fetch_rss: RSS 取得 + 前処理（SSRF対策・サイズ上限・トラッキング除去）
  - score_news: OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント（ai_scores へ保存）
- 市場レジーム
  - score_regime: ETF (1321) の MA200 乖離とニュースセンチメントを合成して market_regime に保存
- 研究支援
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- 監査ログ
  - init_audit_db / init_audit_schema: 監査用 DuckDB DB の初期化（テーブル・インデックス）

前提 / 必要環境
----------------
- Python 3.10+（型記法に | を使用）
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API, RSS, OpenAI API への通信

例: pip での最低依存インストール
- 例: pip install duckdb openai defusedxml

設定（環境変数）
----------------
設定は環境変数、またはプロジェクトルートの .env / .env.local から自動ロードされます（kabusys.config）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主に使用される環境変数（一部）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL : kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知用
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV : development / paper_trading / live（デフォルト development）
- LOG_LEVEL : DEBUG/INFO/...
- OPENAI_API_KEY : OpenAI API キー（score_news, score_regime で使用）

簡単な .env 例
- .env.example を参考にしてください（プロジェクトルートに配置）。
- 例:
  JQUANTS_REFRESH_TOKEN=xxxx
  OPENAI_API_KEY=sk-xxxx
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development

セットアップ手順
----------------
1. リポジトリをチェックアウトし、仮想環境を作成:
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存ライブラリをインストール:
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを使用）

3. 環境変数を設定:
   - .env をプロジェクトルートに作成するか、OS環境変数を設定してください。
   - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データベース用ディレクトリ作成:
   - デフォルトで data/ 配下に DB ファイルを作成します。必要に応じて作成してください。

使い方（基本例）
----------------

- DuckDB 接続を用意
  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（株価・財務・カレンダー取得＋品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（OpenAI を使って ai_scores を保存）
  from kabusys.ai.news_nlp import score_news
  cnt = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  print(f"scored {cnt} codes")

- 市場レジーム判定（1321 MA200 + マクロニュース）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))  # OpenAI キーは環境変数か引数で指定

- 監査ログ DB 初期化（監査専用 DB を作る）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit_duckdb.db")
  # init_audit_db は transactional=True 相当の処理でスキーマを作成します

- 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  momentum = calc_momentum(conn, date(2026,3,20))
  # z-score 正規化
  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

注意点と設計ポリシー
-------------------
- ルックアヘッドバイアス防止:
  多くの関数（ETL・スコアリング・リサーチ）は date 引数を明示的に受け取り、datetime.today() を直接参照しないよう設計されています。バックテストでの公平性を重視しています。
- 冪等性:
  ETL -> save_* 関数は ON CONFLICT を利用して同一 PK の上書きが可能なため、複数実行でも一貫した状態を保ちます。
- フェイルセーフ:
  LLM や外部 API 呼び出しで問題が起きた場合、例外でプロセスを即終了せずフォールバック（例: スコア = 0.0）して継続する実装が多く含まれます。
- セキュリティ:
  RSS 取得では SSRF 対策、XML の defusedxml 使用、レスポンスサイズ制限など安全対策を実施しています。
- ログ:
  各モジュールは logging を利用。LOG_LEVEL によって出力を制御してください。

ディレクトリ構成（主なファイル）
--------------------------------
src/kabusys/
- __init__.py                 - パッケージ初期化、version
- config.py                   - 環境変数・.env の自動ロード / Settings
- ai/
  - __init__.py
  - news_nlp.py               - ニュースの LLM スコアリング（score_news）
  - regime_detector.py        - 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py         - J-Quants API クライアント（fetch_*/save_*）
  - pipeline.py               - ETL パイプライン（run_daily_etl 等）
  - quality.py                - データ品質チェック
  - news_collector.py         - RSS 収集 / 前処理
  - calendar_management.py    - 市場カレンダー周りのユーティリティ
  - audit.py                  - 監査ログスキーマ定義・初期化
  - etl.py                    - ETLResult の再エクスポート
  - stats.py                  - 統計ユーティリティ (zscore_normalize)
- research/
  - __init__.py
  - factor_research.py        - モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py    - forward returns / IC / summary
- monitoring/                  - 監視・Slack 通知周り（概要のみ、実装ファイルがある場合）
- execution/                   - 発注実装層（外部ブローカー連携用。詳細は該当モジュールを参照）
- strategy/                    - 戦略定義層（signal 生成等。詳細は該当モジュールを参照）
- research/                    - 研究用ユーティリティ（上に記載）

テスト・開発
------------
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml を起点）を探索して読み込みます。テスト実行時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分は内部で分離されており、ユニットテストでは _call_openai_api を patch して差し替えることが想定されています。
- DuckDB を用いるため、テスト時は ":memory:" を指定してインメモリ DB を使うと便利です（例: init_audit_db(":memory:")）。

貢献 / 開発方針
---------------
- 各関数はドキュメントと設計方針がソース内に詳細に書かれているため、新規実装は既存の設計ガイドライン（ルックアヘッド防止、冪等性、フェイルセーフ等）に従ってください。
- LLM / API 呼び出しはリトライ・バックオフ・エラーハンドリングを必ず実装してください。

ライセンス
---------
プロジェクトに同梱の LICENSE を参照してください（本 README 内では明示していません）。

補足
----
本 README はソースコードの主要機能をまとめた参照です。より詳細な設計仕様（DataPlatform.md, StrategyModel.md 等）が別途存在する想定のため、実運用やバックテストの前にそれらと合わせて確認してください。質問や具体的なコード例が必要であれば、どの機能についての使用例が欲しいか教えてください。