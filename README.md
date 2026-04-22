KabuSys
======

日本株向け自動売買システムのコアライブラリ群です。  
本リポジトリには実行エンジン（ExecutionEngine）、監視/アラート（Monitoring）、ポートフォリオ構築・ポジションサイズ計算、研究用ファクター計算、AI ベースのニュースセンチメント評価などの主要コンポーネントが含まれます。

プロジェクト概要
--------------
- 目的: 日本株の自動売買を支援するためのライブラリ・実行スクリプト群。発注（実運用 / ペーパートレード）・監視・リスク制御・ログ永続化・分析/研究ユーティリティを提供します。
- 設計方針:
  - 実行系ロジックとデータ永続化を分離（SQLite / DuckDB を使用）
  - 環境変数 / .env による設定管理（config_setup による対話式作成）
  - フェイルセーフ設計（監視の通知・Kill Switch、AI 呼び出しのリトライ／フォールバックなど）
  - 研究・バックテスト向けに DuckDB を用いた高速集計関数を提供

主な機能一覧
--------------
- 実行エンジン (run_execution.py)
  - BrokerClientFactory によるブローカー抽象化（KABUSYS_ENV=paper_trading では MockBrokerClient を使用）
  - OrderManager / OrderRepository / RiskManager / Reconciler 等の組み立て
  - PID ファイル・停止フラグ対応（data/execution.pid, data/stop_requested.flag）
- 監視（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存監視
  - TradeMonitor: 注文／約定ログ監視（滞留注文、異常約定など） ※実装ファイル群あり
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナル
  - MonitoringDB: SQLite ベースの永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等配分・スコア配分、セクター上限適用、レジーム乗数、ポジションサイズ決定（単元丸め・集計 cap）
- 研究 / 分析（research パッケージ）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン・IC 計算・統計サマリー等のユーティリティ
- AI モジュール（ai パッケージ）
  - news_nlp: OpenAI（gpt-4o-mini など）を用いたニュースの銘柄別センチメント評価（ai_scores への書き込み）
  - regime_detector: ETF・マクロニュースを組み合わせた日次市場レジーム判定（market_regime テーブルに永続化）
  - API 呼び出しはリトライ・パース検証を行い、失敗時は安全にフォールバック
- ユーティリティ
  - logging_setup: 統一的なログ設定（コンソール stdout + 日次ローテーションファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定（Windows/Linux 対応）
  - config: 環境変数・.env の自動読み込み、Settings クラス
  - config_setup: .env を対話式に生成するウィザード
  - validate_config: 起動前に設定やファイル存在などを検査する CLI
- ツール
  - paper_verification_report: ペーパートレード DB を集計し検証レポートを生成

セットアップ手順
--------------
前提
- Python 3.10 以上（PEP 604（X | Y 型）や型ヒント表記を使用）
- SQLite は標準で利用可能
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config の YAML 検証を利用する場合）

例: 仮想環境作成と依存インストール
1. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. pip で必要ライブラリをインストール（requirements.txt がない場合は手動で）
   - pip install duckdb psutil openai
   - （任意）pip install pyyaml

3. ディレクトリ作成（ログ・データ用）
   - mkdir -p data logs

環境変数の設定
- 推奨ワークフロー: python -m kabusys.config_setup を実行して .env を作成
- 主要な環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY（AI 機能を利用する場合）
  - LOG_LEVEL（例: INFO）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1。production は 0 推奨）
- .env は絶対に Git にコミットしないでください。

