KabuSys — 日本株自動売買システム（リポジトリ README）
概要
本リポジトリは日本株の自動売買システム KabuSys の Python コードベースです。  
主な目的はシグナル生成 → ポートフォリオ構築 → 発注実行 → 監視／リスク制御までを含む一連の処理を提供することです。  
（この README は src/kabusys 以下の主要モジュール群をベースにした開発者向けの概要・セットアップ・使い方ドキュメントです。）

特徴（抜粋）
- 実行エンジン（ExecutionEngine）と監視エンジン（MonitoringEngine）を分離した設計
- Paper Trading（モックブローカー）と Live（実ブローカー）を環境切替でサポート
- DuckDB（時系列・分析用）、SQLite（監視・発注ログ用）を併用したデータ管理
- AI モジュール（OpenAI）を使ったニュースセンチメント評価・レジーム判定機能
- ログ出力の統一（Console + 日次ローテートファイル）
- Kill Switch（フラグファイル）やリスク監視（ドローダウン、ポジション上限）による自動停止機構
- Paper Trading 検証レポート生成スクリプト

必須環境・依存パッケージ（代表）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の検証を行う場合）
- その他: sqlite3（標準ライブラリ）、logging 等

（実際の requirements.txt がある場合はそちらを使用してください。ない場合は pip で上記パッケージをインストールしてください。）

主な環境変数（代表）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: execution 環境（development / paper_trading / live）。デフォルト: development
- OPENAI_API_KEY: OpenAI を使う場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant, partial, never, reject）
- PID_FILE_PATH / KILL_FLAG_PATH 等（デフォルトは data フォルダ下のファイル）

セットアップ手順（開発環境向け・クイックスタート）
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成して有効化（例）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール
   pip install duckdb psutil openai pyyaml
   （requirements.txt があればそれを使用してください）
   pip install -r requirements.txt

4. .env の作成（対話式ウィザード）
   python -m kabusys.config_setup
   - このスクリプトは .env の生成・更新を対話形式で補助します。
   - 必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください。

5. 設定の検証
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. 初回実行前に data/ ディレクトリを作成（必要に応じて）
   mkdir -p data logs

起動・使い方（代表コマンド）
- 監視ループ起動（SystemMonitor）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視はいかなる KABUSYS_ENV においても本番 sqlite_path を使用します（監視ログは常に本番 DB に保存）。

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動中は data/execution.pid に PID が保存され、data/stop_requested.flag が作成されると停止します。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能（または --db オプション）。

- 設定検証（前述）
  python -m kabusys.validate_config [--strict]

停止・Kill Switch
- 監視/実行系はフラグファイルや PID を使って制御します。
  - data/stop_requested.flag: 実行ループ（monitoring / execution）を終了させる外部停止フラグ（run_*.py が監視）
  - data/kill.flag: KillSwitch により作成される停止フラグ（ExecutionEngine 停止トリガ）
  - PID ファイル: data/execution.pid（ExecutionEngine の PID 保存先、デフォルト）

内部コンポーネント（主なモジュール）
- config.py: 環境変数の読み込み・Settings クラス（自動 .env ロード・検証付き）
- config_setup.py: .env を対話式で作成するウィザード
- validate_config.py: 起動前の設定検証ツール（必須 env 変数・DB パス・YAML の存在等）
- run_execution.py: ExecutionEngine 起動スクリプト（paper_trading 時は専用 DB を使用）
- run_monitoring.py: SystemMonitor のポーリング実行スクリプト
- monitoring/
  - monitoring_db.py: SQLite に対する永続層（テーブル作成・CRUD）
  - system_monitor.py: CPU/メモリ/Disk/プロセス監視、データ鮮度チェック
  - trade_monitor.py（存在）: 発注ログの監視（滞留・異常約定など）
  - risk_monitor.py: ドローダウン・ポジション上限の監視
  - kill_switch.py: Kill Switch（フラグファイル書き込み）ロジック
  - monitoring_engine.py: 各 Monitor を束ねるポーリングエンジン
  - alert_manager.py（存在）: アラート送信管理（LINE 等）
- execution/（発注関連: Engine, BrokerFactory, OrderManager 等 — 実際の実装は該当ファイル群）
- portfolio/
  - portfolio_builder.py: 候補選定とスコアソート
  - position_sizing.py: 株数決定・丸め処理・投下上限調整
  - risk_adjustment.py: セクター上限・レジーム乗数
- research/
  - factor_research.py: Momentum / Volatility / Value 等ファクター計算（DuckDB 経由）
  - feature_exploration.py: 将来リターン・IC・統計サマリー
- ai/
  - news_nlp.py: ニュースセンチメント評価（OpenAI を呼び出して ai_scores を書き込み）
  - regime_detector.py: ETF MA とマクロニュースを組み合わせた市場レジーム判定（OpenAI 利用）
- utils/
  - logging_setup.py: ルートロガーの統一セットアップ（stdout + 日次ファイルローテート）
  - process_priority.py: プロセス優先度・CPU affinity ユーティリティ（Windows/Linux 対応）
- tools/
  - paper_verification_report.py: Paper Trading の検証レポート出力

ディレクトリ構成（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - ...
    - ai/
      - news_nlp.py
      - regime_detector.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - tools/
      - paper_verification_report.py
    - ...（execution, data, strategy 等のパッケージ）

実運用上の注意・運用メモ
- KABUSYS_ENV は重要: paper_trading と live では DB やブローカー挙動が異なります。必ず本番（live）での動作を入念に検証してください。
- Kill Switch（kill.flag）は本番保護の重要機構です。KILL_FLAG_CLEAR_ON_START を本番で 1 にするのは危険です（自動クリアされてしまうため）。
- OpenAI を用いる機能は API キーの課金対象になります。API コール回数と失敗時の動作に注意してください（失敗時はフェイルセーフでスコア=0 等にフォールバックする実装がなされています）。
- ログはデフォルト logs/ に日次ローテートで出力されます。ログディレクトリが作成できない場合はコンソールのみ出力されます。
- SQLite／DuckDB のファイルパスは .env で設定できます。バックアップや適切なファイル配置を検討してください。

トラブルシューティング（よくある項目）
- .env が読み込まれない/環境変数が足りない:
  python -m kabusys.validate_config で問題点を確認してください。
- ログディレクトリ作成エラー:
  権限やパスを確認し、必要なら LOG_DIR を .env で指定してください。
- OpenAI 周りの例外:
  OPENAI_API_KEY の設定、ネットワーク、レート制限に留意。ライブラリのバージョン差による挙動変化にも注意。

貢献・開発ガイドライン（簡易）
- 新しい依存を追加したら requirements.txt を更新してください。
- DB スキーマ変更は monitoring_db.init_monitoring_db にマイグレーション処理を追加すること（既存 DB 互換性を保つ）。
- 設定項目は config_setup と validate_config に反映させてください。

最後に
この README はコードベースの主要な使用法と構成を簡潔にまとめたものです。詳細な設計や仕様（StrategyModel.md、PortfolioConstruction.md 等の設計文書）がある場合はそちらを参照してください。必要であれば README を拡張してデプロイ手順や systemd / Docker / k8s の実行例も追記できます。ご要望があれば追加します。