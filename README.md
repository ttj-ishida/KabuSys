KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / モニタリングを目的とした Python ベースのシステムです。
主要な機能はシグナル計算・ポートフォリオ構築・発注エンジン（ExecutionEngine）・監視（Monitoring）・AI を用いたニュース評価などを含みます。

設計方針（抜粋）
- 核心ロジックは純粋関数（副作用を持たない）で実装し、テスト容易性を重視
- 本番データベースとペーパートレード DB を分離（KABUSYS_ENV に依存）
- OpenAI を用いた NLP 機能は API キーを外部から与える設計（フェイルセーフあり）
- ロギング・プロセス優先度設定・kill-switch 等の運用機能を備える

主な機能一覧
---------------
- Execution（発注）:
  - ExecutionEngine を起動してブローカーへ発注（KABUSYS_ENV に応じて MockBroker を使用）
  - リスク管理（RiskManager）、Order 管理、再整合（Reconciler）
- Monitoring（監視）:
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - kill.flag による停止シグナル発行、各種アラート発行
- Portfolio（ポートフォリオ構築）:
  - 候補選定、等重・スコア重み、リスク基づくポジションサイズ計算、セクターキャップ、レジーム調整
- Research（研究用）:
  - ファクター計算（Momentum / Value / Volatility / Liquidity）、特徴量探索、IC 計算、前方リターン算出
  - DuckDB を用いた高速分析
- AI 支援:
  - ニュース記事のセンチメント評価（OpenAI / gpt-4o-mini 想定）
  - 市場レジーム判定（MA とマクロニュースの組合せ）
- ユーティリティ:
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading の検証レポート生成ツール（tools.paper_verification_report）
  - 統一的なログ設定・プロセス優先度ユーティリティ

セットアップ手順
----------------

前提
- Python 3.10 以上を推奨（ソースで | 型注釈等を使用）
- SQLite（標準ライブラリ）、DuckDB、psutil、openai 等の Python パッケージ

推奨インストール例（venv を使用）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai
   - PyYAML は設定ファイル検証で任意: pip install pyyaml

3. リポジトリルートに移動（.git または pyproject.toml を含む場所がプロジェクトルート）
   - 自動で .env を読み込む機能が有効なため CWD に依存せず動作します。

環境変数 / .env 設定
- 推奨: python -m kabusys.config_setup を実行して対話的に .env を作成
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 重要な環境変数（一部）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録される
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/…）
  - OPENAI_API_KEY: OpenAI API を使う機能で必要
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

設定検証
- .env 作成後、設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗として exit(1)

使い方（主要コマンド）
--------------------

. env 作成・編集（対話式）
- python -m kabusys.config_setup

設定検証
- python -m kabusys.validate_config
- 厳密モード: python -m kabusys.validate_config --strict

ExecutionEngine を起動（発注エンジン）
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときはペーパートレード DB を使用（本番 DB と分離）
  - 起動時に data/execution.pid が作成され、data/stop_requested.flag によって停止可能
  - 起動前に kill.flag が立っている場合は起動しません

Monitoring（監視）を起動
- python -m kabusys.run_monitoring
  - 環境に関わらず本番の sqlite_path を使用して監視を記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（秒、デフォルト 60）
  - data/stop_requested.flag が存在すると監視ループを終了

Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能

AI 機能（ニューススコア・レジーム判定）
- OpenAI API キーを用意（環境変数 OPENAI_API_KEY）
- ニュース評価:
  - 実行用 API は kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼ぶ設計（エンジンやスケジューラから呼出）
  - 失敗時はフェイルセーフでスコアを補完する実装あり

運用上のファイル / フラグ
- data/kill.flag : ExecutionEngine に対する停止フラグ（KillSwitch が書き込む）
- data/stop_requested.flag : run_* スクリプト自体を停止するためのフラグ（手動停止用）
- data/execution.pid : ExecutionEngine の PID ファイル
- logs/<app_name>.log : 日次ローテートされるログファイル（ログディレクトリは LOG_DIR で上書き可）

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys を基準に抜粋）

- kabusys/
  - __init__.py                         - パッケージ定義・バージョン
  - config.py                           - 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py                     - .env 対話式ウィザード
  - validate_config.py                  - 設定検証 CLI
  - run_execution.py                    - ExecutionEngine 起動スクリプト
  - run_monitoring.py                   - SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py      - Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py                       - ニュースの OpenAI によるセンチメント評価
    - regime_detector.py                - 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py                  - SQLite 監視 DB の永続化層
    - monitoring_engine.py              - 各種 Monitor を束ねるエンジン
    - system_monitor.py                 - システム・データ鮮度監視
    - trade_monitor.py (存在)           - 発注ログ監視（コード参照）
    - risk_monitor.py                   - ドローダウン・ポジション上限監視
    - kill_switch.py                    - kill.flag の発行ロジック
    - alert_manager.py (存在)           - アラート送信（LINE 等）
  - execution/
    - execution_engine.py               - 発注実行エンジン本体
    - broker_factory.py                  - ブローカークライアント生成（Mock/実ブローカー切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py
  - portfolio/
    - portfolio_builder.py              - 候補選定・重み計算
    - position_sizing.py                - 株数決定・単元丸め・集約キャップ
    - risk_adjustment.py                 - セクター上限・レジーム乗数
  - research/
    - factor_research.py                - Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py            - 前方リターン・IC・統計
  - utils/
    - logging_setup.py                  - 共通ログ設定（Stream + 日次ローテーション）
    - process_priority.py               - プロセス優先度・CPU affinity 設定
    - その他ユーティリティ

注意事項・運用メモ
-----------------
- KABUSYS_ENV の意味:
  - development: 開発用（発注等の副作用を抑制する設計が組まれている場所あり）
  - paper_trading: 発注はモックで実行、専用の PAPER_TRADING_SQLITE_PATH を使う
  - live: 本番（実際に発注される。設定を慎重に）
- 本番環境での Kill Switch:
  - validate_config は KABUSYS_ENV=live のとき警告を出すチェックを行う（LINE 設定など）
  - KILL_FLAG_CLEAR_ON_START=1 は本番では危険。通常 0 を推奨
- ログ:
  - ログディレクトリに書き込めない場合はコンソール出力のみで継続します（設定済）
- DB マイグレーション:
  - init_monitoring_db() は冪等にテーブル・カラムを作成・追加する（簡易マイグレーション実装あり）
- OpenAI 使用時の注意:
  - API 呼び出しはリトライ・バックオフ・バリデーションを行うが、API キーの漏洩・利用料に注意してください

よくあるコマンド例
-----------------
- 対話式で .env を作成:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- 実行エンジン（ペーパートレード）を起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- モニタ（デフォルト 60s ポーリング）起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

貢献・拡張ポイント
------------------
- ブローカーの実装を追加して live 環境での接続を実現
- strategy_config.yaml に基づく戦略プラグイン化（外部戦略ロード）
- ai.news_nlp のロギング・API 呼出のメトリクス蓄積
- DuckDB スキーマの管理、分析パイプラインの最適化

ライセンス / 著作権
-------------------
（必要に応じてここにライセンス条項を記載してください）

---

この README はコードベースの実装に基づく要点をまとめたものです。実運用やデプロイ時は環境変数・ログ設定・DB のバックアップ・監視ポリシーを十分に検討してください。質問や追加のドキュメント化（API 詳細・設計ドキュメント化）が必要であればお知らせください。