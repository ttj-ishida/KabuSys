# KabuSys

日本株自動売買システムのコアライブラリ（README 日本語版）

このリポジトリは、戦略／ポートフォリオ構築、発注実行、監視、研究／解析、AI 補助（ニュース NLP / レジーム判定）などを含む自動売買システムの主要コンポーネントを提供します。本 README はセットアップと主な使い方、ディレクトリ構成の概要を日本語でまとめたものです。

注意: この README はソースコード（src/kabusys 以下）に基づいて作成しています。実行前に必須環境変数や API キーの設定が必要です。設定ファイルは .env を用いて管理します。

## プロジェクト概要

- 目的: 日本株の自動売買を支援するライブラリ／実行エンジン群（戦略生成、ポートフォリオ構築、注文管理、監視、アラート、研究用ユーティリティ、AI によるニュース分析など）。
- 設計方針:
  - モジュールは可能な限り副作用を避け、純粋関数や明確な I/O 層（SQLite / DuckDB）で分離。
  - 本番 DB とペーパートレード DB を分離（KABUSYS_ENV に依存）。
  - .env（環境変数）で設定管理。対話式ウィザード & 検証 CLI を提供。
  - OpenAI を使ったニュース解析やマクロセンチメント判定を組み込み可能（API キー必須）。

## 主な機能一覧

- 実行エンジン起動 / 停止管理
  - run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離。
  - ストップフラグ（data/stop_requested.flag）で安全に停止可能。
  - PID ファイル（data/execution.pid）管理。

- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）。
  - system_status / trade_logs / risk_logs / positions / dashboard などの永続化（SQLite）とリスク判定、Kill Switch を実装。
  - MonitoringEngine による複数モニタの統合・アラート呼び出し。

- リスク監視 / Kill Switch
  - RiskMonitor: ドローダウン・ポジション上限監視。必要に応じて risk_logs に記録。
  - KillSwitch: 条件により data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送信。

