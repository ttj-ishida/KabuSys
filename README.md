KabuSys
======

日本株向けの自動売買・データプラットフォーム用ライブラリ（モジュール群）です。  
このリポジトリはデータ取得（ETL）・品質チェック・ニュース収集・LLMを使ったニュース評価・市場レジーム判定・ファクター計算・監査ログなど、売買戦略実行の周辺機能を中心に実装しています。

主な特徴
------
- データ取得（J-Quants API）対応
  - 日次株価（OHLCV）・財務データ・上場銘柄情報・JPXマーケットカレンダーの取得（ページネーション・リトライ・レート制御対応）
- ETLパイプライン
  - 差分取得、バックフィル、品質チェック（欠損・重複・スパイク・日付不整合）を含む日次ETL
- ニュース収集
  - RSS収集、URL正規化、SSRF対策、トラッキングパラメータ除去、raw_news / news_symbols への冪等保存
- ニュースNLP（OpenAI）
  - gpt-4o-mini を使った銘柄別ニュースセンチメント評価（JSON Mode、バッチ/リトライ）
- 市場レジーム判定
  - ETF(1321)の200日移動平均乖離とマクロニュースセンチメントを合成して日次の市場レジームを判定
- 研究用ユーティリティ
  - モメンタム／ボラティリティ／バリューのファクター計算、将来リターン計算、IC計算、Zスコア正規化など
- 監査ログ（トレーサビリティ）
  - signal → order_request → execution の階層でトレーサビリティを担保する監査テーブル定義と初期化ユーティリティ
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）、環境変数経由で安全に設定を取得

導入・セットアップ
------
前提
- Python 3.10+（| 型注釈を使用しているため）
- DuckDB を利用（duckdb Python パッケージ）
- OpenAI API を利用する場合は openai パッケージが必要
- RSSパーサで defusedxml を使用

推奨パッケージ（requirements.txt に記載する例）
- duckdb
- openai
- defusedxml

例:
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

3. 環境変数設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（.git または pyproject.toml が存在するディレクトリがプロジェクトルートとして検出されます）。
   - 必須環境変数（少なくとも開発・一部機能で必要）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注連携を行う場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル
     - OPENAI_API_KEY — OpenAI を使う機能（news_nlp, regime_detector）を利用する場合
   - 任意:
     - DUCKDB_PATH （デフォルト data/kabusys.duckdb）
     - SQLITE_PATH （監視用途の SQLite、デフォルト data/monitoring.db）
     - KABUSYS_ENV （development / paper_trading / live、デフォルト development）
     - LOG_LEVEL （DEBUG/INFO/...、デフォルト INFO）
   - 自動.envロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

使い方（簡単な例）
------

- DuckDB 接続を作成して日次 ETL を実行する

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を利用しても良い
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（AI）を実行する

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")  # api_key を省略すると環境変数 OPENAI_API_KEY を参照
  print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定を実行する

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を参照

- 監査ログ用 DB 初期化

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # テーブルを作成して接続を返す

注意事項 / トラブルシューティング
------
- 環境変数が不足していると Settings のプロパティで ValueError が発生します（例: JQUANTS_REFRESH_TOKEN が未設定）。
- OpenAI 呼び出しはネットワーク/レート制限のためリトライロジックが入っていますが、APIキー未設定は即時エラーになります。
- DuckDB のバージョン依存や executemany の挙動に注意してください（コード内で互換性を考慮した実装がされています）。
- 自動で .env を読み込む仕組みはプロジェクトルートの検出に頼っているため、パッケージ化・配布後は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか明示的に環境変数を渡してください。

ディレクトリ構成
------
（主要ファイル・モジュールの一覧）

- src/kabusys/
  - __init__.py
  - config.py                   -- 環境変数 / 設定管理（.env 自動ロード、Settings）
  - ai/
    - __init__.py
    - news_nlp.py                -- ニュース NLU スコアリング（score_news）
    - regime_detector.py        -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py    -- 市場カレンダー管理（営業日判定等）
    - pipeline.py               -- ETL パイプライン（run_daily_etl 他）
    - etl.py                    -- ETL ユーティリティの公開インターフェース（ETLResult）
    - stats.py                  -- 汎用統計ユーティリティ（zscore_normalize）
    - quality.py                -- データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py                  -- 監査ログテーブル定義・初期化
    - jquants_client.py         -- J-Quants API クライアント（取得／保存）
    - news_collector.py         -- RSS ニュース収集（SSRF 対策・前処理）
  - research/
    - __init__.py
    - factor_research.py        -- Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py    -- 将来リターン / IC / 統計サマリー 等
  - (strategy/, execution/, monitoring/ モジュールはパッケージ全体の一部として想定されます)

開発・テスト
------
- 単体テストではネットワークアクセスや OpenAI 呼び出しをモックしてください（コード内で差し替え可能な関数が用意されています）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を使って .env 自動読み込みを無効化できます（テスト用に便利）。

ライセンス / 貢献
------
- （ここにプロジェクトのライセンスや貢献ルールを記載してください。例: MIT License）

補足
------
README はコードベースの主要機能と利用例を要約したものです。各モジュールの詳細な仕様・パラメータ・戻り値・例外については該当モジュールの docstring を参照してください。必要であれば README に追加すべき具体的なセクション（例: CI / デプロイ手順・運用監視方法）があれば教えてください。