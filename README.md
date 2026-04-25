# KabuSys

日本株向け自動売買 / リサーチ基盤のコアライブラリ群です。  
このリポジトリは取引エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、ファクター計算／研究モジュール、ニュースNLP やレジーム判定などの補助機能を含みます。

主にローカル環境やペーパートレード環境での開発・検証を想定しています。  
（本番接続（kabuステーション等）を行う場合は設定を十分に確認してください）

---

## 主な特徴（概要）

- ExecutionEngine（発注系）
  - 本番 / ペーパー（paper_trading）モードを切り替え可能
  - RiskManager / OrderManager / Reconciler 等のコンポーネントを組み合わせた実行フロー
- Monitoring（監視）
  - CPU / メモリ / ディスク / プロセス稼働状況、注文ログ、リスク指標の定期チェック
  - Kill Switch（条件に応じた停止フラグの書き込み）
  - アラート送信フック（LINE 等を想定）
- 研究・分析
  - DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー等）
  - ファクターの特徴量探索・IC 計算ユーティリティ
- AI 関連
  - OpenAI を用いたニュースのセンチメントスコアリング（ai.news_nlp）
  - マクロニュース＋ETF MA を用いた市場レジーム判定（ai.regime_detector）
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - 統一ロギング設定、プロセス優先度設定ユーティリティ
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）

---

## 機能一覧（ファイル単位の要約）

- run_execution.py
  - ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して paper DB に記録。
- run_monitoring.py
  - SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を指定可能。
- config.py
  - 環境変数の読み込み・ラッパー（Settings クラス）。.env 自動ロード機能あり。
- config_setup.py
  - .env を対話式に作成/更新するウィザード。
- validate_config.py
  - 必須環境変数や config/*.yaml の有無などを検証する CLI。
- tools/paper_verification_report.py
  - ペーパートレード DB を解析して各種指標（稼働率、約定率、レイテンシ等）を出力。
- portfolio/
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py：銘柄選定・配分・単元丸め・セクター制限等
- research/
  - factor_research.py / feature_exploration.py：DuckDB を用いたファクター計算・IC/統計解析
- ai/
  - news_nlp.py：ニュース記事を集約して OpenAI による銘柄単位センチメント評価を実行し ai_scores に書き込む
  - regime_detector.py：ETF MA とマクロセンチメントを合成して market_regime を判定・永続化
- monitoring/
  - monitoring_db.py：SQLite ベースの監視 DB 層（テーブル作成 / CRUD ユーティリティ）
  - system_monitor.py / trade_monitor.py / risk_monitor.py：個別監視ロジック
  - kill_switch.py / monitoring_engine.py / alert_manager.py：Kill Switch、監視統合エンジン、アラート管理
- utils/
  - logging_setup.py：コンソール+日次ローテーション・ファイルハンドラを統一して設定
  - process_priority.py：プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 必要条件（依存関係）

推奨 Python バージョン: 3.10 以上（型ヒントの | 演算子等を使用）  
主要パッケージ（抜粋）:
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行う場合）
- （標準ライブラリのみで動く部分も多いですが、上記は主要機能で必要になります）

例（pip）:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # POSIX
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   （requirements.txt が無い場合は上記の主要パッケージを individually インストール）
4. .env を用意
   - 対話式ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは `.env` を手動で作成（.env.example を参考にすること）

5. 設定検証（必須環境変数やパスのチェック）
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ等の初期化
   - デフォルトの DB/ログパスは `.env` や Settings のデフォルトに従います（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, logs/）
   - 必要に応じてディレクトリを手動作成（logging_setup が自動作成を試みます）

注意:
- KABUSYS_ENV により挙動が変わります（development / paper_trading / live）。
- paper_trading では本番 SQLite を使わず PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使います。

---

## 使用方法（よく使うコマンド例）

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV で制御）
  ```
  # 本番モード例
  export KABUSYS_ENV=live
  python -m kabusys.run_execution

  # ペーパートレード
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  実行時に data/execution.pid が作成され、data/stop_requested.flag により停止できます。  
  paper_trading モードでは MockBrokerClient を使用し、取引記録は paper_trading.db に保存されます。

- Monitoring を起動
  ```
  # MONITOR_POLL_INTERVAL に秒数を指定可能（デフォルト 60）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  監視は常に production 用の sqlite_path（Settings.sqlite_path）を参照します。停止は data/stop_requested.flag を作成して行います。

- .env を生成・編集
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート
  ```
  # デフォルト DB は data/paper_trading.db（環境変数で上書き可）
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または明示的に DB を指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュール呼び出し（簡単な例）
  - score_news / score_regime は Python からインポートして使用できます。例:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_count = score_news(conn, target_date=date(2026,4,20), api_key="sk-...")
    ```
  - OpenAI API キーは環境変数 OPENAI_API_KEY でも指定可能。

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の fill 動作: instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY（AI 機能利用時に必要）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（ログ保存先、デフォルト: logs/）
- MONITOR_POLL_INTERVAL（run_monitoring 用ポーリング間隔秒数、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視・停止関連）

---

## 停止・Kill Switch

- 実行プロセスの停止（安全にシャットダウン）:
  - run_execution は data/stop_requested.flag が存在すると起動/実行中に停止を開始します。
  - run_monitoring でも同じ stop flag を検出してループを抜けます。
- Kill Switch:
  - monitoring により条件が満たされると data/kill.flag が書き込まれ、ExecutionEngine 側で検出して停止できます。
  - 本番では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

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
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/  (発注ロジック: Engine, BrokerFactory, OrderManager など)
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
  - tools/
    - paper_verification_report.py

レポジトリルートに以下のようなディレクトリ/ファイルが想定されます:
- data/ (SQLite DB、pid、flag など)
  - data/monitoring.db
  - data/paper_trading.db
  - data/kabusys.duckdb
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag
- logs/（ログファイル出力先）
- .env / .env.local

---

## 開発メモ / 注意点

- DuckDB 接続を利用する研究・AI モジュールはローカルの prices_daily / raw_financials / raw_news 等のテーブルに依存します。データの準備が必要です。
- OpenAI の呼び出しにはエラーやレート制限を考慮したリトライ実装が含まれていますが、API 使用量・コストに注意してください。
- 本番運用前には必ず validate_config により設定を確認し、KABUSYS_ENV=live の場合は LINE 等の通知設定や kill flag の動作を再確認してください。
- 単体テストや統合テスト向けに KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env ロードを無効化できます。

---

README に記載のない詳細な実装や利用方法は各モジュールのドキュメント（ソース内の docstring）を参照してください。必要であれば、実行時の具体的なシナリオ（デバッグ、ローカル検証、Docker 化など）に合わせた追加手順も作成します。