- ポートフォリオ構築（純粋関数）
  - 銘柄選定、スコア・等分配の重みづけ、単元株丸め、リスクベース配分など（portfolio/*）。

- 研究 / 解析（DuckDB）
  - ファクター計算（モメンタム・ボラティリティ・バリューなど）、将来リターン、IC 計算、統計サマリ（research/*）。
  - DuckDB 接続を受け取り SQL＋Python で高速に解析。

- AI 機能（OpenAI）
  - news_nlp: ニュースを LLM（gpt-4o-mini）でセンチメント解析して ai_scores に保存。
  - regime_detector: ETF（1321）の MA200 乖離＋マクロニュースセンチメントを合成して市場レジームを判定し DB に保存。
  - OpenAI API キー（OPENAI_API_KEY）が必要。API 呼び出しはリトライ/フェイルセーフ付き。

- CLI ツール
  - 環境設定ウィザード: python -m kabusys.config_setup（.env を対話式作成／更新）
  - 設定検証: python -m kabusys.validate_config（起動前に .env / config/*.yaml の問題検出）
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report（ペーパートレード DB から期間集計）

- ロギング・プロセス優先度
  - utils/logging_setup: stdout + 日次ローテートファイル（logs/<app>.log）
  - utils/process_priority: OS を考慮してプロセス優先度設定（high/normal/low）

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリをインストール
   - 必須（実行 / 監視）: duckdb, psutil, openai（AI 機能使用時）、PyYAML（設定検証で YAML を検証したい場合）
   - 例:
     ```
     pip install duckdb psutil openai pyyaml
     ```
   - sqlite3 は標準ライブラリに含まれます。

4. .env 作成（対話式ウィザードを推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成します。手動で作成する場合は .env.example を参照してください。

5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告もエラー扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```

6. 必要なデータディレクトリを作成（.env のパスに応じて）
   ```
   mkdir -p data logs
   ```

注意: Settings モジュールは自動的にプロジェクトルートの .env をロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。.env は Git にコミットしないでください。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

AI 機能を使う場合:
- OPENAI_API_KEY

主な設定変数（よく使うもの）
- KABUSYS_ENV: development | paper_trading | live（既定: development）
- DUCKDB_PATH（既定: data/kabusys.duckdb）
- SQLITE_PATH（既定: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（既定: data/paper_trading.db）
- LOG_LEVEL（既定: INFO）
- PAPER_FILL_MODE（paper_trading 用: instant | partial | never | reject）

## 使い方（実行例）

- ExecutionEngine（発注実行）を起動
  - 通常（環境は .env の KABUSYS_ENV に依存）
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレードで動かす場合は .env で KABUSYS_ENV=paper_trading を設定すると MockBroker を使い、data/paper_trading.db に記録されます。

  - 停止:
    - run_execution は data/stop_requested.flag の存在を監視して安全停止します（同様に run_monitoring も監視）。
    - Kill Switch（データに応じて）で data/kill.flag が書き込まれると ExecutionEngine に停止シグナルを送ります。
    - 手動で停止するには stop flag を作成:
      ```
      mkdir -p data
      echo "manual stop" > data/stop_requested.flag
      ```

- Monitoring（監視ループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数でポーリング間隔を上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
    （0 以下や不正値はデフォルト 60 秒にフォールバック）

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスの指定:
    ```
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
    ```

- .env の自動ロード抑止（テスト時など）
  ```
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 python -m kabusys.validate_config
  ```

- ログ
  - デフォルト出力:
    - コンソール（stdout）
    - ファイル: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテート、30 日保持）
  - ログレベルは LOG_LEVEL または setup_logging の引数で制御します。

## 重要な実行フラグ・ファイル

- data/stop_requested.flag
  - 存在すると run_execution.run_session などのループを安全に抜けます（終了指示）。
- data/kill.flag
  - KillSwitch が書き込むファイル。ExecutionEngine に対して停止（Kill）を要求するために使用されます。
  - Settings で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアします（本番では 0 を推奨）。
- data/execution.pid
  - ExecutionEngine の PID ファイル（起動スクリプトで指定）。

## セキュリティ注意点

- .env に API キーやパスワード（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / OPENAI_API_KEY など）を含めますが、絶対に Git にコミットしないでください。
- KABUSYS_ENV=live の場合は特に注意して設定を確認してください（validate_config は live 時に追加の警告を出します）。

## ディレクトリ構成（主要ファイル・モジュール）

（src/kabusys を基準）

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数/.env の読み込みと検証）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（PID / stop flag 管理、paper_trading 分離）
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを LLM でセンチメント解析して ai_scores に書込む
    - regime_detector.py
      - MA200 + マクロセンチメントで市場レジーム判定
  - monitoring/
    - monitoring_db.py
      - SQLite テーブルの初期化と永続化ラッパー（MonitoringDB）
    - system_monitor.py
      - システム状態（CPU/メモリ/ディスク）・データ鮮度・Execution の PID チェック
    - trade_monitor.py
      - （trade 関連の監視ロジック: 滞留注文や約定異常の検出）※コードベースに部分あり
    - risk_monitor.py
      - ドローダウン・ポジション数の監視
    - kill_switch.py
      - kill.flag の作成・管理
    - monitoring_engine.py
      - 各モニタを束ねてポーリング・アラート発行
    - alert_manager.py
      - （アラート送信ロジック：LINE 等）※実装参照
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など
      - 発注ロジック・注文管理・リスク管理・ブローカー抽象化
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算
    - position_sizing.py
      - 単元丸め・リスクベースの株数計算
    - risk_adjustment.py
      - セクターキャップ・レジーム乗数
  - research/
    - factor_research.py
      - モメンタム / ボラティリティ / バリューなどのファクター計算（DuckDB）
    - feature_exploration.py
      - 将来リターン / IC / 統計サマリ
  - tools/
    - paper_verification_report.py
      - ペーパートレード DB から検証レポート生成
  - utils/
    - logging_setup.py
      - ログの一元設定（stdout + 日次ファイル）
    - process_priority.py
      - プロセス優先度 / CPU affinity ユーティリティ

（その他）
- data/
  - 実行時 DB（monitoring.db / paper_trading.db 等）、flag/pid ファイル、logs/（デフォルト）などを格納する想定。

## 開発・運用上のメモ

- DB（監視用 SQLite と分析用 DuckDB）は分離されるように設計されています。ペーパートレードは本番 DB と完全分離するため、KABUSYS_ENV による切り替えを活用してください。
- OpenAI 呼び出しは外部 API 依存かつコストが発生します。API キー管理やレート制御には注意してください。
- ログディレクトリの作成に失敗するとファイルハンドラはスキップされコンソールのみになります（警告が出ます）。
- 各 CLI（config_setup / validate_config / tools）はモジュールとして実行できます（python -m kabusys.…）。

## 参考コマンド一覧

- .env の作成（ウィザード）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```

- 監視ループ起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースの主要点をまとめたものです。各モジュールの詳細な仕様や拡張方法は該当ソース（src/kabusys 以下）内の docstring / コメントを参照してください。質問や追加したい項目があれば教えてください。