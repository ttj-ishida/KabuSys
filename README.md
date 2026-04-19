# KabuSys

日本株向けの自動売買システム（ライブラリ兼実行スクリプト群）

このリポジトリは、戦略のリサーチ／ファクター計算、ポートフォリオ構築、発注実行（paper/live 切替可）、監視・アラート、そして AI を使ったニュース解析／レジーム判定などのコンポーネントで構成された自動売買フレームワークです。

- 言語: Python
- 目標 Python バージョン: 3.10+
- 主な外部依存: duckdb, psutil, openai, (オプション) PyYAML

以下にプロジェクト概要、機能一覧、セットアップ、使い方、主要ファイル・ディレクトリ構成を日本語でまとめます。

プロジェクト概要
- モジュール化された自動売買基盤：
  - リサーチ / ファクター計算（DuckDB 上の履歴データを参照）
  - ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算）
  - ExecutionEngine（発注ロジック・リスク管理・注文管理） — paper_trading と live の切替対応
  - 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch（data/kill.flag）
  - AI モジュール（ニュース NLP によるセンチメント、レジーム判定） — OpenAI を利用
  - 各種ユーティリティ（ロギング設定、プロセス優先度設定など）
- データ永続化：
  - 監視ログ等: SQLite（デフォルト data/monitoring.db）
  - 分析用: DuckDB（デフォルト data/kabusys.duckdb）
  - ペーパートレードの発注履歴は本番 DB から分離され、data/paper_trading.db を使用可能

主な機能一覧
- CLI / スクリプト
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証ツール: python -m kabusys.validate_config [--strict]
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視ループ起動: python -m kabusys.run_monitoring
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額・スコア加重配分
  - ポジションサイズ決定（risk_based / equal / score）
  - セクター上限適用、レジーム乗数
- 研究・分析
  - モメンタム / ボラティリティ / バリューファクター算出（DuckDB SQL ベース）
  - 将来リターン、IC 計算、統計サマリ（外部ライブラリ非依存）
