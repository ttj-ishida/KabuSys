KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買・研究・監視コンポーネント群を含む小規模なシステムです。  
ここにあるコードは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・リスク制御、研究用ファクター計算、AI を使ったニュースセンチメント評価などの主要機能で構成されています。

主な特徴
--------
- 実運用とペーパートレードを環境変数で切り替え可能（KABUSYS_ENV）
- ExecutionEngine（発注エンジン）と監視プロセスは別プロセス／DBで分離
- 監視機能:
  - SystemMonitor（CPU / メモリ / ディスク / データ鮮度 / 実行プロセス検出）
  - TradeMonitor（発注ログの監視、滞留注文・約定異常検出等）
  - RiskMonitor（ドローダウン・保有銘柄数の監視）
  - KillSwitch（重大リスク発生時に停止フラグを作成）
  - MonitoringEngine（上記を束ねてポーリング）
- ポートフォリオ構築:
  - 候補選定、等配分／スコア加重、ポジションサイズ計算、セクター上限・レジーム乗数
- 研究・分析:
  - DuckDB を使ったファクター計算（モメンタム／バリュー／ボラティリティ等）
  - 将来リターン・IC 計算・統計サマリ
- AI 統合:
  - OpenAI を使ったニュースのセンチメント評価（gpt-4o-mini 想定）
  - 市場レジーム判定（ETF + マクロニュースの LLM 評価）
- ツール:
  - Paper Trading の検証レポート生成スクリプト

セットアップ手順
----------------
※ ここでは一般的な手順を示します。実際の依存関係は requirements.txt 等を参照してください。

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install -r requirements.txt
   - 必須ライブラリ（主要な例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証のためにあると便利）
   - 注意: requirements.txt がない場合は上記を個別に入れてください。

4. 環境変数の初期設定
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告もエラー扱いになります

5. ディレクトリ作成（必要なら）
   - data/ や logs/ は自動作成されますが、パーミッション等で失敗する場合は手動で作成してください。

主要な環境変数（抜粋）
----------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 環境）
- LOG_LEVEL / LOG_DIR: ログ設定
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

使い方（起動コマンド）
--------------------
- 環境設定ウィザード（.env の作成/更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（実行エンジン）起動
  - python -m kabusys.run_execution
  - 備考: KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、data/paper_trading.db に記録されます。停止は data/stop_requested.flag を作成することで行えます。

- Monitoring（監視プロセス）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を常に利用します（環境に依らず）。

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH

停止・制御
---------
- ExecutionEngine の安全停止:
  - data/stop_requested.flag を作成するとループが検知して停止します（run_execution/run_monitoring 双方で使用）。
- Kill Switch:
  - 監視で重大なリスクが検出されたとき、data/kill.flag が生成されます（ExecutionEngine は起動時に確認・必要に応じてクリーンアップする）。
- PID ファイル:
  - data/execution.pid 等が書かれます（プロセス管理に利用）。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は主要なファイル・モジュールの概観（src/kabusys 以下）。実際のファイルはリポジトリを参照してください。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の自動ロード・Settings 定義
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py     — マクロ + ETF MA によるレジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite を使った監視ログの永続化層
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch のフラグ管理
    - monitoring_engine.py   — 複数モニタの統合ポーリング
    - (trade_monitor.py, alert_manager.py 等が想定される)
  - portfolio/
    - portfolio_builder.py   — 候補選定・等配分／スコア配分
    - position_sizing.py     — 発注株数計算・集約キャップ処理
    - risk_adjustment.py     — セクター上限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py     — モメンタム・バリュー・ボラティリティ計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
    - __init__.py
  - utils/
    - logging_setup.py       — 共通ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度／CPU affinity 設定ユーティリティ
    - __init__.py
  - (execution/* — ExecutionEngine 関連コンポーネント群)

設計上の注意点・運用ノウハウ
-------------------------
- .env は Git にコミットしないこと（config_setup のヘッダにも明記）。
- データベース:
  - monitoring（SQLite）は監視ログ用（デフォルト data/monitoring.db）。
  - DuckDB は分析用（デフォルト data/kabusys.duckdb）。
  - paper_trading モードでは発注系の DB を完全分離（PAPER_TRADING_SQLITE_PATH）。
- OpenAI を利用する機能は API キーが必須。API 呼び出しはリトライやフェイルセーフが組み込まれていますが、利用量には注意してください。
- ロギング:
  - setup_logging を各起動スクリプトで呼び出して統一的にログを出力します。LOG_DIR 環境変数で保存先を指定可。
- 監視は MONITOR_POLL_INTERVAL で間隔を制御可能。値が不正な場合はデフォルト 60 秒にフォールバックします。
- 本番環境（KABUSYS_ENV=live）では Kill Switch、LINE 通知等の設定を特に注意して下さい（validate_config にガードチェックあり）。

トラブルシューティング（簡易）
------------------------------
- .env の読み込みがうまくいかない:
  - プロジェクトルートの検出は .git か pyproject.toml を基準に行われます。配布後や特殊配置では自動ロードがスキップされる場合があります。手動で環境変数を設定してください。
- ログファイルが作成されない:
  - LOG_DIR のディレクトリ作成に失敗している可能性があります。パーミッションを確認するか、LOG_DIR を書き込み可能なパスに設定してください。
- OpenAI 関連で例外が発生する:
  - API キーの有無、ネットワーク、レート制限などを確認。ライブラリのバージョン差異にも注意してください。

ライセンス・貢献
----------------
- 本 README 上ではライセンス情報を省略しています。実際のリポジトリに LICENSE ファイルがある場合はそちらを参照してください。  
- バグ報告・プルリクエスト歓迎です。設計に関する議論は issue を立ててください。

以上がこのコードベースの概要と基本的な使い方です。個別のモジュールや API（例: ExecutionEngine の詳細な設定、BrokerClientFactory の実装など）については該当ファイルのドキュメント／コードコメントをご参照ください。