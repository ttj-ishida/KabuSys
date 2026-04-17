# KabuSys

日本株自動売買システム KabuSys の簡易ドキュメント（README）。  
このリポジトリは戦略・ポートフォリオ構築、実行エンジン、監視、研究ツール、AI 統合などを含むモジュール群で構成されています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動コマンドの例）
- 環境変数（主要項目）
- ファイル・ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けの自動売買フレームワークです。
- 戦略のリサーチ／ファクター計算（DuckDB ベース）、ポートフォリオ構築、ポジションサイジング、実行エンジン、監視（Monitoring）および AI（ニュース NLP、レジーム検出）を含みます。
- Paper Trading（ペーパートレード）モードと Live（本番）モードを区別して動作します。Paper Trading では MockBrokerClient を利用して本番データベースと分離された専用 SQLite に記録します。

---

主な機能一覧
- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートに基づく）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 起動前検証ツール（kabusys.validate_config）
- 実行・発注
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading と Live を切替可能（環境変数 KABUSYS_ENV）
  - リスク管理（RiskManager）やオーダーリポジトリ等の統合
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログ永続化（SQLite、monitoring_db）
  - Kill Switch（フラグファイルにより実行エンジン停止）
  - run_monitoring.py による定期ポーリング（ポーリング間隔は環境変数で上書き可能）
- ポートフォリオ構築（純関数）
  - 候補選定、等重／スコア重み、セクター制限、レジーム調整、株数算出（単元丸め）
- 研究用モジュール
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（情報係数）、統計サマリー
- AI 統合
  - ニュース記事を OpenAI（gpt-4o-mini 等）でセンチメント評価し ai_scores に格納
  - マクロニュース + MA200 を合成して市場レジーム判定（regime_detector）
- ツール
  - Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

セットアップ手順（開発環境向け）
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python >= 3.10 推奨
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要な外部ライブラリ（主なもの）
     - duckdb
     - psutil
     - openai
     - PyYAML（config/*.yaml の検証に任意で使用）
   - 例（pip）:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを利用してください（本リポジトリ例では含まれていないため個別にインストール）。

3. 環境変数ファイル (.env) を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動でルートの .env を作成。重要なキー:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能利用時に必須）
     - その他: LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID 等

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1) になります

5. 必要に応じてデータディレクトリを作成
   - data/ ディレクトリや各 DB ファイルの親ディレクトリを事前に作成しておくと良い

---

使い方（起動コマンド例）
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 起動時、data/stop_requested.flag が存在すると起動せず終了
    - 実行中に data/stop_requested.flag を作成するとエンジン停止をトリガー
    - 実行時に data/execution.pid が作成される（PID ファイル）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 備考:
    - 監視は monitoring DB（Settings.sqlite_path）を使用（環境にかかわらず本番 sqlite_path を参照）
    - data/stop_requested.flag が存在するとループを終了

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を指定するか、環境変数 PAPER_TRADING_SQLITE_PATH を設定

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定して、該当モジュール（kabusys.ai.news_nlp.score_news / kabusys.ai.regime_detector.score_regime）をプログラム内から呼び出す
  - CLI スクリプトは付属していませんが、Python から直接実行可能です

---

重要な環境変数（主要項目・デフォルト）
- KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト "development"
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時の専用 DB）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject、デフォルト "instant"）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（開発向け、0/1）

自動 .env 読み込み
- プロジェクトルート（.git または pyproject.toml を基準）を検出し .env → .env.local の順で読み込みます
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを抑止できます

フラグ / PID ファイル
- data/execution.pid: ExecutionEngine の PID（存在しない場合は実行プロセスが未起動）
- data/stop_requested.flag: run_* スクリプトの早期停止用フラグ（作成すると安全に終了）
- data/kill.flag: Kill Switch が作成するフラグ（ExecutionEngine に停止シグナルを送る）

ログ・アラート
- LINE 通知用に LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID を設定可能（本番環境では設定必須に近い）
- validate_config は本番時の設定ミスを検出するためのチェックを含む（KABUSYS_ENV=live 時は特に注意）

---

ディレクトリ構成（主要ファイル抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前検証ツール
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite の監視ログ永続化
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信の実装）
  - execution/               — 実行エンジン周り（OrderManager, OrderRepository, ExecutionEngine 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（上記は主要モジュールの抜粋です。詳細は各ファイルのドキュメンテーション文字列を参照してください。）

---

運用時の注意点 / ベストプラクティス
- 本番運用前に必ず python -m kabusys.validate_config を実行し設定を確認する（--strict モード推奨）。
- KABUSYS_ENV=live の場合は KILL_FLAG_CLEAR_ON_START=0 を推奨（誤って Kill Flag をクリアしない）。
- OpenAI API 等外部サービスを利用する機能は API キーやレート制限に注意する（バックオフ・リトライが実装されているが運用監視は必要）。
- Paper Trading 用 DB は本番 DB と完全に分離される（PAPER_TRADING_SQLITE_PATH を確認）。
- 監視は run_monitoring.py による定期実行で行う。MONITOR_POLL_INTERVAL で間隔を調整可能。

---

追加情報 / 貢献
- 各モジュールはファイル内に詳細な docstring・設計ノートが記載されています。実装の詳細やパラメータの意味は該当ファイルを参照してください。
- バグ報告・機能改善は Issue を立ててください。

----

以上。必要があれば README に API 仕様やより詳細な運用手順（systemd / docker-compose での管理例、ログローテーション、バックアップ手順など）を追記します。どの情報がさらに必要か教えてください。