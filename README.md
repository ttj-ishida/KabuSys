# KabuSys

日本株向けの自動売買システム（プロトタイプ / ライブラリ群）。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AIベースのニュース・レジーム判定等のコンポーネントを含みます。

主な目的は「現物日本株の戦略実装 → 発注 → 監視」までの基本ワークフローを提供することです。実行用スクリプトと対話式環境設定ウィザード / 検証ツールが含まれ、paper trading（ペーパートレード）モードと本番モードを切り替え可能です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数とデフォルト設定
- ディレクトリ構成（主要ファイル）
- 補足・運用メモ

---

## プロジェクト概要

- 発注エンジン（ExecutionEngine）と監視（Monitoring）を分離して実装。
- Paper Trading（擬似ブローカー）をサポートし、本番データベースと分離して検証可能。
- DuckDB を用いたファクター計算 / リサーチ機能。
- OpenAI（gpt-4o-mini）を利用したニュースセンチメントおよびマクロセンチメントによるレジーム判定（APIキー必須）。
- 監視側は SystemMonitor / TradeMonitor / RiskMonitor をまとめる MonitoringEngine を提供し、KillSwitch による停止フラグ書き込みで ExecutionEngine を安全停止できます。
- ログはコンソール(stdout) と日次ローテートファイル出力（logs/*.log）に対応。

---

## 機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による挙動切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔制御）
- 設定管理
  - config_setup.py: .env を対話式に生成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI（--strict オプションあり）
- 監視
  - MonitoringEngine：複数モニタをまとめてポーリング、アラート送出や KillSwitch 評価
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度/プロセス生存など
  - RiskMonitor：ドローダウン・ポジション上限監視、risk_logs への記録
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止する仕組み
- 発注系
  - BrokerClientFactory（ブローカー抽象化。paper_trading 時は MockBrokerClient を使用）
  - OrderManager / OrderRepository / Reconciler / RiskManager / ExecutionEngine
- ポートフォリオ構築（純粋関数）
  - 銘柄選定、等配分 / スコア配分、ポジションサイジング、セクターキャップ、レジーム乗数など
- リサーチ
  - factor_research: momentum / volatility / value などのファクター計算（DuckDB 経由）
  - feature_exploration: 将来リターン計算、IC（情報係数）など
- AI
  - news_nlp: ニュースのセンチメントを OpenAI に投げて ai_scores に保存
  - regime_detector: ETF(1321) の MA とマクロセンチメントを組み合わせた市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（SQLite を集計）

---

## セットアップ手順（開発/ローカル向け）

1. リポジトリをクローンしてプロジェクトルートへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 必要ライブラリ（代表）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例（pip）:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - ※ requirements.txt がない場合は上記を手動でインストールしてください。

4. 環境変数の準備（.env）
   - 対話式ウィザードで初期作成:
     ```
     python -m kabusys.config_setup
     ```
   - 生成した .env を編集し、必須変数を設定してください（下記参照）。

5. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   # 警告を厳密に FAIL 扱いする場合
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（主要コマンド）

- ExecutionEngine（発注エンジン）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper DB（data/paper_trading.db）に記録します。
  - 起動中は data/execution.pid に PID を記録（設定により変更可）。
  - data/stop_requested.flag が存在すると起動/実行中に停止します。

- Monitoring（システム監視）を起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。
  - 監視は monitoring DB（settings.sqlite_path）に書き込み、DuckDB を分析用に使用。
  - run_monitoring は KABUSYS_ENV に関わらず「本番 sqlite_path（デフォルト data/monitoring.db）」を使用します。
  - data/stop_requested.flag によりループを停止できます。

- 対話式 .env ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート作成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションで SQLite パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も利用可能。

- 研究／バッチ処理・AI モジュールはライブラリ関数として呼び出して使用します（例: kabusys.ai.score_news）。

---

## 環境変数（主要）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主要（任意／デフォルトあり）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト: INFO）
- LOG_DIR — ログディレクトリ（デフォルト: logs/）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）
- OPENAI_API_KEY — OpenAI を使う機能で必要（news_nlp / regime_detector）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）
- PAPER_FILL_MODE — paper_trading 時の約定モード (instant / partial / never / reject)

注意:
- .env 自動ロード機能あり（プロジェクトルートの .env / .env.local）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- .env は機密情報を含むため絶対に Git にコミットしないでください。

---

## デフォルトファイルパス（重要なもの）

- データ / フラグ
  - data/monitoring.db (SQLite, 監視 DB / デフォルト SQLITE_PATH)
  - data/paper_trading.db (SQLite, paper trading 用)
  - data/kabusys.duckdb (DuckDB)
  - data/kill.flag (KillSwitch が書き込む停止フラグ)
  - data/stop_requested.flag (起動スクリプトが監視する停止フラグ)
  - data/execution.pid (ExecutionEngine の PID ファイル)

- ログ
  - logs/<app_name>.log（日次ローテート）

---

## ディレクトリ構成（主要ファイル・モジュール）

以下は src/kabusys 以下の主なファイルと役割です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン, エクスポート）
  - config.py — Settings クラス（環境変数読み取り・検証）、.env 自動ロード
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 設定検証 CLI

  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - utils/
    - logging_setup.py — ロギング初期化 (stdout + TimedRotatingFileHandler)
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・永続化レイヤ
    - system_monitor.py — システム状態 / データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション監視
    - trade_monitor.py — （注文関連監視: ファイル内にあり）※（実装参照）
    - kill_switch.py — Kill Switch（kill.flag 書き込み）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — アラート送信（LINE等）※（実装参照）

  - execution/
    - execution_engine.py — ExecutionEngine（セッション管理、発注ループ）
    - broker_factory.py — ブローカークライアント生成（本番/Mock 切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注関連コンポーネント

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - data/
    - pipeline.py / stats.py 等（DuckDB を使ったデータ取得・統計ユーティリティ）

  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py — マクロ + MA を使ったレジーム判定

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール

> 注: 上のリストは主要ファイルを抜粋したものです。詳細は各モジュールの docstring を参照してください。

---

## 補足・運用メモ

- Paper Trading
  - KABUSYS_ENV=paper_trading では mock ブローカーを用い、paper_trading 用 SQLite に記録します。本番 DB とは分離されます。

- Kill Switch / Stop
  - KillSwitch は監視側の判断で data/kill.flag に理由を書き込みます。ExecutionEngine 起動時は kill.flag の存在を確認するガードがあるため、本番停止を即時化できます。
  - 起動スクリプトは data/stop_requested.flag の存在を監視し、存在すれば優雅に終了します（メンテナンス用）。

- ログ
  - setup_logging() は logs ディレクトリを作成しようとしますが失敗した場合はコンソールのみ出力にフォールバックします。

- OpenAI
  - news_nlp / regime_detector は OPENAI_API_KEY を使用します。API 呼び出しはリトライ処理やパース検証が入っており、失敗時は安全側のフォールバック（スコア 0.0 等）になりますが、API キー未設定時は関数が ValueError を投げます。

- データ鮮度
  - SystemMonitor は DuckDB の prices_daily 等を参照してデータ鮮度を判定します（デフォルトでは最大 3 日差を許容）。

- 依存関係
  - duckdb, psutil, openai が主要な外部依存です。config の YAML 検証は PyYAML を使いますが必須ではありません（未インストール時は YAML 検証をスキップします）。

---

README は以上です。各モジュールの詳細な使い方（ExecutionEngine の設定やブローカー実装、OrderManager の API 等）は該当ファイルの docstring を参照してください。必要であれば、起動・運用手順や設定例（.env.example）を追加で作成します。どの部分を詳しく書いて欲しいか指定してください。