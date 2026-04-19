# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」の実装（ライブラリ・起動スクリプト・管理ツール群）です。戦略／ポートフォリオ構築、実行エンジン、監視・リスク管理、研究・ファクター分析、AI（ニュース NLP / レジーム検出）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次のような機能を提供するモジュール群から構成されています。

- 実行エンジン（ExecutionEngine）: ブローカー接続・注文管理・リスク管理・約定照合など
- 監視（Monitoring）: システム状態、注文の滞留や約定異常、ドローダウン監視、Kill Switch
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出、セクター制約・レジーム調整
- 研究（Research）: ファクター計算（Momentum/Volatility/Value）、特徴量探索・IC解析
- AI コンポーネント: ニュースを LLM（OpenAI）でスコア化する `news_nlp`、市場レジーム判定
- 開発用ツール: .env 設定ウィザード、設定検証 CLI、Paper Trading レポート生成

設計上の特徴:
- DuckDB を用いた分析用データベース、SQLite を監視・注文ログ用に利用（Paper Trading では分離）
- 実行環境（KABUSYS_ENV）により動作モード（development / paper_trading / live）を切替
- フェイルセーフ重視（OpenAI API 失敗時のフォールバック、監視での冗長処理等）
- 自動的な .env ロード、対話的ウィザード、設定検証ツールを備える

---

## 機能一覧

主要モジュール / 機能（抜粋）

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（実際の発注 or モックでのペーパートレード）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL により間隔制御）

- 設定
  - config.py: 環境変数と Settings ラッパー、自動 .env 読み込み
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: 起動前の設定検証 CLI

- 監視
  - monitoring/monitoring_db.py: SQLite スキーマ初期化・永続化 API
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py
  - kill_switch.py: 条件に応じて data/kill.flag を書き込み Execution を停止させる
  - alert_manager（通知機能） — 実装箇所あり（コード内参照）

- 実行関連
  - execution/*: BrokerFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager

- ポートフォリオ
  - portfolio/portfolio_builder.py: 候補選定・重み付け
  - portfolio/position_sizing.py: 株数決定・投下資金の調整
  - portfolio/risk_adjustment.py: セクターキャップ・レジーム乗数

- 研究
  - research/factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - research/feature_exploration.py: 将来リターン・IC 計算・統計サマリ

- AI
  - ai/news_nlp.py: raw_news を LLM でスコア化して ai_scores に書き込む（OpenAI）
  - ai/regime_detector.py: ETF とマクロニュースを利用して 'bull'/'neutral'/'bear' を判定

- ツール
  - tools/paper_verification_report.py: Paper Trading データから検証レポートを生成

- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定（コンソール + 日次ローテート）
  - utils/process_priority.py: プラットフォーム差を吸収したプロセス優先度 / CPU affinity 設定

---

## 前提条件 / 必要環境

- Python 3.10 以上（型ヒント: X | Y を使用）
- システムパッケージ: SQLite（標準搭載）、任意で DuckDB バイナリは Python パッケージで提供
- 推奨 Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で利用、任意）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（requirements.txt がない場合は上記を参考にしてください）

---

## セットアップ手順

1. リポジトリをクローンし移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存ライブラリのインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai pyyaml
   ```

3. .env を作成
   - 対話式ウィザードで .env を生成:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY を .env または環境変数で設定

4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. 保存先ディレクトリ確認・作成
   - デフォルト DB / ファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 必要に応じてディレクトリを作成（多くは起動時に自動作成されます）

---

## 使い方

主要な起動方法とオプション例

- ExecutionEngine を起動（通常 / 本番 / ペーパートレード）
  - 本番モード:
    ```
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - ペーパートレード（モックブローカー、専用 DB を使用）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 実行ループは data/stop_requested.flag の存在を監視します。外部から停止したい場合はこのファイルを作成してください（または Kill Switch により data/kill.flag が作成されることがあります）。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  # ポーリング間隔を変更する場合（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視は環境にかかわらず本番 sqlite_path を使用して監視ログを記録します。
  - stop_requested.flag が存在するとループを終了します。

- .env 対話ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB を override する:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能利用
  - OpenAI API キーは環境変数 OPENAI_API_KEY で設定するか、関数呼び出し時に明示的に渡してください。
  - news_nlp と regime_detector は LLM 呼び出しを行います。API レスポンスやエラーはログに記録され、失敗時はフェイルセーフ動作（フォールバック）します。

- Kill Switch / 停止フラグ
  - KillSwitch は監視モジュールが発動すると data/kill.flag を書き込み、ExecutionEngine の停止トリガーとなります。
  - 手動停止は data/stop_requested.flag を作成（両起動スクリプトはこれを参照して終了します）。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- OPENAI_API_KEY — OpenAI を利用する場合に必須
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading の MockBroker の fill-mode（instant|partial|never|reject）

config_setup や .env.example を参照して設定してください。validate_config で起動前のチェックが可能です。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings
    - config_setup.py           — .env ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - execution/
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (参照実装)
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
    - utils/
      - logging_setup.py
      - process_priority.py

- data/                      — デフォルトの DB / PID / フラグが置かれる（実行時に自動作成）
  - monitoring.db, paper_trading.db, kabusys.duckdb 等
- logs/                      — ログファイル出力先（設定により変更可能）

---

## 開発上の注意点 / 運用ノート

- 実行プロセスは起動直後にプロセス優先度を変更します（psutil が必要）。権限不足では警告が出ますが処理は継続します。
- monitoring モジュールは監視データを常に本番 sqlite に記録します（環境に依存せず本番 DB を参照する設計）。paper_trading の注文履歴は paper_trading 用 DB に分離されます。
- OpenAI 呼び出しはネットワーク障害やレート制限を考慮して指数バックオフでリトライします。失敗時はログを残してフェイルセーフ（0.0 など）で継続します。
- データベースマイグレーション（monitoring_db.init_monitoring_db）は起動時に簡易的な列追加を行います。重要な変更はバックアップ後に運用してください。
- 本番環境（KABUSYS_ENV=live）での Kill Flag や KILL_FLAG_CLEAR_ON_START の設定には十分注意してください（誤設定で自動クリアされると危険です）。

---

README は実行スクリプトや設定の入口を整理したものです。各モジュールの詳細な設計やアルゴリズム（PortfolioConstruction.md、StrategyModel.md 等のドキュメント）が別途存在する想定です。追加ドキュメントや要件があれば、それに合わせて README を拡張します。