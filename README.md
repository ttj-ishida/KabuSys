README
======

概要
----
KabuSys は日本株の自動売買・リサーチ基盤を想定した Python パッケージです。  
主要な機能として、取引エンジンの起動・監視、ポートフォリオ構築（銘柄選定・配分・株数計算）、ファクター計算・特徴量探索、ニュースの NLP スコアリング（OpenAI を利用）などを提供します。  
設定は .env ファイル（環境変数）中心で管理し、データは SQLite / DuckDB を用いて永続化・分析します。

主な特徴
--------
- 実行スクリプト
  - run_execution: ExecutionEngine（発注エンジン）起動
  - run_monitoring: SystemMonitor をポーリングする監視ループ起動
- 監視機能
  - システム状態監視（CPU/メモリ/ディスク/プロセス有無）
  - 注文ログ・リスクログ・ダッシュボードの永続化（SQLite）
  - Kill Switch（閾値超過で data/kill.flag を書き込み、エンジン停止）
- 発注関連
  - ブローカークライアントを抽象化（本番 / ペーパートレードを切替可能）
  - 注文管理、リスク管理、リコンサイルロジック
- ポートフォリオ構築（純粋関数）
  - 候補選定、等重・スコア重み計算、ポジションサイズ計算、セクター制約、レジーム乗数
- リサーチ機能（DuckDB ベース）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC 計算、特徴量サマリ
- AI（OpenAI）連携
  - ニュースのセンチメントスコアリング（gpt-4o-mini を想定）
  - マクロニュース + ETF MA に基づく市場レジーム判定
- ツール
  - Paper Trading の検証レポート生成スクリプト

セットアップ
-----------
前提
- Python 3.10+（typing 構文で | を使っているため）
- SQLite（標準ライブラリに同梱）
- DuckDB（Python パッケージ）
- psutil（プロセス優先度やリソース計測に使用）
- OpenAI SDK（AI 機能を使う場合）
- PyYAML（config 検証で YAML を検証する場合。任意）

推奨手順（例）
1. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

3. 初期設定
   - 対話型ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 作成後、設定検証を実行:
     - python -m kabusys.validate_config
     - 問題がある場合はメッセージに従って .env を編集してください。
   - なお、自動で .env を読み込む仕組みがあり（プロジェクトルートの .env / .env.local）、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できます。

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live） default: development
- OPENAI_API_KEY — OpenAI を利用する機能で必要（news_nlp, regime_detector 等）
- その他（任意またはデフォルトあり）
  - DUCKDB_PATH (data/kabusys.duckdb)
  - SQLITE_PATH (data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
  - LOG_LEVEL (INFO 等)
  - PAPER_FILL_MODE (instant | partial | never | reject) — ペーパー注文の挙動

使い方
------
基本的なコマンド例（プロジェクトルートで実行）

1) 環境設定ウィザード（.env 作成・編集）
   - python -m kabusys.config_setup

2) 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

3) 監視プロセス起動（SystemMonitor ポーリング）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60）
     例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視は data/stop_requested.flag が存在すると終了します。

4) ExecutionEngine（発注エンジン）起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使って data/paper_trading.db に記録されます（本番 DB と分離）。
   - 起動時に data/stop_requested.flag が既にあるとエンジンは起動せず終了します。
   - 実行中に data/stop_requested.flag を作成するとエンジンを停止します。

5) Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで SQLite ファイル指定可能（環境変数 PAPER_TRADING_SQLITE_PATH も優先して使用）

6) AI 機能（プログラムからの呼び出し例）
   - ニューススコア付け（プログラムから呼ぶ）
     from kabusys.ai.news_nlp import score_news
     score_news(duckdb_conn, target_date, api_key="あなたのキー")
   - レジーム判定
     from kabusys.ai.regime_detector import score_regime
     score_regime(duckdb_conn, target_date, api_key="あなたのキー")
   - CLI ラッパーは提供していないため、スクリプトや REPL から呼び出してください。

