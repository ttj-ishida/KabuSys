# KabuSys

日本株自動売買システムの Python パッケージ。  
トレード実行エンジン、監視（Monitoring）、リスク管理、ポートフォリオ構築、リサーチ/ファクター計算、AI によるニュースセンチメント評価などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主な目的は以下です。

- シグナルに基づく発注を行う Execution Engine（本番 / ペーパートレード対応）
- 実行状況・システム状態の継続的監視とアラート（Monitoring）
- ドローダウンやポジション上限のリスク検出と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、株数決定）
- DuckDB を用いたリサーチ / ファクター計算モジュール
- OpenAI を用いたニュース NLP による銘柄別センチメント評価
- 設定ウィザード / 設定検証ツール、紙トレード検証レポート等のユーティリティ

---

## 機能一覧

- Execution Engine
  - 本番（live） / ペーパートレード（paper_trading）モード
  - paper_trading では MockBroker を使用し DB を分離（data/paper_trading.db）
  - リスク管理（最大ポジション比率、利用率、ドローダウンなど）
- Monitoring
  - システム（CPU/Memory/Disk/プロセス）監視
  - 発注ログ（trade_logs）、ポジション、リスクログ、ダッシュボードの永続化（SQLite）
  - Kill Switch（条件に応じて data/kill.flag を書き込み、Execution を停止）
  - ログ/アラートの発行（AlertManager を通す設計）
- ポートフォリオ構築
  - 候補選定、等重／スコア重み、リスク調整（セクターキャップ、レジーム乗数）
  - 発注株数決定（単位株丸め、aggregate cap）
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続を受ける純粋関数）
  - Forward returns, IC 計算、統計サマリー
- AI / NLP
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメント集計（ai_scores テーブルへ書込）
  - マクロニュース＋ETF MA を使った市場レジーム判定（market_regime テーブル）
  - API の失敗にはリトライやフォールバックを備えたフェイルセーフ設計
- ユーティリティ
  - 対話式 .env 作成ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト

---

## 必要要件（推奨）

- Python 3.10+
- 推奨ライブラリ（最低限の一覧）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML パースを行う場合）
- （環境によって追加パッケージが必要な場合があります）

インストール例（仮想環境推奨）:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール（上記参照）
4. 環境変数設定
   - 対話式ウィザードで .env を作成するのが簡単です:

     ```
     python -m kabusys.config_setup
     ```

   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う環境変数（デフォルト値は括弧内）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - LOG_LEVEL (INFO)
     - OPENAI_API_KEY（AI 機能利用時）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒、デフォルト 60）
     - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject") — Paper Trading の約定挙動
     - KILL_FLAG_CLEAR_ON_START (0 | 1)
5. 設定検証（任意）:

```
python -m kabusys.validate_config
# 警告も失敗扱いにする場合:
python -m kabusys.validate_config --strict
```

---

## 使い方

以下は主要な起動 / 利用方法です。

- Execution Engine を起動する

  - 通常（環境変数に応じて本番 or ペーパー自動判定）:

    ```
    python -m kabusys.run_execution
    ```

  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録されます（本番 DB と分離）。
    - エンジンは data/execution.pid を作成して PID 管理を行います。
    - data/stop_requested.flag を作成するとループ内で検知して優雅に停止します。
    - Kill Switch は data/kill.flag により Execution を停止させる仕組みです。

- Monitoring を起動する

  ```
  python -m kabusys.run_monitoring
  ```

  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定できます（デフォルト 60）。
  - Monitoring は設定にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。
  - data/stop_requested.flag を置くと監視ループを終了します。

- .env の対話式作成 / 更新

  ```
  python -m kabusys.config_setup
  ```

  --env-file オプションで出力先を変更できます。

- 設定検証

  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 周り（プログラムから呼び出す）
  - ニューススコアリング（DuckDB 接続を渡して呼ぶ）:

    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key=...)

  - レジーム判定:

    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=...)

  これらは CLI ではなくプログラム API として利用する想定です（必要に応じて thin CLI を作成してください）。

- ログ
  - ログは logs/<app_name>.log に日次ローテートで保存されます（デフォルト logs ディレクトリ）。
  - ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。

---

## 重要なファイル / フラグ

- data/kill.flag — Kill Switch による Execution 停止フラグ（書き込みで停止）
- data/stop_requested.flag — run_monitoring / run_execution の外部停止トリガ（存在するとループが停止）
- data/execution.pid — ExecutionEngine が作成する PID ファイル
- デフォルト DB:
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - DuckDB (分析): data/kabusys.duckdb

---

## 環境変数自動ロード挙動

- パッケージはプロジェクトルート（.git または pyproject.toml がある場所）を自動検出し、
  .env を自動で読み込みます（.env.local があれば上書き）。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

（src/kabusys 以下の主要ファイル／パッケージ構成と役割）

- kabusys/
  - __init__.py — パッケージメタ情報
  - config.py — Settings クラス（環境変数 / .env の読み込み、検証ロジック）
  - config_setup.py — .env 作成対話ウィザード（CLI）
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（起動時にプロセス優先度を設定、DB 接続、エンジン起動）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（コンソール + ローテートファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite による永続化（テーブル作成、読み書きラッパー）
    - system_monitor.py — CPU/Memory/Disk/プロセス/データ鮮度の監視
    - trade_monitor.py — （発注ログ監視：滞留注文、約定異常等）
    - risk_monitor.py — ドローダウン・ポジション上限の監視
    - kill_switch.py — Kill Switch（flag 書き込み）ユーティリティ
    - monitoring_engine.py — 個別 Monitor を束ねるループ
    - alert_manager.py — アラート送信管理（LINE 等へ通知）
  - execution/ (エンジン関連、OrderManager, BrokerFactory 等)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 発注株数決定ロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等の因子計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計集計
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI で銘柄別スコアを算出、ai_scores へ保存）
    - regime_detector.py — マクロニュース + ETF MA によるレジーム判定
  - data/（実行時に使用するファイル群、リポジトリには含まれない想定）
    - *.db, *.flag, *.pid, ...

---

## 開発上の注意 / ベストプラクティス

- KABUSYS_ENV=live を使う場合は特に注意して設定を確認してください。validate_config は live 時の守りのチェックを行います。
- .env は機密情報（API トークン等）を含むため Git へのコミットは禁止です。
- Paper Trading モードは本番 DB と完全分離されるように設計されています（PAPER_TRADING_SQLITE_PATH を確認）。
- OpenAI API を使う処理はネットワーク障害・レート制限を考慮してリトライとフォールバックが組み込まれていますが、API キーの管理とコストに注意してください。
- ログは logs ディレクトリに日次ローテーションで出力されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

必要であれば README に含めるコマンド例、.env.example のテンプレート、または各モジュールのより詳細な API ドキュメントを追加で作成します。どの部分を優先して詳述しますか？