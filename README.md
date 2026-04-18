# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システムのコア実装です。バックテスト／リサーチ用の DuckDB ベースのファクター計算、Execution エンジン（発注管理 / リスク管理 / ブローカー抽象化）、Monitoring（プロセス・データ鮮度・リスク監視）、AI モジュール（ニュース NLP / レジーム判定）などを含みます。

---

目次
- プロジェクト概要
- 主な機能
- 前提（Prerequisites）
- セットアップ手順
- 使い方（主要コマンド例）
- 環境変数（主要なもの）
- ファイル／ディレクトリ構成（概要）
- 補足（運用メモ）

---

## プロジェクト概要

KabuSys はモジュール構成で設計された日本株自動売買フレームワークです。主要コンポーネントは次の通りです。

- ExecutionEngine: 発注処理、OrderManager、RiskManager、Reconciler 等を組み合わせてトレードを実行
- Monitoring: システム状態、注文/約定ログ、リスク（ドローダウン／保有上限）を定期チェックし、必要に応じて Kill Switch を発動
- Research: DuckDB を用いたファクター計算、将来リターン計算、IC / 統計サマリ等
- AI: OpenAI（gpt-4o-mini など）を利用したニュースセンチメント / レジーム判定
- Tools: Paper Trading の検証レポート生成等のユーティリティ

設計方針として「本番 DB と Paper Trading の分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時のフォールバック）」等が採用されています。

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話生成
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading では MockBroker を使用し paper DB を利用
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - ポーリング間隔は MONITOR_POLL_INTERVAL で調整可能（デフォルト 60 秒）
  - 停止フラグ / kill flag を扱う
- DuckDB を用いたファクター計算・リサーチモジュール（kabusys.research）
- AI モジュール（ニュース NLP / レジーム判定） — OpenAI API を利用
- Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- ポートフォリオ構築・ポジションサイズ計算・セクター制約ロジック（kabusys.portfolio）
- ロギングユーティリティ（統一ログ設定、日次ローテート）

---

## 前提（Prerequisites）

- Python 3.9+（型ヒントにより 3.9 以上が想定）
- 必要ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML 検証を行う場合）
- （任意）SQLite / DuckDB ファイルはプロジェクトの data/ 配下に作成されます

インストール例:
```
pip install duckdb psutil openai PyYAML
```

requirements.txt があればそちらを使ってください（本コードベースには含まれていない場合があります）。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成し有効化
3. 依存ライブラリをインストール（上記参照）
4. .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成（プロジェクトルート）。主要なキーは下記「環境変数」を参照。
5. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります。

初期起動時には data/ 以下（例: data/monitoring.db, data/kabusys.duckdb, data/execution.pid）や logs/ が自動作成されます（権限があることを確認）。

---

## 使い方

### 実行（ExecutionEngine）
本番またはペーパートレードの ExecutionEngine を起動します。

- 実行コマンド:
  ```
  python -m kabusys.run_execution
  ```

- ペーパートレードにするには:
  - .env の KABUSYS_ENV を `paper_trading` にするか、環境変数で指定。
  - Paper モードでは MockBrokerClient を使い、デフォルトで `data/paper_trading.db` に書き込みます。

- 起動フロー:
  - PID ファイル（data/execution.pid）を作成
  - 停止フラグ stop_requested.flag が存在する場合は起動しない
  - スレッドでエンジンを走らせ、stop_requested.flag を監視して停止

### 監視（Monitoring）
Monitoring コンポーネントをポーリング起動します。

- 実行コマンド:
  ```
  python -m kabusys.run_monitoring
  ```

- ポーリング間隔を変更:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  デフォルトは 60 秒。0 以下や不正値は無視され 60 秒にフォールバックします。

- 監視は本番 sqlite_path（Settings.sqlite_path）を使用してログを残します（環境に関係なく本番 DB を参照する旨の設計）。