運用上のヒント / 重要点
- Monitoring は Settings.env にかかわらず sqlite_path（デフォルト data/monitoring.db）を使用します。Execution は paper_trading 環境で専用 DB を使うので本番 DB と分離可能です。
- Kill Switch: RiskMonitor 等の判定により KillSwitch が data/kill.flag を書き込むと ExecutionEngine に停止命令が送られます。live 環境では KILL_FLAG_CLEAR_ON_START を 1 にしないことを推奨します。
- ログ: logs/ 配下に日次ローテーションでログが出力されます。LOG_DIR 環境変数で変更可能。
- プロセス優先度: 起動スクリプトは set_process_priority("high") を呼び出します。psutil による設定に失敗した場合は警告が出ますが動作は継続します。
- OpenAI 関連: API キーの設定と呼び出し回数に注意。429 / 一時的な接続エラーは指数バックオフでリトライしますが、API 使用量やコストは運用者で管理してください。

ディレクトリ構成（抜粋）
-------------------
src/
  kabusys/
    __init__.py
    config.py                # 環境変数・.env の読み込みおよび Settings
    config_setup.py          # .env 対話式ウィザード
    validate_config.py       # 設定検証 CLI
    run_monitoring.py        # SystemMonitor ポーリング起動スクリプト
    run_execution.py         # ExecutionEngine 起動スクリプト

    utils/
      logging_setup.py       # ログ設定ユーティリティ
      process_priority.py    # プロセス優先度・CPU affinity

    monitoring/
      monitoring_db.py       # SQLite のスキーマ初期化 + 永続化 API
      system_monitor.py      # システム・データ鮮度監視
      trade_monitor.py       # （注文監視）※省略ファイル参照
      risk_monitor.py        # ドローダウン / ポジション上限監視
      kill_switch.py         # kill.flag 管理
      monitoring_engine.py   # 各モニタを束ねる

    execution/
      broker_factory.py      # ブローカークライアントの生成
      execution_engine.py    # ExecutionEngine 実装
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py

    research/
      factor_research.py
      feature_exploration.py

    ai/
      news_nlp.py             # OpenAI を使ったニュースセンチメント
      regime_detector.py      # レジーム判定（MA + マクロセンチメント）

    tools/
      paper_verification_report.py

データ・ログ
-----------
- デフォルトのパス
  - DuckDB: data/kabusys.duckdb
  - Monitoring (SQLite): data/monitoring.db
  - Paper Trading (SQLite): data/paper_trading.db
  - PID / Kill フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
  - ログ: logs/<app_name>.log

- stop_requested.flag を置くと run_monitoring / run_execution のループが終了します（安全なシャットダウンのトリガーとして使用）。

開発者向けメモ
--------------
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を検出して行います。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- YAML 検証を行う場合は PyYAML をインストールしてください。validate_config.py はインストールがなければ YAML のパースチェックをスキップします。
- AI 関連の API 呼び出しは外部 SDK（openai）が必要です。テストでは _call_openai_api をモックしてください。

トラブルシューティング
---------------------
- 必須環境変数の未設定でエラーになる場合:
  - python -m kabusys.validate_config で不足項目を確認し、.env を修正してください。
- ログファイルが作成されない:
  - 権限や LOG_DIR の設定を確認。作成できない場合はコンソール出力のみになります。
- OpenAI 呼び出しで 429 が多発する場合:
  - バックオフ設定やバッチサイズ（news_nlp の _BATCH_SIZE）を見直すか API 制限を緩める（アカウント側）必要があります。

ライセンス / 連絡
-----------------
この README はコードベースの解説用に作成されています。詳しいアルゴリズムや運用ルール（PortfolioConstruction.md 等）は別ドキュメントを参照してください。質問や改善提案があればリポジトリの issue を作成してください。