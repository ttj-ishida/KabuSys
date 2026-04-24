# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ兼各種起動スクリプト群）です。  
このREADMEはリポジトリ内の主要モジュールをもとに、セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

注意: 本 README は配布されたソースコードを基に作成しています。実運用時は必ず設定の検証、テスト環境での動作確認を行ってください。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つコンポーネントを含む自動売買システムです。

- ExecutionEngine（発注エンジン）
  - 実口座 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - ブローカークライアントの抽象化（BrokerClientFactory）
  - 注文管理、リスク管理、再整合処理など
- Monitoring（監視）
  - システム稼働状況、データ鮮度、注文ログ、リスク指標を監視
  - Kill Switch（条件により execution を停止するフラグ）
  - 監視ログは SQLite（monitoring.db）へ永続化
- Research / Portfolio（リサーチ・ポートフォリオ構築）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - ポートフォリオ候補選定・重み計算・ポジションサイズ計算
- AI系（OpenAI を用いたニュースセンチメント、レジーム判定）
- 各種ユーティリティ
  - 環境設定ウィザード（.env 生成）
  - 設定検証 CLI
  - ロギング設定、プロセス優先度等ユーティリティ
  - Paper Trading 検証レポート生成スクリプト

---

## 主な機能一覧

- 環境設定
  - .env 対話式ウィザード（kabusys.config_setup）
  - 自動 .env ロード（.env / .env.local、OS 環境変数が優先）
- 設定検証
  - 必須環境変数・設定ファイルの事前チェック（kabusys.validate_config）
- 実行
  - run_execution.py: ExecutionEngine の起動スクリプト
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db を使用して本番 DB と分離
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視は環境に依らず本番 sqlite_path を使用
- 監視 / アラート
  - system_monitor: CPU/メモリ/Disk、プロセス生存、データ鮮度の監視
  - trade_monitor / risk_monitor: 注文滞留、約定異常、ドローダウン、ポジション上限等の検出
  - KillSwitch: 指定条件で data/kill.flag を書き込み ExecutionEngine の停止をトリガ
  - MonitoringDB: SQLite に監視ログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- ポートフォリオ構築（portfolio）
  - 候補選定、等重・スコア重み、リスク調整（セクター制限）、ポジションサイズ計算
- AI（openai）
  - news_nlp: ニューステキストを集約し LLM でセンチメントスコアを生成し ai_scores に保存
  - regime_detector: ETF の MA200 乖離とマクロニュースに基づく市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成

---

## 前提（Prerequisites）

- Python 3.10 以上（typing の | 記法等を使用しているため）
- 推奨パッケージ（最低限の例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- その他（環境により）:
  - SQLite は標準ライブラリで利用可能
  - OpenAI を利用する機能は OPENAI_API_KEY が必要

例（仮想環境作成・パッケージインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai PyYAML
```

プロジェクトに requirements.txt がない場合は上記を参考にインストールしてください。

---

## セットアップ手順

1. リポジトリをクローンし、ソースルートに移動する
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - ペーパートレード専用 DB パスは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
4. 設定検証（起動前に必ず実行推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合
   python -m kabusys.validate_config --strict
   ```
5. ログディレクトリ作成は自動（logs/）ですが、権限等で作成に失敗する場合は手動で用意してください。

注意:
- 自動で .env を読み込む挙動は config.py により行われます。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env.local が存在すると .env の値を上書きします。OS 環境変数が最優先です。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（デーモン化等はシステム側で行ってください）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は paper-trading モード（MockBrokerClient）になります。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中は data/execution.pid に PID を書きます。

- Monitoring を起動（ポーリング監視）
  ```bash
  # デフォルト 60 秒間隔
  python -m kabusys.run_monitoring
  # 環境変数で間隔を変更（例: 30秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視ループは data/stop_requested.flag を見て停止します。
  - Monitoring は環境（KABUSYS_ENV）に関係なく本番 sqlite_path（SQLITE_PATH）を使用します。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```
  - 簡易的な PASS/FAIL 判定を提供します（稼働率・約定率・レイテンシ等）。

