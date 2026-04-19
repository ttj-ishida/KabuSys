# KabuSys — 日本株自動売買システム（README）

以下は、このリポジトリの主要な使い方・設定手順・ディレクトリ構成の簡易ドキュメントです。コードは src/kabusys 以下に実装されています。

---

## プロジェクト概要
KabuSys は日本株向けの自動売買システムおよびそれを支える監視・研究ツール群です。  
主な機能は、注文の実行エンジン（ExecutionEngine）、システムおよび取引の監視（Monitoring）、ポートフォリオ構築ロジック、ファクター計算・リサーチ、そして OpenAI を用いたニュース NLP / レジーム判定などです。

設計上の特徴：
- production / paper_trading / development を切り替え可能な環境設定
- Paper Trading 時はモックブローカーを使用し、本番 DB とは分離された専用 DB に記録
- 監視は独立プロセスで定期ポーリングし、Kill Switch により安全停止が可能
- DuckDB を使った研究向けファクター計算モジュール
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント・レジーム判定（オプション）

---

## 主な機能一覧
- Execution
  - ExecutionEngine（発注・オーダー管理・リスク管理・照合作業）
  - ブローカー抽象化（paper_trading では MockBrokerClient を使用）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス監視、株価データ鮮度チェック
  - TradeMonitor: 発注ログ・滞留注文・約定異常検出（trade_logs を参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ書き込み
  - KillSwitch: 条件達成時に data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 上記を束ねてポーリング実行
- Portfolio construction
  - 候補選定、等重/スコア重み、リスクベースのポジションサイジング、セクターキャップ、レジーム乗数
- Research
  - DuckDB を使ったファクター計算（Momentum/Value/Volatility など）
  - Forward return、IC（Information Coefficient）、ファクター統計サマリ
- AI
  - news_nlp: raw_news を LLM で評価して銘柄ごとの ai_score を生成
  - regime_detector: ETF（1321）の MA とマクロニュースを合成して market_regime を判定
- Tools
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）

---

## 必要条件（依存）
主な Python ライブラリ（抜粋）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml のパース検証を行う場合に任意で必要）

一般的には requirements.txt を用意している想定ですが、無い場合は上記を pip でインストールしてください:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存のインストール
   - pip install -r requirements.txt
   - もしくは必要ライブラリを個別インストール（上記参照）
4. 初期 .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - 各種 API トークンやパス、KABUSYS_ENV 等を対話的に設定して .env を作成します
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
6. データディレクトリ（自動で作られることもあります）
   - デフォルトの DB / ログ等:
     - SQLite (監視用): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - DuckDB: data/kabusys.duckdb
     - ログ: logs/<app_name>.log
   - 必要に応じて .env でパスを上書きしてください

---

## 主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient を使用し paper_sqlite_path へ記録
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を使用する場合）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔 秒、デフォルト: 60）
- KILL_FLAG_PATH（Kill Switch のファイルパス、デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか 1/0、デフォルト: 0）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject、デフォルト: instant）

.env の例（抜粋）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

## 実行方法（主なスクリプト）
- ExecutionEngine（注文エンジン）起動
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録します（production DB と完全分離）
    - エンジンは data/stop_requested.flag を見て停止します
    - PID ファイル: data/execution.pid（Settings.pid_file_path を参照）
- Monitoring（監視プロセス）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）
  - Monitoring は KABUSYS_ENV に関わらず production の sqlite_path を使用して監視ログを記録します
  - 停止は data/stop_requested.flag を作成することで行います
- 設定検証（CLI）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- .env ウィザード
  - python -m kabusys.config_setup
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数を上書き）
- 研究 / AI 関数はライブラリとしてインポートして利用
  - 例: from kabusys.research import calc_momentum
  - AI 機能を動かすには OPENAI_API_KEY が必要

---

## 停止 / Kill Switch / フラグ
- ExecutionEngine 停止シグナル:
  - KillSwitch はリスク条件（ドローダウン超過・ポジション上限超過等）で data/kill.flag を書き込み Execution を停止させます
  - 手動で停止させたい場合は data/kill.flag を作成してください
- run_execution / run_monitoring の外部停止:
  - data/stop_requested.flag を作成すると、それらのプロセスが検知して正常終了します
- KILL_FLAG_CLEAR_ON_START 環境変数が 1 の場合、起動時に kill.flag を自動でクリアします（本番では 0 推奨）

---

## ロギング
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一
- 出力先:
  - コンソール stdout（デフォルト）
  - 日次ローテーションファイル: logs/<app_name>.log（デフォルト）
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で指定可能

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要なファイル / パッケージの説明です（ツリービューは抜粋）。

- src/kabusys/
  - __init__.py (パッケージ定義・バージョン)
  - config.py (環境変数 / Settings クラス・.env 自動ロード)
  - config_setup.py (.env 対話ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - tools/
    - paper_verification_report.py (ペーパートレード検証レポート)
  - utils/
    - logging_setup.py (ログ設定ユーティリティ)
    - process_priority.py (プロセス優先度 / CPU affinity 設定)
  - ai/
    - news_nlp.py (ニュース NLP スコアリング)
    - regime_detector.py (市場レジーム判定)
  - monitoring/
    - monitoring_db.py (SQLite 永続化層)
    - system_monitor.py
    - trade_monitor.py (trade_monitor.py は省略しているが監視ロジックを含む想定)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (アラート送信ロジック: LINE など想定)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - execution/ (注文実行関連: broker_factory, execution_engine, order_manager, 等)
  - data/ (データパイプライン・DuckDB/SQLite テーブル操作モジュール)

（リポジトリには上記以外にも補助モジュールが含まれます。詳細はソースを参照してください。）

---

## 注意事項・運用上のヒント
- 本番環境（KABUSYS_ENV=live）では .env の内容・LINE 通知設定・KILL_FLAG_CLEAR_ON_START 等を十分に確認してください。validate_config の live ガードが警告を出します。
- Paper Trading モードは本番 DB と完全に分離されます（PAPER_TRADING_SQLITE_PATH を利用）。ペーパートレードでの検証を推奨。
- OpenAI を利用する処理は外部 API 依存のため、ネットワークやレート制限により部分失敗する可能性があります。AI モジュールはフェイルセーフで継続する設計になっていますが、API キーの管理・コストに注意してください。
- ログディレクトリが作れない場合、ファイル出力は無効化されコンソール出力のみになります（その旨警告が表示されます）。

---

この README はコード中の docstring / コメントに基づいて作成しています。各機能の詳細や拡張方法は該当モジュールの docstring を参照してください。必要であればコマンド別の具体的な実行例や CI/CD 起動手順、Docker 化手順などの追記も作成できます。どの部分を詳しくしたいか教えてください。