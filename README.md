# KabuSys

日本株向け自動売買システム（ライブラリ＋起動スクリプト群）

このリポジトリは、戦略計算・ポートフォリオ構築、発注実行（本番／ペーパートレード分離）、監視・アラート、AIベースのニュースセンチメント評価、ならびに検証・運用支援ツールを含む自動売買基盤の一部実装です。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- ファクター計算・特徴量生成（research）
- ポートフォリオ構築・リスク調整・ポジションサイズ計算（portfolio）
- 発注エンジン起動スクリプト（run_execution）
  - 本番／ペーパートレードを環境変数で切替
  - 発注・リスク管理・再整合（reconciler）等を組み合わせて実行
- 監視用エンジン・プロセス（run_monitoring / monitoring）
  - システム状態、注文ログ、リスク監視、Kill Switch（停止フラグ）
- AI モジュール（news_nlp, regime_detector）
  - OpenAI API を用いたニュースセンチメント / 市場レジーム判定
- 運用支援ツール（config_setup, validate_config, paper_verification_report）
- ログ設定・プロセス優先度などユーティリティ（utils）

設計方針の一部:
- 本番 DB とペーパートレード DB を分離して安全に検証可能
- ルックアヘッドバイアスを避けるため datetime.today()/date.today() 依存を最小化
- 重要な書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で扱う
- 多くの処理は副作用の少ない純粋関数または小さな責務のクラスで実装

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine 起動（スレッド起動・停止フラグ対応）
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループ
- 設定管理
  - .env ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 監視
  - system_status / trade_logs / risk_logs / positions / dashboard の SQLite 管理（monitoring_db）
  - Kill Switch（データ不整合・ドローダウン等で停止フラグを書込）
  - AlertManager 経由の通知（LINE 等の設定に依存）
- 研究・戦略
  - ファクター計算（momentum/volatility/value）
  - forward returns, IC 計算, 統計サマリ
- ポートフォリオ構築
  - 候補抽出、等配分・スコア配分、リスクベースの株数計算
  - セクター上限やレジーム乗数の適用
- AI
  - ニュース記事をまとめて LLM に渡し銘柄別センチメントを ai_scores に保存
  - マクロ記事＋ETF MA を使った市場レジーム判定
- 運用ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 必要条件 / インストール

推奨 Python バージョン: 3.9+

必須パッケージ（一例、プロジェクトに requirements.txt が無い場合は手動で）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML (validate_config で YAML 検証をする場合)

例:
```bash
python -m pip install duckdb psutil openai pyyaml
```

ソースを配置してから、作業ディレクトリに `data/` と `logs/` を作成するか、スクリプトが自動作成します。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading の場合、MockBrokerClient を使用し DB は data/paper_trading.db に記録される
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI を使う処理（news_nlp, regime_detector）で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（0/1）

ログディレクトリ:
- LOG_DIR を指定しない場合は logs/ に app_name.log（日次ローテーション）が出力されます。

---

## セットアップ手順（推奨の初期フロー）

1. リポジトリをクローン / 配置
2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt  # ある場合
   # または個別に: pip install duckdb psutil openai pyyaml
   ```
3. 初期.env を対話的に作成
   ```bash
   python -m kabusys.config_setup
   ```
   - 入力した .env はプロジェクトルートに保存されます（絶対に Git にコミットしないでください）。
4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告を厳格に扱う場合:
   python -m kabusys.validate_config --strict
   ```
   - ここで JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須変数が確認されます。
5. 必要に応じて data/ と logs/ のパーミッション設定。

---

## 使い方（起動例）

- 監視プロセス（常駐ポーリング）
  ```bash
  export MONITOR_POLL_INTERVAL=60  # オプション
  python -m kabusys.run_monitoring
  ```
  挙動:
  - process 優先度を "high" に設定（psutil 利用）
  - Settings から DB パスを取得して監視 DB を初期化
  - data/stop_requested.flag が存在するとループを終了します

- 実行エンジン（ExecutionEngine）
  ```bash
  # paper_trading の場合
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  挙動:
  - paper_trading の場合、MockBrokerClient を使用し DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
  - 停止フラグ（data/stop_requested.flag）があると起動せず終了します
  - 実行中に stop flag を検出すると engine.stop() を呼びスレッド停止を待機します

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（ニューススコア・レジーム判定）
  - OPENAI_API_KEY を環境変数に設定して利用してください。
  - 例: kabusys.ai.score_news / regime_detector.score_regime を Python から呼び出す

---

## 運用上の注意・安全機能

- Kill Switch
  - RiskMonitor や各種モニターの結果に応じて data/kill.flag を書き込みます。ExecutionEngine は起動時や稼働中に kill.flag を検出すると停止処理を行います。
  - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動的に kill.flag をクリアしますが、本番では 0 を推奨します。
- DB 分離
  - paper_trading モードではペーパートレード用 DB を使い、本番データと完全に分離して記録します。
- ロギング
  - 共通の logging 設定（utils.logging_setup）により stdout と日次ローテートログへ出力されます。
- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を試みます。権限や OS により失敗することがありますが安全にスキップされます。

---

## 主要ファイル / ディレクトリ構成

（src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py         (実装ファイルあり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         (実装ファイルあり)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
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
  - data/                     — default: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db (実行時に作成される)

（注）一部ファイルはここでは抜粋のみ示しています。実装の詳細は各モジュールの docstring を参照してください。

---

## 開発者向けメモ

- 設定ファイル:
  - .env（プロジェクトルート）を使用。`.env.example` がある場合はこれを参照して作成してください。
- テスト:
  - 多くの内部関数は副作用を抑えた設計になっているためユニットテストが容易です（OpenAI 呼出し等はモック推奨）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して冪等に必要カラム追加を行います（簡易マイグレーション）。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```
- 監視プロセス起動
  ```bash
  python -m kabusys.run_monitoring
  ```
- 実行エンジン起動
  ```bash
  python -m kabusys.run_execution
  ```
- Paper 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## ライセンス / コントリビュート

この README はコードベースの概要をまとめたものです。実運用に投入する前に設定・権限・テストを十分に実施してください。コントリビュートや変更提案はリポジトリのプルリクエスト経由でお願いします。

---

必要ならば README に各モジュールの API 使用例やサンプル .env のテンプレート、運用フロー（起動順序、監視→実行の組合せ）を追加で記載します。どの情報を追加したいか教えてください。