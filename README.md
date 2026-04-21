# KabuSys

日本株向けの自動売買・リサーチ基盤（ライブラリ + 起動スクリプト群）

このリポジトリは、売買ロジック・ポートフォリオ構築・監視・AI を組み合わせた日本株自動売買システムのコア部分を含みます。各モジュールは分離された責務を持ち、ローカル開発・ペーパートレード・本番運用を意識した設計になっています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト・コマンド）
- 環境変数と設定
- ディレクトリ構成（主要ファイル説明）
- 運用上の注意

---

## プロジェクト概要

KabuSys は以下の機能を持つ Python パッケージです。

- ファクター計算（momentum / volatility / value 等）と特徴量解析
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ExecutionEngine による発注/注文管理（本番 / ペーパートレード切替）
- 監視 (Monitoring)：システム稼働状況、注文ログ、リスク（ドローダウン、ポジション上限）監視
- AI モジュール：ニュースの NLP スコアリング（OpenAI 利用）や市場レジーム判定
- ユーティリティ：.env ウィザード、設定検証、ログ設定、プロセス優先度設定 等
- 検証ツール：Paper Trading 用の検証レポート生成

設計のポイント:
- 環境依存設定は .env ファイル／環境変数で管理
- paper_trading 環境では本番 DB と分離（data/paper_trading.db）
- DuckDB を分析用 DB、SQLite を監視/取引ログ用 DB に使用

---

## 機能一覧

主要な機能（抜粋）:

- kabusys.config: 環境変数読み込み / Settings 抽象化（KABUSYS_ENV による動作モード判定）
- kabusys.config_setup: 対話式で .env を作成・更新する CLI ウィザード
- kabusys.validate_config: 起動前の設定検証ツール（必須環境変数や config/*.yaml の検査）
- Execution:
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用）
- Monitoring:
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔制御）
  - monitoring_engine / system_monitor / trade_monitor / risk_monitor / kill_switch 等
  - monitoring_db: SQLite スキーマ初期化・読み書きラッパー
- Portfolio:
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクター上限、レジーム乗数
- Research:
  - ファクター計算（momentum/volatility/value）や forward return、IC 計算、統計サマリ
- AI:
  - news_nlp: OpenAI を用いたニュースセンチメントスコアリング（ai_scores テーブルに書き込み）
  - regime_detector: ETF の MA200 乖離とマクロニュースを合成して市場レジーム判定
- tools:
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## セットアップ手順

1. Python 仮想環境を作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージをインストール
   - 必要最低限: duckdb, psutil, openai（AI を使う場合）、sqlite3 は標準搭載
   - 設定検証に PyYAML を使う（任意）
   例:
   ```bash
   pip install duckdb psutil openai
   pip install PyYAML  # YAML 検証を有効にしたい場合
   ```

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. 初期設定（.env 作成）
   対話式ウィザードで .env を作成します:
   ```bash
   python -m kabusys.config_setup
   ```
   既存の .env を読み込み、必要項目を対話で入力します。

4. 設定検証（起動前に推奨）
   ```bash
   python -m kabusys.validate_config
   # 厳格モード（警告を FAIL とする）
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ（data/）やログディレクトリ（logs/）は自動作成されますが、権限などに注意してください。

---

## 使い方（主要スクリプト・コマンド）

- ExecutionEngine を起動（本番 / ペーパーに応じて設定）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、paper_trading 用 DB（デフォルト: data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag があると起動せず終了します。
  - PID ファイルは Settings.pid_file_path（デフォルト: data/execution.pid）に書きます。

- Monitoring を起動（SystemMonitor のポーリング）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用します（KABUSYS_ENV に依存しない）
  - 停止フラグ: data/stop_requested.flag が置かれるとループを終了します

- .env 対話ウィザード（再掲）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（再掲）
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。--db でパスを指定するか、環境変数 PAPER_TRADING_SQLITE_PATH を利用。

- AI 関連（プログラムから呼ぶ API）
  - ニュース NLP スコアリング:
    - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数か環境変数 OPENAI_API_KEY を使用
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行モード（development / paper_trading / live）。デフォルト: development
  - paper_trading: 発注はモック。paper_trading 用 SQLite を使用（PAPER_TRADING_SQLITE_PATH）
  - live: 本番（実際発注）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: monitoring ポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある .env および .env.local を自動でロードします。
- 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

Kill / Stop フラグ:
- data/kill.flag: Kill Switch（監視から書き込まれる停止フラグ）。ExecutionEngine はこのファイルを見て停止します。
- data/stop_requested.flag: run_execution/run_monitoring の外部停止フラグ（手動で置くことでループ停止）

---

## ディレクトリ構成（主要ファイル説明）

リポジトリ内部（src/kabusys）の主要モジュール:

- __init__.py
  - パッケージ定義（バージョン等）

- run_execution.py
  - ExecutionEngine 起動スクリプト。paper_trading 時は Mock Broker、専用 SQLite を使用。

- run_monitoring.py
  - SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL で間隔設定。

- config.py
  - Settings クラス：環境変数のラッパー・検証。自動 .env ロードを実行。

- config_setup.py
  - 対話式 .env 作成ウィザード。

- validate_config.py
  - 起動前の設定検証 CLI（必須環境変数・ファイルの存在等をチェック）。

- utils/
  - logging_setup.py: 共通ログ設定（stdout + 日次ローテートファイル）
  - process_priority.py: psutil を使ったプロセス優先度・CPU affinity 設定
  - 他ユーティリティ

- monitoring/
  - monitoring_db.py: SQLite スキーマ作成・永続化レイヤ
  - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py: 注文滞留や約定異常の検出（詳細は該当ファイル参照）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: 条件に基づく data/kill.flag 書き込み
  - monitoring_engine.py: 複数モニタを束ねたポーリング実行

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
  - 発注・注文管理・リスク管理の実装（起動は run_execution.py）

- portfolio/
  - portfolio_builder.py: 候補選定・重み付け
  - position_sizing.py: 発注株数算出・単元丸め・資金配分ロジック
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: momentum/volatility/value 等のファクター計算（DuckDB を利用）
  - feature_exploration.py: 将来リターン・IC・統計サマリ

- ai/
  - news_nlp.py: OpenAI を使ったニュースセンチメントスコアリング（ai_scores へ書込み）
  - regime_detector.py: MA200 乖離 + マクロニュースで市場レジーム判定

- tools/
  - paper_verification_report.py: ペーパートレード DB から PASS/FAIL 判定つきレポート出力

---

## 運用上の注意

- 重要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env を Git にコミットしないでください。
- 本番運用（KABUSYS_ENV=live）の場合、KILL_FLAG_CLEAR_ON_START=1 を設定すると既存の kill flag を自動でクリアしてしまうため危険です。デフォルトは 0 を推奨。
- run_execution/run_monitoring は起動直後にプロセス優先度を "high" に設定します（psutil で実施）。権限不足等で失敗することがありますがログは出力されます。
- AI モジュールを実行するには OpenAI API キー（OPENAI_API_KEY）が必要です。API 呼び出しはレート制限・エラーを考慮してリトライやフォールバック実装がありますが、コストと API 利用ポリシーに注意して利用してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成・インデックス追加・既存列のマイグレーション（例: peak_value / latency_ms の追加）を行います。
- ロギング:
  - setup_logging() は stdout と logs/<app_name>.log（日次ローテーション）を設定します。LOG_DIR 環境変数で保存先を変更できます。
- .env は自動でロードされますが、テストや特殊用途でロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

もし特定のモジュール（例えば ExecutionEngine の詳細・OrderRepository の仕様・AI モジュールのカスタマイズ方法など）の README を別途作成してほしい場合は、対象を指定して依頼してください。