設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）になります
  - PyYAML が入っていれば config/*.yaml のパース検証も行います

使い方（起動・CLI）
--------------
基本的な起動スクリプト
- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）指定（デフォルト 60）
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（環境に関係なく）
  - 監視プロセスは起動時にプロセス優先度を "high" に設定します

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは paper_sqlite_path（デフォルト data/paper_trading.db）へ記録され、本番 DB と分離されます
  - 起動時に data/stop_requested.flag が存在する場合は起動をスキップします
  - 実行中に data/stop_requested.flag を作成するとエンジンを安全に停止します

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
    - --strict オプションで警告を致命扱いにできます

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

ログ
- ログは logs/<app_name>.log に日次ローテーションで保存（デフォルト 30 日保持）
- setup_logging を各スクリプトで呼び出して統一的に出力しています
- コンソールは stdout に出力されます

停止・Kill Switch
- 監視・実行はフラグファイルで停止信号をやり取りします:
  - data/stop_requested.flag — run_* スクリプトがループ終了に利用
  - data/kill.flag — KillSwitch によって書き込まれ、ExecutionEngine 側に停止指示を与える（Settings.kill_flag_path）
- KillSwitch.clear() を使うか、手動でファイルを削除してクリアできます（ただし本番では自動クリア設定に注意）

ディレクトリ構成（主要ファイル）
--------------
（src/kabusys 以下の主要モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                -- 環境変数/.env 管理（Settings）
    - config_setup.py          -- .env 対話型ウィザード
    - validate_config.py       -- 設定検証 CLI
    - run_monitoring.py        -- Monitoring 起動スクリプト
    - run_execution.py         -- ExecutionEngine 起動スクリプト
    - utils/
      - logging_setup.py       -- ログ設定ユーティリティ
      - process_priority.py    -- プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py       -- SQLite テーブル作成 / Persistence API
      - system_monitor.py      -- CPU/メモリ/ディスク/データ鮮度監視
      - trade_monitor.py       -- 注文ログ監視（滞留注文等）
      - risk_monitor.py        -- ドローダウン / ポジション数監視
      - kill_switch.py         -- kill.flag 書き込み/評価
      - monitoring_engine.py   -- 各 Monitor 統合ループ
      - alert_manager.py       -- （アラート送信管理: LINE 等、実装場所）
    - execution/
      - execution_engine.py    -- 実行エンジン（セッション管理）
      - broker_factory.py      -- Broker クライアント生成
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py            -- ニュースセンチメント（OpenAI）
      - regime_detector.py     -- レジーム判定（ETF + LLM）
    - tools/
      - paper_verification_report.py
    - data/                    -- 実行時に使用するディレクトリ（data/*.db, *.flag, pid 等）

開発者向けメモ / 注意点
--------------
- Python バージョン: 3.10+
- .env 自動読み込み:
  - プロジェクトルートは .git または pyproject.toml を基準に探索
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用）
- DB:
  - monitoring は Settings.sqlite_path（デフォルト data/monitoring.db）を使用
  - paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を利用して本番 DB と隔離
  - DuckDB を分析・研究用の高速集計に使用（Settings.duckdb_path）
- AI 呼び出し:
  - OPENAI_API_KEY を環境変数または関数引数で指定
  - news_nlp / regime_detector は JSON Mode を利用し、レスポンスの厳密検証・リトライを行います
- ログディレクトリ作成に失敗した場合はファイル出力が無効化されます（コンソール出力は継続）
- .env は機密情報を含むため絶対にリポジトリへコミットしないでください

よく使うコマンド例
--------------
- .env を作る（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- ペーパー検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

ライセンス・その他
--------------
- 本 README ではライセンス情報を含めていません。実際の配布時には LICENSE を合わせて配置してください。
- セキュリティ: API トークン等は環境変数または .env に設定し、バージョン管理システムに含めないでください。

問い合わせ・寄稿
--------------
- バグ報告や機能提案は issue を立ててください。
- 大きな変更を行う場合は設計・安全面（発注ロジック、Kill Switch、DB マイグレーション）を十分に考慮してプルリクエストを作成してください。

以上。README に不足があれば、特に強調したい実行フローや追加で記載したい設定項目（例: 各 config/*.yaml の内容や Broker 実装の切り替え方法等）を教えてください。必要に応じてサンプル .env のテンプレートも作成します。