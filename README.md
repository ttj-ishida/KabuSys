# KabuSys — 日本株自動売買システム

概要
- KabuSys は日本株向けの自動売買／研究／監視を目的とした Python コードベースです。
- 株価データ集計（DuckDB）・SQLite による監視ログ・ExecutionEngine（発注処理）・リスク監視・AI を用いたニュースセンチメント評価などのコンポーネントを備えています。
- 設定は .env（および .env.local）で管理し、KABUSYS_ENV によって動作モード（development / paper_trading / live）が切り替わります。

主な機能
- ExecutionEngine（発注・注文管理・リスク制御）
  - 本番 / ペーパートレード切替（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し DB を分離）
  - PID ファイル出力・停止フラグ監視（data/execution.pid, data/stop_requested.flag）
- 監視（Monitoring）
  - SystemMonitor: プロセス生存・CPU/メモリ/ディスク利用率・データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、kill.flag 発行
  - MonitoringEngine: 上記を定期実行し、アラート送信（AlertManager 経由）
- 環境設定 / 検証
  - 対話式ウィザードで .env を作成（kabusys.config_setup）
  - 起動前チェック（必須環境変数・config/*.yaml 等の検証、kabusys.validate_config）
- 研究・ポートフォリオ構築
  - ファクター計算（momentum / volatility / value 等）
  - 特徴量探索（forward returns / IC / summary）
  - ポートフォリオ選定・重み計算・ポジションサイズ決定（等金額・スコア重み・リスクベース）
  - セクター制限・レジーム乗数
- AI（OpenAI）連携
  - ニュースセンチメント（gpt-4o-mini）を銘柄ごとにスコア化して ai_scores に格納
  - 市場レジーム判定（ETF MA とマクロニュースの LLM 評価を合成）
- ユーティリティ
  - プロセス優先度・CPU affinity 設定（psutil ベース）
  - ペーパートレード検証レポート生成ツール

要求事項（主なライブラリ）
- Python 3.9+（タイプヒント等を考慮）
- duckdb
- psutil
- openai（AI 機能利用時）
- PyYAML（設定ファイル検証時：任意）
- SQLite（組み込み）

簡単セットアップ手順
1. リポジトリをクローン / 取得
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 設定検証で YAML を使う場合: pip install pyyaml
   - （推奨）requirements.txt がある場合は pip install -r requirements.txt
4. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - 手動で .env を作る場合は .env.example を参考に必要な環境変数を設定
   - 自動ロード: kabusys.config がプロジェクトルート（.git または pyproject.toml）を検出すると .env / .env.local を自動で読み込みます。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- OPENAI_API_KEY（AI 機能利用時）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db） — Monitoring は環境に関わらずこの sqlite_path を使用します
- PAPER_TRADING_SQLITE_PATH（paper_trading モード用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject、デフォルト: instant）
- LOG_LEVEL（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用、任意）
- KILL_FLAG_CLEAR_ON_START（本番での自動 kill.flag クリア。0 推奨）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒。デフォルト 60 秒。環境変数で上書き可能）

起動・使い方（主要なエントリポイント）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - オプション: --strict（警告も失敗扱い）
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作:
    - プロセス優先度を "high" に設定（psutil により OS に依存）
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離
    - 実行中に data/stop_requested.flag が存在するとエンジンを停止します
    - PID ファイル (data/execution.pid) を生成
- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可（デフォルト 60 秒）
    - Monitoring は KABUSYS_ENV にかかわらず設定の sqlite_path を使用（監視ログは本番用 DB に記録）
    - 停止は data/stop_requested.flag による
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --db <path> --from YYYY-MM-DD --to YYYY-MM-DD
  - 環境変数 PAPER_TRADING_SQLITE_PATH を使う場合は --db を省略可能
- AI 機能（ニューススコア・レジーム判定）
  - kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime を呼び出して利用
  - OPENAI_API_KEY 必須。API の呼び出しはリトライやフォールバックを備えています。

停止フラグ / Kill Switch
- run_execution / run_monitoring は停止用のフラグファイル（data/stop_requested.flag）を監視して安全に停止します。
- KillSwitch（監視側）は data/kill.flag に理由を書き込み、ExecutionEngine 側で読んで停止させる仕組みがあります（設定は Settings.kill_flag_path）。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では 0（非クリア）を推奨します。

設定ファイルの自動読み込みルール
- 自動読み込みは以下の優先順（OS 環境変数を最優先）:
  1. OS 環境変数
  2. .env.local（既存の OS 環境変数は保護）
  3. .env
- 自動読み込みを無効にする場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

ディレクトリ構成（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / .env ロードロジック、Settings クラス
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 起動前チェック CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py  — ペーパートレード検証レポート
    - ai/
      - news_nlp.py             — ニュースを LLM でスコアリングして ai_scores に書き込み
      - regime_detector.py      — 市場レジーム判定
    - monitoring/
      - monitoring_db.py        — SQLite 監視ログ永続化層 + MonitoringDB ラッパ
      - monitoring_engine.py    — モニタ群を束ねるエンジン
      - system_monitor.py       — システム状態 / データ鮮度監視
      - trade_monitor.py        — 注文滞留 / 約定異常監視
      - risk_monitor.py         — ドローダウン / ポジション上限監視
      - kill_switch.py          — kill.flag 書き込みロジック
      - alert_manager.py        — （未表示部分）アラート送信管理
    - execution/
      - order_manager.py
      - order_repository.py
      - execution_engine.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
      - order_record.py
      （実装に応じた発注・リスク制御ロジック）
    - research/
      - factor_research.py      — ファクター計算（momentum/volatility/value）
      - feature_exploration.py  — 将来リターン / IC / summary 等
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - utils/
      - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - data/ (実行時に作成されることが想定)
      - execution.pid
      - stop_requested.flag
      - kill.flag
      - monitoring.db / paper_trading.db など

注意事項 / 運用上のポイント
- Monitoring は監視ログを本番 sqlite_path に書き込みます。環境にかかわらず同じ sqlite_path を使うため、権限やパスの設定に注意してください。
- paper_trading モードでは paper_trading 用の SQLite を使用して本番 DB と完全分離することを想定しています（PAPER_TRADING_SQLITE_PATH）。
- OpenAI を使う処理は API キーの管理と利用コストに注意してください。API 呼び出しはリトライ・フェイルセーフを備えていますが、過度の呼び出しは費用とレート制限に繋がります。
- .env は機密情報（API トークン等）を含むため、絶対にバージョン管理システムにコミットしないでください。
- 実行ユーザーがプロセス優先度を変更する権限を持っている必要があります（psutil の挙動は OS と権限に依存）。

トラブルシューティングのヒント
- 設定検証:
  - python -m kabusys.validate_config で起動前に必須環境変数やファイルパス、YAML のパースをチェックできます。
- ログ:
  - 各スクリプトは logging.basicConfig(level=logging.INFO) で INFO レベルのログを出力します。必要に応じて LOG_LEVEL を変更してください。
- 停止:
  - 強制終了したい場合は data/stop_requested.flag を作成すると run_execution/run_monitoring が安全に停止します。監視が kill.flag を書いた場合、ExecutionEngine 側でその flag を検出して停止する設計になっています。

代表的なコマンド例
- 環境ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- エンジン起動（ペーパートレード設定済み）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- 監視開始（ポーリング間隔 30 秒に変更）:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

その他
- コード内ドキュメント（docstring）に各関数・クラスの設計意図やフォールバック / フェイルセーフの挙動が詳述されています。実運用前に validate_config と実行時ログを確認し、環境固有のパスや API キー周りを十分にセットアップしてください。

README の内容や補足情報をプロジェクト特有の要件（デプロイ手順、監視ターゲット、LINE 通知設定方法など）に合わせて拡張できます。必要があれば運用手順書（デプロイ / 監視 / 障害時対応フロー）も作成します。