KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買・研究基盤（KabuSys）のコアモジュール群です。  
バックテスト／リサーチ用の DuckDB、監視／ログ用の SQLite を利用し、Execution（発注実行）、Monitoring（監視）、AI（ニュースNLP／レジーム判定）などのコンポーネントで構成されています。

主な特徴
--------
- 実行/監視プロセスの起動スクリプト（run_execution.py / run_monitoring.py）
- Paper Trading（ペーパートレード）を本番 DB と完全分離して実行可能
- .env ベースの環境設定ウィザード（対話式）
- 起動前の設定検証 CLI（validate_config）
- DuckDB を用いたファクター計算 / リサーチモジュール
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価・レジーム判定（API キー必須）
- 監視用の永続化層（SQLite）とアラート／Kill Switch 機構
- ロギングは標準出力 + 日次ローテートファイルをサポート（logs/）

機能一覧
--------
主要機能（抜粋）：

- Execution（発注）
  - BrokerClientFactory によるブローカークライアント抽象化（KABUSYS_ENV=paper_trading 時は MockBroker を使用）
  - RiskManager / OrderManager / Reconciler / ExecutionEngine の組立てと実行
  - PID ファイル管理（data/execution.pid）

- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク・プロセス生存・データ鮮度のチェック
  - TradeMonitor：注文／約定ログの整合性チェック（滞留注文・異常約定等）
  - RiskMonitor：ドローダウンやポジション上限監視（ダッシュボード更新、リスクログ記録）
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：上記をまとめてポーリング

- Research / Data
  - DuckDB ベースのファクター計算（momentum/value/volatility 等）
  - forward returns / IC / 統計サマリー等の分析ツール

- AI
  - news_nlp.score_news：ニュース記事を OpenAI で評価して ai_scores に書き込み
  - regime_detector.score_regime：マクロ＋ETF MA を組合せた市場レジーム判定（market_regime テーブルへ書込）

- Utils / Ops
  - config_setup.py：.env を対話式で作成・更新
  - validate_config.py：起動前の環境・設定検証 CLI
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成
  - ロギング設定ユーティリティ（統一ログ出力）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ手順
----------------
※ここでは一般的な手順を示します。実際は環境に応じて Python バージョンや要件を調整してください。

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は最低限以下をインストールしてください）
     - duckdb, psutil, openai, (PyYAML は config 検証で必要)

4. 環境変数の設定（.env を作成）
   - 対話式ウィザードを使う：
     - python -m kabusys.config_setup
   - 手動で .env を作る場合、最低限必須の環境変数：
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - その他の主要な環境変数（主なもの）：
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI モジュール利用時に必須

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合は --strict を付ける

使い方（起動 / 操作例）
--------------------

- Execution（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 特記事項：
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db に記録します（本番 DB と分離）。
    - 実行中に停止させたい場合は data/stop_requested.flag を作成するか、Kill Switch により data/kill.flag が書き込まれた場合はエンジンが停止します。
    - PID ファイル path は Settings().pid_file_path（デフォルト data/execution.pid）。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト: 60）。
  - run_monitoring は常に本番の sqlite_path を使用して監視 DB を初期化します（環境に依存しない）。

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI（ニューススコア・レジーム判定）
  - news_nlp を使う場合は OPENAI_API_KEY を設定してください。
  - モジュール関数（プログラムから呼び出す場合）:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- .env の自動ロード
  - 起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動で読み込みます。
  - 自動ロードを無効化する場合:
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

停止・Kill スイッチ関連
---------------------
- 強制停止トリガー:
  - KillSwitch が条件を満たすと data/kill.flag に理由を書き込みます。ExecutionEngine はこのフラグを検知して停止します。
- 手動停止（優雅な終了）:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが終了します。
- 起動時に Kill Flag を自動クリアする設定:
  - KILL_FLAG_CLEAR_ON_START=1 を .env に設定できます（本番では危険なので 0 推奨）。

ログ
---
- ログは標準出力に出力され、logs/<app_name>.log に日次ローテーションで保存されます（デフォルト 30 日保持）。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御します。

デフォルト DB パス
-----------------
- DuckDB: data/kabusys.duckdb
- SQLite（監視）: data/monitoring.db
- SQLite（paper_trading）: data/paper_trading.db

ディレクトリ構成（主要ファイル）
------------------------------
以下は本リポジトリの主要なモジュール構成（src/kabusys 配下）です：

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照)
  - execution/
    - execution_engine.py (参照)
    - broker_factory.py (参照)
    - order_manager.py (参照)
    - order_repository.py (参照)
    - reconciler.py (参照)
    - risk_manager.py (参照)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/ (ランタイムで生成される想定)
    - monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid など
  - utils/
    - logging_setup.py
    - process_priority.py

補足 / 運用上の注意
------------------
- 本番運用（KABUSYS_ENV=live）の場合は .env と設定ファイル（config/*.yaml）を十分に確認してください。validate_config の追加チェックを活用してください。
- OpenAI を利用する機能は API コスト・レイテンシ・レート制限に注意して運用してください。API キーは秘匿扱い（.env は Git 管理しない）。
- Paper Trading は本番 DB と分離されますが、設定ミスにより上書きしないよう .env のパスや環境変数を確認してください。
- プロセス優先度設定（set_process_priority）はプラットフォーム依存で失敗する場合があります。失敗時は警告ログが出力され処理は続行します。

ライセンス・貢献
----------------
（ここにライセンスや貢献方法を記載してください）

以上。README の内容はコードベースの実装に基づいた概略です。特定の運用手順や依存関係（requirements.txt、systemd ユニット、コンテナ定義等）はプロジェクトの運用方針に合わせて別途整備してください。