# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ内ドキュメント（README）。  
本README はローカル開発 / ペーパートレード / 本番実行のための概要・セットアップ・使い方・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムです。主な機能は以下のとおりです。

- 戦略・リサーチ（ファクター計算、特徴量探索）
- ポートフォリオ構築（候補選定、重み計算、単元株処理、ポジションサイジング）
- ExecutionEngine（発注管理、リスク管理、注文照合）
- Monitoring（システム稼働・データ鮮度・注文状態・リスク監視）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定） — OpenAI API を利用
- 開発用ツール（.env ウィザード、設定検証、Paper Trading 検証レポート生成）

コードは src/kabusys 以下にまとまっており、DB は DuckDB（分析）と SQLite（監視・ペーパートレードログ等）を使用します。

---

## 機能一覧

- config
  - 自動 .env 読み込み（プロジェクトルート検出）
  - Settings クラスで環境変数を型安全に取得
  - config_setup.py: 対話式 .env ウィザード
  - validate_config.py: 起動前検証 CLI
- execution
  - ExecutionEngine / OrderManager / RiskManager / Reconciler 等（発注処理とリスク制御）
  - BrokerClientFactory により実際環境 or Mock（paper_trading）を切替
- monitoring
  - SystemMonitor: CPU/メモリ/Disk、Execution プロセスの生存、データ鮮度監視
  - TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / AlertManager（アラート送信は LINE 等）
  - monitoring_db: SQLite に監視ログを永続化
- portfolio
  - 候補選定、重み計算、セクター制限、サイズ決定ロジック（純粋関数）
- research
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 特徴量探索・IC 計算・統計サマリー
- ai
  - news_nlp: OpenAI を用いたニュースセンチメント集計（ai_scores に書き込み）
  - regime_detector: ma200 とマクロニュースでレジーム判定
- tools
  - paper_verification_report: ペーパートレード結果の検証レポート生成

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows PowerShell
   ```

3. 必要なパッケージをインストール  
   ※ 実際の requirements ファイルはプロジェクトに依存します。少なくとも以下をインストールしてください：
   - duckdb
   - psutil
   - openai (AI 機能を使う場合)
   - PyYAML（config 検証で YAML を検証する場合）
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. .env の準備  
   - 対話式ウィザードで生成できます:
     ```
     python -m kabusys.config_setup
     ```
   - もしくはリポジトリの .env.example を参考に `.env` をプロジェクトルートに作成してください。最低必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （AI 機能を使う場合）OPENAI_API_KEY を環境変数か引数で渡す

5. ディレクトリ作成（ログ・データ領域）
   ```
   mkdir -p data logs
   ```

注意：
- Settings はプロジェクトルート（.git ある場所、または pyproject.toml のある場所）を基準に .env を自動ロードします。テスト等で自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 主要環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- OPENAI_API_KEY（AI 機能利用時に必要）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag をクリアするか。開発時のみ 1 を使う）

---

## 使い方（実行・CLI）

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告もエラー扱い
  ```

- 実行エンジン起動（ExecutionEngine）
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV に依存
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード指定例:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します（本番 DB と完全分離）。

- 監視ループ起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数で上書き可能:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は常に本番の sqlite_path を使用（monitoring は環境に依存しない本番 DB を参照）。

- .env 対話式セットアップ
  ```
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルトの DB パスを変更する場合:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

---

## ログ・停止フラグ・プロセス優先度

- ログ
  - デフォルトは logs/ ディレクトリに日次ローテートで保存されます（kabusys.utils.logging_setup）。
  - ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で指定可能。

- 停止制御
  - run_execution / run_monitoring はプロジェクト内 data/stop_requested.flag を監視／参照しています。これを作成するとスクリプトが安全に停止します。
  - Monitoring 側には KillSwitch（data/kill.flag）機能があり、閾値超過時に kill.flag を書き込み ExecutionEngine 停止を促します。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では推奨しません）。

- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を試みます（psutil を用いるため権限が必要な場合があります）。失敗しても警告を出し続行します。

---

## よくあるトラブルと対処

- OpenAI API 関連
  - OPENAI_API_KEY が未設定だと AI 機能はエラーになるかスキップします。API 利用時は必ず設定してください。
  - レート制限・タイムアウト対策は取り入れてありますが、過度な呼び出しは避けてください。

- データベース / ファイル
  - 初回は data ディレクトリや logs ディレクトリがないとファイル作成に失敗することがあります。手動で作るか起動時に自動作成される設定を確認してください。
  - monitoring_db.init_monitoring_db は冪等でテーブル・カラムのマイグレーションも一部行います。

- プロセス優先度設定に失敗する（AccessDenied）
  - 権限が足りない場合は警告が出てスキップされます。必要なら sudo 等で実行するか OS の権限設定を見直してください。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主なファイルと役割です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン）
  - config.py — 環境変数/.env の読み込みと Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- src/kabusys/utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

- src/kabusys/execution/  （発注関連）
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
  （実装詳細は該当ファイル参照）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数算出
  - risk_adjustment.py — セクター上限・レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

- src/kabusys/ai/
  - news_nlp.py — ニュースセンチメントスコア算出（OpenAI）
  - regime_detector.py — 指数 + マクロニュースで市場レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

- その他
  - config/*.yaml — システム/データ/戦略/リスク/実行/監視 の設定（存在しない場合はスクリプトで生成）
  - data/ — デフォルトの DB / PID / フラグファイル等（実行環境で生成される）
  - logs/ — ログファイル

---

## 開発メモ / 注意点

- 多くのモジュールは「外部リソースへアクセスしない」方針のテスト可能な純粋関数群と、DB/API を扱うサイドエフェクト層に分離されています（テスト容易化）。
- レガシー DB バージョン差や DuckDB の executemany 制約など、互換性対策がコード中にあります。DB のバージョンやライブラリ更新時は注意してください。
- 本番（KABUSYS_ENV=live）時は LINE 通知や kill flag の設定に特に注意してください（KILL_FLAG_CLEAR_ON_START は本番で 0 推奨）。

---

もし README に追加して欲しい情報（例:具体的な設定例、requirements.txt、デプロイ手順、CI 設定、API モック実装の詳細など）があれば教えてください。必要に応じて追記します。