# KabuSys

KabuSys は日本株向けの自動売買・リサーチ基盤のサンプル実装です。  
戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ用ツール群、OpenAI を使ったニュース NLP / レジーム検出などのユーティリティを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト）
- 環境変数と .env
- ディレクトリ構成

---

プロジェクト概要
- 日本株自動売買システムの参照実装（研究・テスト向け）。
- 発注エンジン（実際のブローカー／モック切替可）、監視エンジン、ポートフォリオ構築、因子計算、ニュース NLP（OpenAI 利用）などで構成。
- DuckDB（分析用）と SQLite（監視・発注ログ）を利用してデータを永続化します。
- 本番（live）／ペーパートレーディング（paper_trading）／開発（development）を切り替え可能。

---

機能一覧
- Execution
  - ExecutionEngine による発注フロー（ブローカークライアント切替）
  - RiskManager / OrderManager / Reconciler 等の発注周辺ロジック
  - Paper trading（モック）時は paper_trading 用 SQLite に完全分離して記録
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文、約定異常など）※実装箇所あり
  - RiskMonitor（ドローダウン／ポジション上限監視）
  - KillSwitch（条件を満たすと data/kill.flag を書き込み Execution を止める）
  - MonitoringEngine（複数モニタの統合ポーリング）
- Portfolio
  - 候補選定（スコア順）、等配分／スコア加重、ポジションサイズ計算、セクター上限等の純関数群
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC 計算、特徴量サマリ等
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント → ai_scores テーブル書き込み
  - regime_detector: ETF（1321）MA とマクロニュースセンチメントを合成して日次レジーム判定
- Tools
  - paper_verification_report: ペーパートレード DB から運用検証レポート生成
- 設定ユーティリティ
  - config_setup: 対話式 .env ウィザード
  - validate_config: 起動前チェック（必須 env、config/*.yaml の存在/パース等）
- ユーティリティ
  - ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定

---

セットアップ手順（ローカル）
前提: Python 3.10 以上を推奨（typing の構文に依存）。

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール  
   （requirements.txt がある場合はそれを使ってください。なければ以下をインストール）
   ```bash
   pip install duckdb psutil openai
   # オプション: YAML 検証をする場合
   pip install pyyaml
   ```

4. .env を作成  
   推奨: 対話式ウィザードで生成
   ```bash
   python -m kabusys.config_setup
   ```
   主要な必須環境変数:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（news_nlp / regime_detector を使う場合）
   その他（デフォルト値あり）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - LOG_LEVEL / LOG_DIR / PID_FILE_PATH / KILL_FLAG_CLEAR_ON_START / PAPER_FILL_MODE 等

   自動 .env ロードはデフォルトで有効です。自動ロードを無効化する場合:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

5. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ作成（ログや DB 保存先）
   - data/（kill.flag, execution.pid, monitoring DB など）
   - logs/（ログファイル）
   多くのスタートアップスクリプトは起動時にディレクトリを作成しますが、権限に注意してください。

---

使い方（主要スクリプト）
- ExecutionEngine を起動（本番 or paper_trading の挙動は KABUSYS_ENV に依存）
  ```bash
  python -m kabusys.run_execution
  ```
  特記事項:
  - 起動時にプロセス優先度を "high" に設定しようとします（psutil の権限に依存）。
  - paper_trading 環境では MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。
  - 停止制御: リポジトリルートの data/stop_requested.flag を作ると起動済みエンジンに停止要求が送られます。KillSwitch は data/kill.flag を書き込み Execution を停止させます。

- Monitoring を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  オプション:
  - ポーリング間隔の上書き: 環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを記録します（monitoring の設計方針による）。

- .env 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  どちらも OPENAI_API_KEY（または引数の api_key）を必要とします。

ログ
- ログはデフォルトで stdout（コンソール）と logs/<app_name>.log（日次ローテート）へ出力されます。
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で設定可能。

停止フラグ・キルスイッチ
- data/stop_requested.flag: run_execution/run_monitoring がポーリングで検出して安全停止を行うフラグ（外部から起動停止要求する際に使用）。
- data/kill.flag: KillSwitch が書き込むことで ExecutionEngine を停止させる（本番では慎重に扱う）。KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリアすることも可能だが、本番では 0 推奨。

---

重要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY（AI モジュール利用時）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- LOG_LEVEL（INFO 等）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env ロードを無効化）

自動 .env 読み込みについて
- プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動で読み込みます（OS 環境変数優先）。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

ディレクトリ構成（主要ファイル・モジュール）
（パッケージルートは src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理、自動 .env 読み込み
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/                — 発注エンジン周りの実装（BrokerFactory 等）
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - （TradeMonitor 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (実行時に生成されることが多い)
    - kill.flag
    - stop_requested.flag
    - execution.pid
    - monitoring.db / paper_trading.db（SQLite）
  - logs/ (ログ出力先)

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
  （validate_config で存在や YAML パースをチェック）

---

開発・運用上の注意
- KABUSYS_ENV=live の場合は本番設定です。LINE 通知や Kill Switch 周り、DB のパス等を十分に確認してください。
- OpenAI API 呼び出しはレート制限やネットワークエラーが発生しうるため、news_nlp・regime_detector はバックオフ・フォールバック（失敗時はスコア 0 など）を実装していますが、API キー管理とコストには注意してください。
- SQLite・DuckDB のファイルパスに書き込み権限が必要です。systemd / Cron 等でデプロイする場合は作業ディレクトリと権限を確認してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（設定上の挙動）。
- テスト・CI から自動実行する際は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して環境セットアップを明示的に行うと再現性が高くなります。

---

問い合わせ / 貢献
- README にはライセンスや issue の案内がないため、リポジトリのルールに従ってください。改善提案・バグ修正は PR を通じて行ってください。

--- 

必要であれば README にサンプル .env のテンプレートや Docker / systemd のデプロイ手順の追記、さらに詳細なモジュール別 API ドキュメントを追加します。どの内容を優先して追記しましょうか？