- AI（OpenAI）
  - news_nlp: ニュース記事を集約して LLM で銘柄ごとセンチメント評価し ai_scores に書込
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM 結果を合成して市場レジーム判定
- 監視・リスク管理
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存チェック
  - TradeMonitor / RiskMonitor: 滞留注文、約定異常、ドローダウン、ポジション上限チェック
  - KillSwitch: しきい値到達時に data/kill.flag を書き込み ExecutionEngine を停止させる

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須 (最低限):
     - pip install duckdb psutil openai
   - 開発・便利ツール:
     - pip install PyYAML  （validate_config が config/*.yaml を検証する場合に必要）
   - （プロジェクトに requirements.txt がある場合はそれを利用してください）
     - pip install -r requirements.txt

4. .env を作成する
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - ウィザードで生成された .env をプロジェクトルートに保存してください。
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - KABUSYS_ENV（development|paper_trading|live、デフォルト development）
   - データベースパス（デフォルト値）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1)

6. データディレクトリの作成（自動で作られることが多いが確認）
   - mkdir -p data logs

実行 / 使い方（代表的なコマンド）
- 実行エンジン（発注）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し発注は paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が立っていれば起動をスキップ
    - 停止は data/stop_requested.flag を作成するか kill.flag による Kill Switch が発動する
    - 実行中は data/execution.pid に PID を書く（設定経由）

- 監視ループ
  - python -m kabusys.run_monitoring
  - 動作:
    - SystemMonitor / RiskMonitor 等を定期実行し、監視ログを SQLite に記録
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
    - 監視は本番 sqlite_path を使用（監視は環境に関わらず同一 DB を参照）

- 設定ウィザード
  - python -m kabusys.config_setup
  - 対話的に .env を生成・更新します

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で PAPER_TRADING_SQLITE_PATH を直接指定可能

環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時の分離 DB）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログディレクトリ（デフォルト logs）
- MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- KILL_FLAG_PATH: data/kill.flag のパス（Settings.kill_flag_path）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除するか（1=クリア、0=クリアしない）

ログ
- ログ設定ユーティリティ（kabusys.utils.logging_setup）を利用して統一的にログを出力
- デフォルト: stdout に出力し、logs/<app_name>.log に日次ローテートで保存（30 日保持）
- ログレベルは引数/環境変数 LOG_LEVEL で制御

停止・Kill Switch の仕組み
- 監視モジュール（MonitoringEngine／KillSwitch）はリスク閾値に達すると data/kill.flag を作成します
  - ExecutionEngine は kill.flag の存在を検知して安全に停止します
- run_*.py には data/stop_requested.flag を用いた手動停止（外部からファイルを作成してループを止める）もあります

注意事項 / 運用上のポイント
- set_process_priority（高優先度設定）は OS 権限に依存するためアクセス権限が必要な場合があります。失敗しても警告が出ますが処理は継続します。
- OpenAI を利用する機能は API キーが必須で、レート制限・エラー時はリトライやフォールバック処理が実装されていますが、運用時はコスト・制限に注意してください。
- 本番（KABUSYS_ENV=live）では kill_flag_clear_on_start を 0 にしておくことを推奨（誤って自動クリアされると Kill Switch が無効化される可能性があります）。
- validate_config で PyYAML がない場合は config/*.yaml の検証がスキップされます（警告が出ます）。

主要ディレクトリ・ファイル構成（src/kabusys）
- __init__.py
- config.py: 環境変数/.env の読み込み・Settings クラス（主要設定をプロパティとして提供）
- config_setup.py: .env 作成ウィザード（対話式）
- validate_config.py: 設定検証 CLI（環境変数と config/*.yaml のチェック）
- run_execution.py: ExecutionEngine 起動スクリプト（paper_trading 切替、PID/stop フラグ管理）
- run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で制御）

- portfolio/
  - portfolio_builder.py: 候補選定、等分・スコア加重配分
  - position_sizing.py: 発注株数計算（リスクベース等）
  - risk_adjustment.py: セクター制限、レジーム乗数

- research/
  - factor_research.py: Momentum/Volatility/Value 等のファクター計算（DuckDB を SQL で参照）
  - feature_exploration.py: 将来リターン、IC、統計サマリ

- ai/
  - news_nlp.py: ニュース記事を OpenAI で評価し ai_scores に書込む
  - regime_detector.py: マクロニュース + ETF MA による市場レジーム判定

- monitoring/
  - monitoring_db.py: SQLite スキーマ定義および永続化ユーティリティ（MonitoringDB クラス）
  - system_monitor.py: システム・データ鮮度監視ロジック
  - risk_monitor.py: ドローダウン / ポジション上限チェック
  - monitoring_engine.py: 各 monitor を束ねて定期実行するエンジン
  - kill_switch.py: kill.flag の書込み・管理ロジック
  - trade_monitor.py / alert_manager.py （注文監視・アラートは同ディレクトリに存在）

- utils/
  - logging_setup.py: ルートロガーの統一セットアップ（stdout + 日次ローテートファイル）
  - process_priority.py: プロセス優先度 / CPU affinity の簡易ラッパー

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成スクリプト

開発・拡張のヒント
- DuckDB 接続を渡して純粋関数的にファクターを計算する設計のため、テストがしやすく、データソースを差し替えて検証可能です。
- AI モジュールは外部 API の呼び出しを明確に分離し、レスポンス検証・リトライ・クリップ等の堅牢化処理を備えています。OpenAI SDK のバージョン差に注意してモック化・テストを行ってください。
- monitor / execution 間はファイルフラグ（kill.flag / stop_requested.flag）で疎結合に設計されています。運用時は flag ファイルの管理ポリシーを明確にしてください。

ライセンス・貢献
- README にライセンス情報が無い場合はリポジトリルートの LICENSE を参照してください。
- バグ報告・機能提案は issue を立ててください。

以上が本リポジトリの README 相当の概要です。README.md に書き起こす際は、実際の requirements.txt / LICENSE / CONTRIBUTING などプロジェクト固有のファイルがあればそれらも追記してください。必要であれば README のドラフトをマークダウン形式で作成します。どのレベルの詳細（例: 実行例のコマンド列、.env の例、DB スキーマ抜粋など）を含めたいか指示ください。