- 停止:
  - 監視プロセスはプロジェクトルートの data/stop_requested.flag を検出するとループを終了します。
  - KillSwitch（監視側）によって data/kill.flag が書かれると ExecutionEngine 側が停止シグナルを受けます。

### Paper Trading 検証レポート
Paper Trading DB（data/paper_trading.db）から期間を指定してレポートを生成します。

- 実行例:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB パスを直接指定:
  ```
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

### AI 関連
- ニューススコアリング:
  - OpenAI API キー（OPENAI_API_KEY）を .env に設定しておくか、score_news などの関数に api_key を渡す必要があります。
- レジーム判定:
  - 同様に OPENAI_API_KEY を使用します。
- 実行はライブラリ関数（kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime）を呼び出す形で実行します。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用関連:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログファイル格納ディレクトリ（デフォルト: logs/）

DB 関連:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）

AI:
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時に必要）

Monitoring / Kill switch:
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" は有効。デフォルト "0"）

Monitoring ポーリング:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

その他: README や .env.example を参照してください（.env は Git 管理に含めないこと）。

簡単な .env の例（敏感情報は伏せる）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## ディレクトリ構成（主要ファイル説明）

（ルート: src/kabusys 以下）

- __init__.py
  - パッケージ定義 & version

- config.py
  - 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）

- config_setup.py
  - 対話式ウィザードで .env を生成する CLI

- validate_config.py
  - 起動前の設定検証 CLI（必須環境変数、YAML ファイル確認等）

- run_execution.py
  - ExecutionEngine の起動スクリプト（PID ファイル管理、Paper モード分離）

- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL）

- execution/
  - 発注周りの実装（BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等）
  - （詳細ファイルはプロジェクト内の execution ディレクトリ参照）

- monitoring/
  - monitoring_db.py — SQLite の監視ログテーブル定義 + DB 操作ラッパー（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py, risk_monitor.py — 注文・リスク監視（risk_monitor はドローダウン監視など）
  - kill_switch.py — kill.flag の作成・評価ロジック
  - monitoring_engine.py — 各モニタを束ねるエンジン
  - alert_manager.py — 通知管理（LINE などへ通知する実装が入る想定）

- portfolio/
  - portfolio_builder.py — 銘柄選択・スコア順ソート等
  - position_sizing.py — 株数・単元丸め・aggregate cap 適用
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB 利用）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ

- ai/
  - news_nlp.py — ニュースを集約し OpenAI でセンチメントを算出し ai_scores に書き込む
  - regime_detector.py — ETF MA とマクロニュースで市場レジーム判定

- tools/
  - paper_verification_report.py — Paper Trading DB からの検証レポート生成

- utils/
  - logging_setup.py — 共通ログ設定（コンソール + 日次ローテートファイル）
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

データ・ログ:
- data/ — SQLite / DuckDB / PID / flag ファイル等を配置（実行時に生成）
- logs/ — ログファイル（app_name に応じたファイルが出力される e.g. logs/execution.log）

---

## 補足（運用メモ）

- Kill Switch / stop flag:
  - 監視モジュールがリスクを検出した場合、data/kill.flag を書き込み、ExecutionEngine はこれを検出して安全に停止します。
  - 管理者が強制停止させたい場合は stop_requested.flag（data/stop_requested.flag）を作ることでプロセスを停止できます（run_* スクリプトで検出）。
- Paper Trading:
  - paper_trading モードでは発注は仮想的に行われ、本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- ログ:
  - logging_setup を各起動スクリプトで呼んでいるため、logs/ に日次ローテーションされたログが残ります。ログディレクトリ作成に失敗するとコンソール出力のみになります。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して安全にカラム追加（簡易マイグレーション）を行います。

---

この README はコードベースの主要機能と運用方法をまとめたものです。詳細は各モジュールの docstring とソースコードを参照してください。必要であれば、起動・デプロイ手順（systemd / Supervisor / Docker-compose）やテスト手順を追加しますのでその旨を教えてください。