- 設定検証・ウィザード
  ```bash
  python -m kabusys.config_setup
  python -m kabusys.validate_config --strict
  ```

- AI 機能（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=...) を呼ぶ際は DuckDB 接続と OPENAI_API_KEY が必要です（api_key 引数で指定可）。
  - regime_detector.score_regime(conn, target_date, api_key=...) も同様。

---

## 主要な環境変数（代表例）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必要）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に data/kill.flag を自動クリアするか（0/1、デフォルト 0）

設定は .env / .env.local / OS 環境変数のいずれかで与えます（OS 環境変数が最優先）。

---

## ログ・PID・フラグファイル

- ログ: デフォルト logs/<app_name>.log（setup_logging で設定）
- PID: data/execution.pid（ExecutionEngine 起動時）
- 停止フラグ:
  - data/stop_requested.flag: run_execution / run_monitoring の外部停止フラグ（存在するとループが終了）
  - data/kill.flag: KillSwitch が書き込むフラグ（ExecutionEngine 停止のために作成）

---

## データベース挙動

- monitoring 用 SQLite（デフォルト data/monitoring.db）に以下テーブルを持ちます（init_monitoring_db により必要なら作成・マイグレーションされます）:
  - system_status, trade_logs, positions, risk_logs, dashboard
- DuckDB（デフォルト data/kabusys.duckdb）はリサーチ / AI の高速集計に使用します。
- ペーパートレードは paper_trading 用の SQLite を使って本番 DB と完全分離できます（KABUSYS_ENV=paper_trading）。

---

## 開発者向けメモ / 注意点

- config.py はプロジェクトルート（.git または pyproject.toml）を基に .env 自動読み込みを行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- Logging は全スクリプトで共通の setup_logging を使用することで統一されています。
- process_priority.set_process_priority は psutil を使って OS に依らない優先度設定を試みますが、権限不足等で失敗することがあります（Warning ログ）。
- AI 系のモジュールは OpenAI の呼び出しでネットワークエラーやレート制限を考慮したリトライロジックを持っていますが、実行には API キーとネットワーク環境が必要です。
- Research / Portfolio 関数群は副作用を持たない純粋関数設計が基本です（テストしやすい）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル・モジュールのツリー（この README 作成時点の抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照あり)
    - kill_switch.py
    - alert_manager.py (参照あり)
  - execution/
    - broker_factory.py (参照あり)
    - execution_engine.py (参照あり)
    - order_manager.py (参照あり)
    - order_repository.py (参照あり)
    - reconciler.py (参照あり)
    - risk_manager.py (参照あり)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/   (実行時に生成されることがある: monitoring.db / paper_trading.db / kabusys.duckdb / kill.flag 等)

注: 一部ファイルは参照のみ（ここに全ソースがあるとは限りません）が、READMEは現在提供されたコードを基に構成しています。

---

## よくある操作例

- Development（ローカル）でモニタリングだけ一度だけ実行して結果を確認したい:
  - MonitoringEngine をテスト用途に run_once で呼ぶコードを作るか、run_monitoring.py を短時間の MONITOR_POLL_INTERVAL で起動。
- Paper Trading のデータを検証:
  - PAPER_TRADING_SQLITE_PATH を指して paper_verification_report を実行。
- .env を生成して設定チェック:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config --strict

---

## ライセンス・バージョン

パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" を参照してください。  
ライセンス情報はリポジトリルートの LICENSE ファイル等を参照してください（この配布物には含まれていない場合があります）。

---

不足している情報や、README に追記したい具体的な利用シナリオ（例: systemd ユニットのサンプル、Docker 起動方法、CI 設定など）があれば教えてください。必要に応じて追記・改善します。