# KabuSys

日本株向け自動売買システム（ライブラリ＋起動スクリプト群）

このリポジトリは、売買ロジック・ポートフォリオ構築・監視・AI 補助機能（ニュース NLP / レジーム判定）などを含む自動売買基盤の実装です。実行にはローカル DB（SQLite / DuckDB）と外部 API（kabuステーション / J-Quants / OpenAI 等）が必要になります。

---

## 概要

- 売買実行エンジン（ExecutionEngine）と監視プロセス（Monitoring）が分離された構成
- Paper Trading（模擬発注）と Live（実口座）の運用モードをサポート
- DuckDB を用いたリサーチ／ファクター計算モジュール
- OpenAI を用いたニュースセンチメント（ai/news_nlp）とレジーム判定（ai/regime_detector）
- 監視データは SQLite（監視 DB）へ永続化
- kill.flag / stop_requested.flag によるプロセス制御（Graceful stop / Kill switch）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（paper_trading 時は MockBrokerClient を使用し専用 DB に記録）
  - run_monitoring.py: SystemMonitor（システム資源・データ鮮度等）をポーリング
- 環境セットアップ / 検証
  - config_setup.py: .env を対話作成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI（--strict オプションあり）
- リサーチ / ファクター計算
  - research.factor_research: モメンタム / ボラティリティ / バリュー計算
  - research.feature_exploration: 将来リターン計算、IC（Information Coefficient）等
- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定 / 重み付け
  - portfolio.position_sizing: 株数計算（単元丸め、リスク制約）
  - portfolio.risk_adjustment: セクター上限・レジーム乗数
- AI 機能
  - ai.news_nlp: ニュース記事を集約し OpenAI に投げて銘柄ごとのスコアを ai_scores テーブルへ書き込み
  - ai.regime_detector: ETF（1321）とマクロニュースの LLM スコアを合成して市場レジーム判定
- 監視・リスク管理
  - monitoring/*.py: MonitoringDB（SQLite 永続化）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine
- ユーティリティ
  - utils.logging_setup: 統一的なログ設定（コンソール + 日次ローテートファイル）
  - utils.process_priority: プロセス優先度・CPU affinity 設定

---

## 前提（Prerequisites）

- Python 3.9+（コードは型ヒント等を使用）
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証機能で任意）
- SQLite は標準ライブラリで使用可能

インストール例（仮に venv を使う場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（requirements.txt は本リポジトリに含まれていないため、用途に応じて適宜追加してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して依存パッケージをインストール
   （上の Prerequisites 参照）

3. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードが .env を生成します。必要な必須変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   そのほかの主要環境変数（デフォルトが存在するもの）:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（paper_trading モード時に使用）
   - LOG_LEVEL — デフォルト: INFO
   - OPENAI_API_KEY — ai モジュールを使う場合必須

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告も含めて厳しくチェックしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. ディレクトリと権限確認
   - logs/（ログ出力先）は自動作成されますが、権限に注意
   - data/ 配下に DB ファイル（data/monitoring.db, data/paper_trading.db）やフラグファイルが置かれます

---

## 使い方（実行方法）

- ExecutionEngine を起動（バックグラウンドで実行する場合はプロセス管理ツールを利用してください）
  ```bash
  python -m kabusys.run_execution
  ```
  特記事項:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に取引ログ等を記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します（安全ガード）。
  - 実行中は pid ファイル（デフォルト data/execution.pid）を作成します。

- Monitoring を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  オプション:
  - ポーリング間隔を環境変数で上書き: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に関わらず）

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- .env を編集したときは validate_config でチェックしてから起動してください。

---

## 停止・Kill / フラグファイル

- Graceful stop（外部から監視ループや実行エンジンを停止したい場合）
  - run_monitoring.py / run_execution.py はプロジェクトルートの data/stop_requested.flag（stop_requested.flag）を監視しており、ファイルが存在するとループを抜けて終了します。
  - 例:
    ```bash
    touch data/stop_requested.flag
    ```
- Kill Switch（Monitoring が条件を満たした時に ExecutionEngine を停止する仕組み）
  - Monitoring の KillSwitch は data/kill.flag を書き込みます（デフォルトの kill_flag_path は Settings.kill_flag_path）。
  - ExecutionEngine は起動時・稼働中に kill.flag を検出して安全に停止します。
  - 注意: 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（デフォルトがあるもの / 説明）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI 利用時に必須
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（Settings クラス参照）

詳細は `src/kabusys/config.py` を参照してください。

---

## ログ

- ログはデフォルトで logs/ ディレクトリへ日次ローテート（30日保持）されます。
- 環境変数 LOG_DIR で出力先を変更できます。
- 全スクリプトは起動時に utils.logging_setup.setup_logging を呼んで統一的に設定します。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理
  - config_setup.py — .env 作成ウィザード（CLI）
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - data/ (想定) — data ファイル群（DB / フラグ / pid）
  - logs/ (想定) — ログ出力先
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py — 市場レジーム判定（LLM + ETF MA）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在する場合)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - tools/
    - paper_verification_report.py

（上は主要ファイルの抜粋です。詳細は src/kabusys 以下をご確認ください）

---

## 開発・運用上の注意

- Paper Trading と Live の DB は分離されています。paper_trading モードでは settings.paper_sqlite_path を使用するため、本番データに影響を与えません。
- AI（OpenAI）呼び出しはコストとレイテンシの観点で注意が必要です。API キーは安全に管理してください。
- run_* スクリプトは起動直後にプロセス優先度を "high" に設定しようとします（psutil による）。権限がない場合は警告を出してスキップします。
- config/*.yaml（各種設定テンプレート）が必要な場合は scripts 等で生成するワークフローを用意してください。validate_config は PyYAML が無いと YAML 検証をスキップします。
- ログディレクトリの作成に失敗した場合、ファイル出力は無効化されコンソール出力のみになります。

---

## よく使うコマンドまとめ

- .env 作成ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution 起動
  ```bash
  python -m kabusys.run_execution
  ```

- Monitoring 起動（ポーリング間隔 30 秒に変更）
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 参考

- 設定の詳細は src/kabusys/config.py を参照してください（デフォルト値や検証ロジックが実装されています）。
- ロギングやファイルパスのカスタマイズは utils.logging_setup と環境変数（LOG_DIR / LOG_LEVEL）を利用してください。
- AI 関連は OpenAI SDK のバージョンに依存します。OpenAI SDK の API 変更に伴いラッパー関数（_call_openai_api）を差し替え可能な設計になっています。

---

README はここまでです。さらに具体的な起動例、systemd ユニットファイル、Docker 化、CI テスト、または個別モジュールの API ドキュメントが必要であれば教えてください。