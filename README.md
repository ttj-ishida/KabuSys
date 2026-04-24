KabuSys — 日本株自動売買システム
=====================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
このリポジトリには、以下を含む主要コンポーネントが実装されています。

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（システム監視・アラート・Kill Switch）
- Research（ファクター計算・特徴量探索）
- AI モジュール（ニュース NLP / レジーム判定：OpenAI 利用）
- Portfolio（銘柄選定・配分・ポジションサイズ計算）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定管理）

目的は本番運用・ペーパートレード双方をサポートしつつ、テスト可能で安全性を考慮した設計を提供することです。

主な機能
---------
- Execution（発注）
  - 実際のブローカークライアントとペーパートレード用 MockBroker の切り替え（KABUSYS_ENV に依存）
  - OrderManager / RiskManager / Reconciler による堅牢な発注フロー
  - 発注イベントの永続化（SQLite: monitoring DB／ペーパートレード DB）

- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度を監視
  - TradeMonitor：滞留注文・約定異常等の監視（trade_logs を参照）
  - RiskMonitor：ドローダウン・ポジション上限の監視とリスクログ
  - KillSwitch：フラグファイルへの書き込みで ExecutionEngine を安全停止
  - MonitoringEngine：複数モニタをまとめて定期ポーリング

- Research / Portfolio
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計要約
  - 銘柄選定・重み計算・ポジションサイズ算出（単元株丸め・投下資金制限等）

- AI（OpenAI）
  - news_nlp: ニュースをまとめて LLM に投げ、銘柄別センチメントを ai_scores に記録
  - regime_detector: ETF（1321）の MA とマクロニュースを組合せ、市場レジーム（bull/neutral/bear）判定

- ユーティリティ
  - ログ設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - .env 対話式ウィザードと設定検証 CLI

セットアップ
-----------
1. Python（3.9+ を想定）をインストールし、仮想環境を作成・有効化します。
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 依存パッケージをインストールします（必要に応じて追加してください）。
   - 必要パッケージ（主なもの）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     pip install duckdb psutil openai PyYAML

   注: sqlite3 は標準ライブラリ、その他一部のユーティリティは標準で動作します。

3. .env を用意します（自動ロード機構あり）
   - 対話式ウィザードで生成する:
     python -m kabusys.config_setup
   - あるいはルートに .env を手動作成して必要な環境変数を設定してください。

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨／任意の環境変数（一部）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視用 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時に使用）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定モード）
- KILL_FLAG_CLEAR_ON_START: 0/1（Execution 起動時の kill.flag 自動クリア）

自動 .env 読み込み
- プロジェクトルート（.git または pyproject.toml がある場所）を基準に .env を自動読み込みします。
- OS 環境変数が優先され、.env.local は .env を上書きします。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

設定検証
- .env と config/*.yaml の基本チェックを CLI で実行できます:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

使い方（主要エントリポイント）
--------------------------------
- 起動（ExecutionEngine）
  - 本番またはペーパートレードの発注エンジンを起動します。
  - 実行:
    python -m kabusys.run_execution
  - 注:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
    - 起動直後に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中に data/stop_requested.flag を作成するとエンジンは安全に停止します。
    - ExecutionEngine の PID はデフォルトで data/execution.pid に書かれます（Settings.pid_file_path）。

- 監視プロセス（Monitoring）
  - 定期的に各種モニタを実行し、ログ・アラート・Kill Switch などを管理します。
  - 実行:
    python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書きできます（デフォルト 60 秒）。
  - 監視プロセスは KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを書き込みます。
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループを終了します。

- 設定ウィザード
  - .env の初期作成・更新:
    python -m kabusys.config_setup

- Paper Trading 検証レポート
  - ペーパートレード DB を集計して品質指標（稼働率・約定率・レイテンシ等）を出力:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

ログ・PID・フラグファイル
------------------------
- ログ:
  - デフォルト logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション 30 日保持）
  - コンソールには stdout に出力されます。

- PID ファイル:
  - ExecutionEngine は Settings.pid_file_path（デフォルト data/execution.pid）に PID を書きます。

- 停止フラグ:
  - data/stop_requested.flag : run_execution / run_monitoring が監視している停止トリガ（両方に共通）
  - data/kill.flag : KillSwitch が書き込むファイル（ExecutionEngine に対する緊急停止シグナルとして機能）

ディレクトリ構成（主なファイル）
------------------------------
リポジトリのソースは src/kabusys 以下に配置されています。主要なモジュールとファイルを抜粋します。

- src/kabusys/
  - __init__.py                       — パッケージ定義（バージョン等）
  - config.py                         — 環境変数 / 設定管理（Settings クラス）
  - config_setup.py                   — .env 対話式ウィザード
  - validate_config.py                — 設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py                     — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py              — レジーム判定（MA + マクロニュース + OpenAI）
  - monitoring/
    - monitoring_db.py                — SQLite 監視 DB の初期化と抽象化クラス
    - system_monitor.py               — システム/データ鮮度監視
    - trade_monitor.py                — 注文関連の監視（trade_logs）
    - risk_monitor.py                 — ドローダウン / ポジション上限監視
    - kill_switch.py                  — Kill Switch（フラグファイル）
    - monitoring_engine.py            — モニタ群を束ねるエンジン
    - alert_manager.py                — （アラート送信ロジック、実装による）
  - execution/
    - execution_engine.py             — 発注エンジン本体
    - broker_factory.py               — ブローカークライアント生成
    - order_manager.py                — 注文管理
    - order_repository.py             — 注文永続化
    - reconciler.py                   — 注文照合
    - risk_manager.py                 — リスク判定
  - portfolio/
    - portfolio_builder.py            — 候補選定・重み計算
    - position_sizing.py              — 株数決定ロジック（単元丸め・cap）
    - risk_adjustment.py              — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py              — ファクター計算（momentum/value/volatility）
    - feature_exploration.py          — IC / 将来リターン / 統計
  - tools/
    - paper_verification_report.py    — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py                — ロギング初期化ユーティリティ
    - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ

注意事項 / 運用上のヒント
-----------------------
- 本番運用時は必ず KABUSYS_ENV=live を設定し、.env の中身（APIキー等）を慎重に管理してください。
- validate_config を使って設定を事前チェックしてください（--strict モードあり）。
- Monitoring は監視ログに本番 sqlite_path を使用します（run_monitoring は KABUSYS_ENV に依存しません）。
- ペーパートレードは本番 DB と完全分離されるよう PAPER_TRADING_SQLITE_PATH を設定して利用してください。
- OpenAI を利用する機能（news_nlp / regime_detector）では API 呼び出しの失敗に対してリトライとフォールバック（ゼロスコア）を行い、致命的な失敗にならないよう配慮していますが、APIキーの管理・コストには注意してください。
- process_priority の設定は OS 権限により失敗することがあります（警告のみで継続します）。

サンプル .env（最小）
--------------------
# 以下は最低限の例（実際のトークンは置き換えてください）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

貢献
----
- バグ報告・プルリク歓迎です。設計上の意図や API 変更は README に明記してください。
- セキュリティ上の問題は公開 issue ではなく直接連絡してください（公開鍵等の管理が必要な場合があります）。

ライセンス
---------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（存在する場合）。

以上。必要があれば「各モジュールの詳細な API ドキュメント」や「運用手順（デプロイ/監視/復旧）」の追加ドキュメントを作成します。どの章を詳しく作れば良いか教えてください。