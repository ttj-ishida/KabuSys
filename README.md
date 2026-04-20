KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買（バックテスト／ペーパートレード／本番運用）を想定した
モジュール群です。以下の主要機能を持ち、実運用を念頭に設計されています。

- 注文実行エンジン（ExecutionEngine）
- 監視・アラート基盤（Monitoring）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング）
- リスク監視（ドローダウン・保有上限など）
- リサーチ用ファクター計算、特徴量解析
- ニュースNLP（OpenAI を利用したセンチメント集約）
- 市場レジーム判定（MA + LLM）
- 開発支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

主な設計方針
- 環境変数ベースの設定（.env をサポート）。config_setup で対話式に生成可能。
- DuckDB（分析データ）と SQLite（監視・ペーパートレード用）を併用。
- 実運用を意識したログ出力（stdout + 日次ローテートファイル）・プロセス優先度調整。
- OpenAI（ニュース・レジーム判定）との連携機能あり（APIキー必須）。

機能一覧
--------
- 実行関連
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し専用 DB に記録。
- 監視関連
  - run_monitoring.py: SystemMonitor をポーリング起動。監視結果は SQLite に保存。
  - monitoring_engine.py, system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, alert_manager（アラート連携は設定に応じて実装）
- ポートフォリオ構築
  - portfolio_builder: 候補選定、等重/スコア重み付け
  - position_sizing: 株数計算、上限・単元丸め、aggregate cap
  - risk_adjustment: セクター上限・レジーム乗数
- リサーチ
  - research.factor_research: モメンタム/ボラティリティ/バリューの計算（DuckDB）
  - research.feature_exploration: 将来リターン / IC / 統計サマリ
- AI（LLM）関連
  - ai.news_nlp: 銘柄ごとのニュースを集約して OpenAI でセンチメント化して ai_scores に書き込み
  - ai.regime_detector: ETF MA とマクロセンチメントを合成して日次レジーム判定
- ツール
  - config_setup.py: .env を対話で作るウィザード
  - validate_config.py: 起動前チェック（必須環境変数 / YAML / パス等）
  - tools.paper_verification_report: ペーパートレード結果のサマリと合否判定

前提 / 必要環境
--------------
- Python 3.10 以上（PEP 604 の Union 型表記や型ヒント表現を利用）
- 必要な外部パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - pyyaml（設定ファイル検証で任意）
- 任意：Git（プロジェクトルート検出に使用）
- OS：Linux / macOS / Windows（process_priority でプラットフォーム差分に対応）

インストール（例）
-----------------
1. リポジトリをクローンして作業ディレクトリへ
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存をインストール（requirements.txt が無ければ個別インストール）
   - pip install duckdb psutil openai pyyaml

設定（.env）
-----------
プロジェクトルートに .env を置くか、対話ウィザードを使って生成します。

推奨フロー:
1. .env を初期作成（対話式）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（.env.example を参照して設定）

主要な環境変数（一部）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring の上書き用）

デフォルトのファイル・フラグ
- data/execution.pid: ExecutionEngine の PID ファイル（実行時に使用）
- data/kill.flag: Kill Switch（監視が検出するとこのファイルを書き、Execution を停止させる）
- data/stop_requested.flag: run_monitoring / run_execution による停止制御（外部で作成するとループを終了）

使い方
------
基本的なコマンド例:

- 環境設定ウィザード（.env を作る）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- ExecutionEngine（注文実行）起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV によって挙動が変わります（paper_trading では MockBroker）
  - ペーパートレードは PAPER_TRADING_SQLITE_PATH に記録され、本番 DB と分離されます

- Monitoring 起動（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で指定可能（デフォルト 60）
  - python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH を上書き）

- AI 関連（プログラム内で呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=...)  # raw_news → ai_scores を更新
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

ログ
----
ログは以下の仕様で出力されます:
- コンソール（stdout）に常に出力
- 日次ローテーションファイル出力: logs/<app_name>.log
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に初期化されます

停止・Kill Switch
-----------------
- 監視モジュールはドローダウンやポジション上限等の条件で kill.flag を生成します。
- 実行エンジンは起動時および起動中に kill.flag / stop_requested.flag をチェックして安全に停止します。

ディレクトリ構成（主なファイル）
-------------------------------
以下は src/kabusys 以下の主要構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト

  - ai/
    - news_nlp.py            — ニュースセンチメント化（OpenAI）
    - regime_detector.py     — 市場レジーム判定
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み
    - position_sizing.py     — 株数決定 / キャップ
    - risk_adjustment.py     — セクター制限 / レジーム乗数
  - research/
    - factor_research.py     — モメンタム/ボラ/バリュー計算（DuckDB）
    - feature_exploration.py — IC・統計処理
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / 永続化層
    - system_monitor.py      — システム監視（CPU/メモリ/データ鮮度）
    - trade_monitor.py       — 注文監視（trade_logs の整合性など）
    - risk_monitor.py        — ドローダウン・ポジション監視
    - monitoring_engine.py   — 各 monitor を束ねる
    - kill_switch.py         — kill.flag 書込みユーティリティ
    - alert_manager.py       — アラート送信（実装に応じて拡張）
  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py       — 監視 DB スキーマ（上記）
  - tools/
    - paper_verification_report.py — Paper Trading のレポート生成
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

実運用上の注意
--------------
- KABUSYS_ENV=live は実際に発注を行います。設定（APIキー・パスワード・LINE通知等）を慎重に行ってください。
- .env は決してリポジトリにコミットしないでください（README ヘッダにも注意書きを生成する仕組みあり）。
- OpenAI API を用いる処理はコストとレイテンシが発生します。APIキーとレート制限に注意してください。
- SQLite / DuckDB のバックアップ・永続化戦略を運用前に検討してください。

貢献
----
バグ修正や改善提案は Pull Request を歓迎します。大きな設計変更前には Issue を立てて議論してください。

ライセンス
----------
リポジトリ内の LICENSE を参照してください（本 README の例ではライセンス表記は付与していません）。

以上が簡易 README です。必要なら「設定例の .env テンプレート」「起動時のデバッグ手順」や「開発用の Docker / systemd ユニット例」など、さらに具体的なセクションを追加できます。どの情報を補足しますか？