README — KabuSys

概要
- KabuSys は日本株向けの自動売買システムのコードベースです。
- 戦略のリサーチ／ファクター計算、ポートフォリオ構築、発注実行、監視、ペーパートレード検証、AI（ニュースセンチメント／レジーム判定）などのコンポーネントを含みます。
- 本リポジトリは主に以下の役割を持つモジュールで構成されています：
  - execution: 発注エンジン／ブローカーインタフェース（paper_trading モードあり）
  - monitoring: システム／トレード／リスク監視、Kill Switch、アラート連携
  - portfolio: 候補選定・ウェイト計算・ポジションサイジング・リスク調整
  - research: ファクター計算・特徴量探索
  - ai: ニュース NLP（OpenAI）を使ったセンチメント、レジーム判定
  - tools: レポート等のユーティリティ

主な機能
- ExecutionEngine（発注実行）
  - 本番（live）／ペーパートレード（paper_trading）を切り替え可能
  - ペーパートレード時は MockBrokerClient を用い、専用 SQLite（data/paper_trading.db）に記録
  - リスクマネージャー、オーダーマネージャー、再整合（reconciler）等を備える
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス生存監視
  - TradeMonitor: 発注／約定ログの監視（滞留注文・異常約定など）
  - RiskMonitor: ドローダウン・ポジション数上限の監視とリスクログ記録
  - KillSwitch: しきい値超過で data/kill.flag を書き込み、Execution を停止させる仕組み
  - MonitoringEngine: 上記コンポーネントを束ねて定期ポーリング（デフォルト 60 秒）
  - 監視ログを永続化する SQLite スキーマ（system_status, trade_logs, positions, risk_logs, dashboard）
- Research / Portfolio
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
  - ポートフォリオ構築用の候補抽出、ウェイト計算、ポジションサイズ計算、セクター制限、レジーム係数適用
- AI コンポーネント（OpenAI）
  - ニュースを LLM（gpt-4o-mini を想定）でセンチメント化して ai_scores に格納
  - マクロニュースと ETF（1321）MA を合成して市場レジーム（bull/neutral/bear）を判定
- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env と config/*.yaml の基本チェック
  - paper_verification_report: ペーパートレード結果の集計・判定レポート出力

前提（Requirements）
- Python 3.10+
- 必須／推奨ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- 標準ライブラリ: sqlite3, logging, threading, argparse など

セットアップ手順
1. リポジトリをクローンしてワークディレクトリに移動
   - git clone ... ; cd <repo>

2. Python 環境を作成（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. データディレクトリの作成（logs, data）
   - mkdir -p data logs

5. .env の作成
   - 対話式ウィザードを実行: python -m kabusys.config_setup
   - または .env.example を参考に .env を作成
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live。デフォルト development）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - OPENAI_API_KEY（AI モジュールを使う場合必須）
     - LOG_LEVEL（任意）
     - LOG_DIR（任意）
     - PAPER_FILL_MODE（paper_trading の fill 動作: instant | partial | never | reject）

6. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

基本的な使い方
- 実行エンジン起動（発注）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します
  - 実行中に停止させるにはプロジェクトルートの data/stop_requested.flag を作成（run_execution はこのファイルを監視します）
  - Execution の PID ファイルは data/execution.pid（Settings.pid_file_path）に保存されます

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます（例: MONITOR_POLL_INTERVAL=30）
  - Monitoring は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します（監視ログを一元化）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能）
  - 主要指標: 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数 等を表示し PASS/FAIL を判定

- AI モジュール（ニューススコア / レジーム判定）
  - OpenAI API キー: OPENAI_API_KEY を .env に設定
  - ニューススコア: kabusys.ai.score_news（呼び出しは duckdb 接続 + target_date を渡して行います）
  - レジーム判定: kabusys.ai.regime_detector.score_regime（同様に duckdb 接続 + target_date）

ログ
- setup_logging によりログは stdout（コンソール）とファイル（logs/<app_name>.log）に出力されます
- ログレベルは環境変数 LOG_LEVEL で設定（デフォルト INFO）
- ログディレクトリは LOG_DIR 環境変数で指定可能（デフォルト logs/）

監視用 DB スキーマ（monitoring_db）
- init_monitoring_db が作成するテーブル（冪等）:
  - system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
  - trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
  - positions (code, qty, avg_price, current_price, updated_at)
  - risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
  - dashboard (単一行で集計を保持; id=1)
- MonitoringDB クラス経由で読み書きを行います

停止・Kill スイッチ
- 強制停止フラグ: data/stop_requested.flag（run_* スクリプトがこれを監視して終了）
- Kill Switch（リスク超過検出時）: data/kill.flag に理由を書き込み、ExecutionEngine 側で停止処理が走る設計
- Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリアする動作を設定可能（本番では 0 推奨）

ディレクトリ構成（src を起点）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込みロジック、Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装により存在)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - data/
    - pipeline.py (prices_daily などを扱うもの)
    - stats.py (zscore_normalize 等)
  - utils/
    - logging_setup.py
    - process_priority.py

注意事項・運用メモ
- KABUSYS_ENV を "live" にすると本番動作になります。機密情報・APIキーの管理、Kill Switch 設定、LINE 通知等を必ず確認してください。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも注意書きがあります）。
- OpenAI API を利用する機能は課金やレート制限の対象です。API キーやリトライ設定に注意して運用してください。
- DuckDB は分析用 DB、SQLite は監視／注文ログ用に使われます（paper_trading 用は分離）。
- process_priority.set_process_priority を起動時に呼び出して優先度を "high" に設定しますが、権限や OS によって効果がない場合があります。ログに警告が出ます。

開発者向け
- モジュールはできるだけ副作用を避け、純粋関数的に設計されています（特に portfolio/* と research/*）。
- テストを追加する場合は、OpenAI 呼び出しやファイル IO 部分をモックすることでユニットテストを容易にできます。
- DuckDB および SQLite の接続は外部から注入する形（引数で渡す）になっているため、テスト用のインメモリ DB を使った検証が可能です。

問い合わせ・貢献
- バグ報告や改善提案は Issue を作成してください。機能追加は事前に設計の相談をお願いします。

以上。README に不足している点や、特定の実行例（例: system_monitor の挙動や ExecutionEngine の API）について追加で説明が必要なら教えてください。