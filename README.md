# KabuSys

日本株向けの自動売買システム（リサーチ・ポートフォリオ構築・発注・監視/アラート）をまとめたパッケージです。  
このリポジトリには、以下の主要機能を提供するモジュール群が含まれます。

- ExecutionEngine（発注エンジン）と Broker クライアント抽象化（paper/live 切替）
- 監視サブシステム（System / Trade / Risk / KillSwitch / Alert）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング・セクターキャップ）
- 解析・リサーチ（ファクター算出・特徴量解析）
- AI 補助機能（ニュース NLP によるセンチメント、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

--- 

## 主な機能（概要）

- Execution
  - 環境変数 KABUSYS_ENV に応じた挙動（development / paper_trading / live）
  - paper_trading 時は MockBrokerClient を利用し、paper_trading 用 SQLite に記録
  - エンジン停止はフラグファイル（data/stop_requested.flag / data/kill.flag）で制御可能

- Monitoring
  - システムリソース（CPU/MEM/DISK）、プロセス生存、データ鮮度の定期チェック
  - 取引ログ監視（滞留注文、約定異常など）
  - リスク監視（ドローダウン、ポジション上限）と KillSwitch（条件で自動停止シグナル）
  - アラート通知連携（LINE 等のトークンを設定すれば通知可能）

- Portfolio
  - 候補選定（スコア順）／重み付け（等金額・スコア加重）／ポジションサイズ計算（リスクベースなど）
  - セクター上限処理、レジーム乗数適用

- Research
  - DuckDB を用いたファクター計算（Momentum/Volatility/Value など）
  - 将来リターンや IC（Information Coefficient）計算、統計サマリ

- AI（オプション、OpenAI）
  - ニュース記事を LLM（gpt-4o-mini 等）でセンチメント化して銘柄単位のスコアを生成
  - マクロニュース＋ETF MA200 を組み合わせた市場レジーム判定

- ツール
  - .env 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）

---

## 動作環境・依存（概略）

- Python 3.10+
- 必須外部ライブラリ（代表例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config で YAML 検証を有効にする場合）
- DB: SQLite（監視/発注ログ等）、DuckDB（時系列・分析用途）

インストール例（requirements.txt が無い場合の例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数ファイル (.env) を作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - ウィザードで生成した .env は絶対に Git にコミットしないでください（シークレット含む）
4. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config
   # --strict をつけると警告も FAIL 扱いになります
   python -m kabusys.validate_config --strict
   ```
5. 必要なディレクトリ（data/, logs/）はスクリプトが自動作成しますが、権限等を事前に確認してください。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db） — Monitoring が使用するSQLite（production 用）
- PAPER_TRADING_SQLITE_PATH（paper_trading 専用 DB）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- LOG_LEVEL（例: INFO）
- LOG_DIR（ログ保存先、デフォルト: logs/）
- OPENAI_API_KEY（AI 機能を利用する際に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用、任意）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）

---

## 起動・使い方

各種エントリポイントはモジュールとして実行できます。

- ExecutionEngine（発注エンジン）を起動
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/stop_requested.flag があると起動せず終了します。
  - 実行中は data/execution.pid にプロセス情報を書きます（PID ファイル）。

- Monitoring を起動（ポーリングループ）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視データを記録します。
  - data/stop_requested.flag を検知すると監視ループを終了します。

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラムから呼び出す）
  - ニュース NLP（銘柄別スコア）:
    - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡してください。

---

## 停止・Kill Switch の仕組み

- 手動停止（外部）:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して停止します。
- 自動停止（運用ルールにより監視が発火）:
  - RiskMonitor 等が条件を満たすと KillSwitch が data/kill.flag に理由を書き込みます。
  - ExecutionEngine は起動時や監視ループで kill.flag を確認し、検出時に停止します。
- kill.flag は KILL_FLAG_CLEAR_ON_START=1 の場合に起動時に自動クリアする設定があります（本番では推奨されません）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（監視ログ）
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - data/ (※ 実行時に生成される想定)
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - logs/ (ログ出力先、デフォルト)

（注）上記はリポジトリの一部抜粋です。各ディレクトリ内にはさらに実装ファイルが含まれます。

---

## 運用時の注意点 / 実装上のポイント

- Monitoring は環境にかかわらず Settings.sqlite_path（監視 DB）を使用します。paper_trading の発注履歴は paper_sqlite_path に分離されます（発注系 DB と監視 DB の分離）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を起点）を基に行います。必要があれば KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- OpenAI 等外部 API を利用する機能は API 呼び出しの失敗をフェイルセーフで扱う設計です（リトライ・フォールバック）。ただし利用には API キーと費用が必要です。
- ロギングは共通ユーティリティで整備されています：logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- プロセス優先度設定・CPU affinity は psutil を利用しており、権限不足や未対応 OS の場合は警告を出してスキップします。
- validate_config は事前チェックとして有用：必須環境変数や config/*.yaml の存在・パース（PyYAML 要）を確認できます。

---

## よく使うコマンド一覧

- .env を作る / 更新
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 実行エンジン起動
  ```bash
  python -m kabusys.run_execution
  ```
- 監視プロセス起動
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート（例）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば README に以下を追加可能です：
- requirements.txt / poetry / pipfile の例
- systemd / supervisor の unit ファイル例（production 起動用）
- サンプル .env.example（必須環境のみ抜粋）
- 詳細な API ドキュメント（各モジュールの公開関数一覧）

この README をベースに、運用向けの詳細手順やデプロイ手順を追記することを推奨します。