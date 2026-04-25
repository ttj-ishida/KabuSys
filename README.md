KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・リサーチ向けモジュール群を集めたプロジェクトです。  
主要な責務は次のとおりです。

- 発注エンジン（ExecutionEngine）と発注管理（OrderManager / Reconciler / RiskManager）
- 監視（Monitoring）: システム状態、注文ログ、リスク監視、Kill Switch
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・株数算出・セクター制約）
- リサーチ（ファクター計算、将来リターン、IC 計算、特徴量サマリ）
- AI を用いたニュース NLP（OpenAI を利用したセンチメント評価）
- 開発/運用支援ツール（.env 作成ウィザード、設定検証、Paper Trading レポート）

本リポジトリの目標は、実運用での堅牢さ（ログ、DB 永続化、フェイルセーフ）と研究ワークフロー（DuckDB によるバッチ解析）を両立することです。

主な機能
--------
- Execution:
  - 本番 / ペーパートレードを環境切替（KABUSYS_ENV）で切替
  - BrokerClientFactory により実ブローカー or MockBroker を利用可能
  - 発注履歴・取引ログを SQLite（または分離された paper_trading.db）に永続化
  - PID ファイル、stop フラグで安全に起動・停止

- Monitoring:
  - システムリソース（CPU/メモリ/ディスク）と Execution プロセス可否チェック
  - 注文の滞留や約定異常の検出
  - ドローダウン・ポジション上限の監視と Kill Switch（kill.flag）発動
  - 監視結果を SQLite に永続化（監視テーブル群を自動作成・マイグレーションで対応）

- Portfolio:
  - シグナルの候補選定、等金額/スコア加重配分
  - リスクベースのポジションサイズ計算（単元株考慮、集約キャップ適用）
  - セクター制約適用、レジーム乗数（bull/neutral/bear）

- Research:
  - DuckDB を用いたファクター計算（Momentum/Volatility/Value）
  - 将来リターン計算、IC（Spearman）算出、統計サマリ

- AI:
  - ニュース記事をまとめて OpenAI（gpt-4o-mini）に送信、銘柄ごとのセンチメント ai_score を ai_scores テーブルに保存
  - マクロニュースと ETF MA を組合せた市場レジーム判定（regime_detector）
  - API のレート／ネットワークエラーに対するリトライ（指数バックオフ）

- 開発・運用ユーティリティ:
  - 対話式 .env ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
  - 統一ログ設定（logs/<app>.log、日次ローテーション）

セットアップ手順
--------------
前提:
- Python 3.9+（プロジェクト内の記述に合わせて適切なバージョンを使用してください）
- 推奨: 仮想環境 (venv)

例:

1. リポジトリをクローンして仮想環境を作成・起動
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 主要な依存例（必須 or 推奨）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   ※ リポジトリに requirements.txt がない場合は、使用する機能に応じて上記を個別にインストールしてください。

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

使い方（実行例）
----------------

- ExecutionEngine（取引エンジン）起動
  - KABUSYS_ENV により動作が変わります:
    - development: 発注なしの開発向け
    - paper_trading: MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
    - live: 実ブローカーを利用
  - 起動:
    - python -m kabusys.run_execution
  - 停止:
    - run_execution は data/stop_requested.flag を検知して安全停止します（flag ファイルを作成）
    - Kill Switch（リスク監視）により data/kill.flag が書かれるとエンジンは停止します（Settings.kill_flag_clear_on_start により起動時の自動クリア設定あり）

- Monitoring 起動
  - 起動:
    - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用して監視データを記録します
  - 停止:
    - data/stop_requested.flag を作成すると監視ループが終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能（デフォルト data/paper_trading.db）

- AI 機能
  - OpenAI API キーを設定 (OPENAI_API_KEY)
  - ニューススコアリング: kabusys.ai.score_news を呼ぶ（プログラムから）
  - レジーム判定: kabusys.ai.regime_detector.score_regime を呼ぶ（プログラムから）
  - 使用モデル: gpt-4o-mini（コード内で指定）

主要な環境変数（抜粋）
--------------------
- KABUSYS_ENV: development | paper_trading | live (default: development)
- JQUANTS_REFRESH_TOKEN: J-Quants 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（default: INFO）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject）

運用上のファイルとフラグ
----------------------
- data/execution.pid: ExecutionEngine が PID を書き出す場所（デフォルト）
- data/stop_requested.flag: 管理者が作成すると run_* スクリプトが安全に終了します
- data/kill.flag: Kill Switch が書き込む停止理由。Execution 起動時に Settings.kill_flag_clear_on_start=1 を設定すると自動でクリアされます（本番では 0 推奨）
- ログ: logs/<app_name>.log（app_name は execution / monitoring など）

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                 # 環境変数・.env の自動読み込みと Settings
    config_setup.py           # .env 対話式ウィザード
    validate_config.py        # 設定検証 CLI

    run_execution.py          # ExecutionEngine 起動スクリプト
    run_monitoring.py         # SystemMonitor 起動スクリプト

    utils/
      logging_setup.py        # 統一的ログ設定
      process_priority.py     # プロセス優先度・CPU affinity ユーティリティ

    execution/                # 発注関連（BrokerFactory, ExecutionEngine, OrderManager など）
      ...

    monitoring/
      monitoring_db.py        # SQLite テーブル作成・永続化 API
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      monitoring_engine.py
      kill_switch.py
      alert_manager.py

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py

    research/
      factor_research.py
      feature_exploration.py

    ai/
      news_nlp.py             # ニュース NLP（OpenAI 呼び出し + DB 書込）
      regime_detector.py      # 市場レジーム判定

    data/                     # デフォルトのデータディレクトリ（DB やフラグファイルを置く）
    logs/                     # デフォルトログディレクトリ

注意事項 / 運用上のヒント
------------------------
- .env は機密情報を含むため Git に含めないでください（config_setup でも同旨の警告あり）。
- KABUSYS_ENV=live 設定時は特に注意（validate_config で警告を出すガードあり）。
- OpenAI を利用する処理は API 呼び出し失敗時にフォールバックして継続するよう実装されていますが、API キー管理やコスト管理は運用者が行ってください。
- DuckDB は分析用のローカルデータベースです。定期的なバックアップを検討してください。
- ロギングは stdout とファイルの両方に出力されます。ログディレクトリ作成に失敗した場合はコンソールのみで動きます。

さらに詳しい開発ドキュメント
--------------------------
各モジュール（StrategyModel.md, PortfolioConstruction.md 等）に基づく実装注釈がコードに多数含まれています。アルゴリズムやパラメータの詳細は該当ファイルの docstring を参照してください。

問題報告 / 貢献
----------------
バグや改善提案は Issue を立ててください。Pull Request を歓迎します。開発に参加する際は、.env の機密情報を含めないようご注意ください。

以上がこのコードベースの README です。必要であれば、特定モジュール（例: ExecutionEngine の起動オプションや AI モジュールの挙動）について追記します。どの部分を詳しく知りたいか教えてください。