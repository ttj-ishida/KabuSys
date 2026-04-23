KabuSys
=======

日本株向け自動売買／リサーチ基盤の一部です。  
このリポジトリは、監視（Monitoring）、実行エンジン（Execution）、ポートフォリオ構築、ファクター計算、AI（ニュースNLP / レジーム判定）などのユーティリティ群を含みます。

主な目的
- 実取引（live）・ペーパートレード（paper_trading）両対応の発注実行エンジン
- システム稼働性・注文状態・リスクの監視と Kill Switch（停止フラグ）
- DuckDB / SQLite を用いたデータ処理・検証用リサーチ関数
- OpenAI を用いたニュースセンチメント解析・レジーム判定
- ペーパートレード検証レポート生成ツール

機能一覧
- Settings：環境変数/.env 読み込み・管理（kabusys.config）
  - 自動 .env 読み込み（.env / .env.local）、必要変数の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）
- 環境ウィザード：.env を対話式に作成・更新（python -m kabusys.config_setup）
- 設定検証：.env と config/*.yaml の整合性チェック（python -m kabusys.validate_config）
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し paper_trading.db に記録（本番 DB と分離）
  - execution PID / stop フラグを監視して安全に停止
- 監視起動スクリプト（run_monitoring.py）
  - SystemMonitor をポーリングして system_status 等を記録
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視レイヤ
  - SystemMonitor：CPU/MEM/DISK、プロセス生存チェック、データ鮮度チェック
  - TradeMonitor：注文滞留・約定異常等の検出（trade_logs ベース）
  - RiskMonitor：ドローダウン / ポジション上限監視、ダッシュボード更新
  - KillSwitch：リスク条件で data/kill.flag を書き込み ExecutionEngine を停止させる
  - MonitoringDB：SQLite に対する読み書き API（テーブル作成 / マイグレーションを含む）
  - MonitoringEngine：各 Monitor を束ねて定期実行・アラート発火
- Portfolio（純粋関数群）
  - 候補選定、重み計算（等重・スコア加重）、セクター制限、ポジションサイズ計算（lot 切上）
- Research（DuckDB ベースのファクター計算）
  - Momentum / Volatility / Value 等のファクター計算、将来リターン、IC 計算、統計サマリ
- AI モジュール（OpenAI 使用）
  - news_nlp.score_news：ニュースを集約して LLM に投げ銘柄ごとにセンチメント（-1.0〜1.0）を算出・保存
  - regime_detector.score_regime：ETF ma200 乖離とマクロニュース LLM を組合せて市場レジーム判定
- ツール
  - paper_verification_report：ペーパートレード DB から検証レポートを生成（稼働率、注文成功率、レイテンシ等）

セットアップ手順（ローカル）
- 前提
  - Python 3.9+（一部の型注釈を利用）、SQLite は標準ライブラリで利用可能
  - DuckDB, psutil, openai, PyYAML（依存関係は環境によって異なる）

1) リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2) 仮想環境を作成・有効化（任意だが推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3) 依存パッケージをインストール
   - requirements.txt があれば:
       python -m pip install -r requirements.txt
   - なければ最低限:
       python -m pip install duckdb psutil openai PyYAML

4) .env を作成
   - 対話式ウィザード推奨:
       python -m kabusys.config_setup
     このウィザードで JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV 等を設定します。
   - もしくは手動で .env を作成（.env.example を参照）

5) 設定の検証（必須）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります:
   python -m kabusys.validate_config --strict

主要な環境変数（よく使うもの）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）

使い方（起動例）
- 監視ループを起動（デフォルト 60 秒間隔。環境変数で上書き可）
  python -m kabusys.run_monitoring
  例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  動作のポイント:
  - 起動時にプロセス優先度を "high" にセットし、MonitoringDB を初期化します。
  - data/stop_requested.flag が存在するとループを終了します。

- 実行エンジンを起動（マーケット実行 / ペーパー切替）
  python -m kabusys.run_execution
  例（ペーパートレード）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  動作のポイント:
  - paper_trading 環境では BrokerClientFactory が MockBrokerClient を生成し
    PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - data/stop_requested.flag を作成するとエンジンを安全に停止できます。
  - 実行中は data/execution.pid に PID が書かれます。

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI スコアリング / レジーム判定（プログラム的利用）
  - news_nlp:
      from kabusys.ai.news_nlp import score_news
      score_news(conn, target_date, api_key="...")

  - regime_detector:
      from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date, api_key="...")

  注意:
  - OpenAI API のキー（OPENAI_API_KEY）が必要です。呼び出しは外部 API のためコスト・レート制限に注意してください。
  - モデルはコード上で gpt-4o-mini を想定しています（変更可）。

ログ
- ロギングは kabusys.utils.logging_setup.setup_logging を各スクリプトで呼び出して統一管理しています。
- デフォルトでは logs/<app_name>.log に日次ローテーションで出力（30 日保持）。コンソールは stdout に出力されます。
- ログ出力先は環境変数 LOG_DIR で変更できます。
- LOG_LEVEL でログレベルを制御します。

停止 / Kill Switch
- KillSwitch（kabusys.monitoring.kill_switch）が危険条件を検出すると data/kill.flag に理由を書き込みます。ExecutionEngine は起動中にこのフラグを検出して停止します。
- 手動で停止したい場合は data/stop_requested.flag を作成すると run_monitoring / run_execution のループが終了します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の読み込みと Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - execution/                — 実行系コンポーネント（Engine, BrokerFactory, OrderManager 等）
  - data/                     — 実行時生成ファイル（例: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid）
  - config/                   — 各種 YAML 設定（system_config.yaml 等。validate_config で参照）

注意事項 / ベストプラクティス
- .env は絶対にリポジトリにコミットしないでください（config_setup も README に注記あり）。
- 本番（KABUSYS_ENV=live）時は LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）等を必ず確認してください。validate_config は live でのガードチェックを行います。
- AI モジュールは外部 API を利用するため、コスト・レート制限・応答の可変性に注意。API エラー時はフェイルセーフでスキップする実装ですが、想定外の動作はあり得ます。
- paper_trading と本番 DB は明確に分離されています。ペーパートレードのデータは PAPER_TRADING_SQLITE_PATH を確認してください。

貢献 / 拡張
- 新しい監視ルールやアラートは monitoring/ 配下に Monitor を追加し、MonitoringEngine に組み込んでください。
- DuckDB スキーマやファクター設計は research/*.py を参考に拡張できます。
- OpenAI 呼び出し周りは retry / rate-limit 周りのロジックを踏襲してください。

ライセンス / その他
- 本リポジトリに含まれるコードの利用条件はリポジトリの LICENSE（存在する場合）を参照してください。

以上が簡易 README です。必要であれば、導入手順の詳細（systemd ユニット例、Docker 化、CI 設定、設定テンプレート .env.example など）を追加で作成します。希望があれば教えてください。