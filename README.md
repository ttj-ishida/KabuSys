# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、戦略リサーチ、ポートフォリオ構築、発注実行、監視、AI（ニュース／レジーム判定）を含む自動売買の主要コンポーネントを提供します。各コンポーネントはモジュール化されており、ローカル開発・ペーパートレード・本番（live）を切り替えて動作します。

---

## 概要

主な目的:

- DuckDB / SQLite を使ったデータ処理と永続化
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算）
- ExecutionEngine による発注管理（本番 / ペーパートレードの分離）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- OpenAI を用いたニュースセンチメント / レジーム判定（オプション）
- 設定ウィザード & 検証ツールを通じた起動前チェック

設計方針としては「フェイルセーフ」「ルックアヘッドバイアス排除」「DB/ファイルによる明瞭な分離」を重視しています。

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートの .env/.env.local）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行・監視
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 SQLite に記録
    - 停止フラグ（data/stop_requested.flag）および kill.flag による制御
  - Monitoring 起動スクリプト（kabusys.run_monitoring）
    - SystemMonitor をポーリングして system_status 等のログを記録
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）

- 監視サブシステム
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存チェック、データ鮮度チェック
  - TradeMonitor: 発注ログの整合・滞留チェック（コード中に存在）
  - RiskMonitor: ドローダウン・ポジション上限の監視（risk_logs, dashboard へ記録）
  - KillSwitch: 条件に応じて data/kill.flag を書き込む

- ポートフォリオ
  - 銘柄選定 / 等重・スコア重み付け（portfolio.portfolio_builder）
  - セクター上限・レジーム乗数（portfolio.risk_adjustment）
  - 株数決定・単元丸め・資金制限（portfolio.position_sizing）

- リサーチ / 解析
  - ファクター計算（momentum / value / volatility） — DuckDB を想定（research.factor_research）
  - 将来リターン / IC / 統計サマリ（research.feature_exploration）

- AI（任意）
  - ニュースを LLM（OpenAI）でスコアリングし ai_scores に格納（ai.news_nlp）
  - マクロニュース + ETF ma200 を用いた市場レジーム判定（ai.regime_detector）
  - OpenAI API 利用は API キーが必須（環境変数 OPENAI_API_KEY）

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

1. リポジトリをクローン・移動
   - (環境に応じて) Python 仮想環境を作成し有効化

2. 依存パッケージのインストール（例）
   - 必要最低限（例）:
     - duckdb
     - psutil
     - openai （AI 機能を使う場合）
     - PyYAML （config ファイル検証を行う場合に推奨）
   - pip 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - （requirements.txt がある場合はそれを利用してください）

3. .env の用意
   - 対話式ウィザードで生成:
     ```
     python -m kabusys.config_setup
     ```
   - あるいはプロジェクトルートに `.env` を作成し、必要な環境変数を設定します（下記参照）。

4. 設定検証（起動前に必ず実行推奨）
   ```
   python -m kabusys.validate_config
   ```
   - --strict をつけると警告も失敗（exit 1）扱いになります。

5. データディレクトリ等の準備
   - デフォルトでは次のファイル/ディレクトリを使用します:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - PID / flag: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログ: logs/<app>.log（logs ディレクトリが自動作成されます）
   - 必要に応じて .env でパスを上書きしてください。

---

## 重要な環境変数（主なもの）

必須（core 起動に必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

実行環境・ログ・DB 関連
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードでの約定挙動（instant/partial/never/reject、デフォルト instant）
- PID_FILE_PATH — execution の pid ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）

OpenAI 関連（AI 機能を使う場合）
- OPENAI_API_KEY — OpenAI API キー（必須）

備考: .env を配置すると自動ロードされます（プロジェクトのルートが .git か pyproject.toml から検出される場合）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（よく使うコマンド）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（デーモン管理/プロセスマネージャを使うことを推奨）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading 用 DB を使用します。
  - 起動後、PID ファイル（デフォルト data/execution.pid）が作成されます。
  - 停止は `data/stop_requested.flag` を作成するか、ExecutionEngine によって kill.flag が書かれると停止シグナルになります。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で変更可能（例: MONITOR_POLL_INTERVAL=30）。
  - 停止フラグ（data/stop_requested.flag）が存在するとループを抜けます。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは引数 --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- AI モジュール呼び出し（プログラム上）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは OPENAI_API_KEY 環境変数または引数で渡す必要があります。

- 停止 / Kill Switch
  - Monitoring/RiskMonitor 等が条件を満たすと data/kill.flag に理由を書き込む（既存時は上書きしない）。
  - ExecutionEngine は起動時に kill.flag があれば起動しません（明示的な解除が必要）。

---

## ディレクトリ構成（主要ファイル）

パッケージルート: src/kabusys

主要モジュールと役割（抜粋）:

- __init__.py
  - パッケージメタ情報

- config.py
  - 環境変数読み込み・Settings クラス（各種設定プロパティ）

- config_setup.py
  - 対話式 .env 作成ウィザード

- validate_config.py
  - 起動前設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- monitoring/
  - monitoring_db.py — SQLite のスキーマ初期化・簡易永続化 API
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度チェック
  - risk_monitor.py — ドローダウン・ポジション上限チェック
  - trade_monitor.py — 発注ログ監視（存在）
  - kill_switch.py — kill.flag 管理
  - monitoring_engine.py — 各 Monitor を束ねる

- execution/
  - （ExecutionEngine、BrokerFactory、OrderManager 等の実装ファイル群）

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・資金配分
  - risk_adjustment.py — セクター制限・レジーム乗数

- research/
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン・IC・統計

- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — マクロ+ETF によるレジーム判定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート

- utils/
  - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ローテート）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/
  - （実行時に生成される SQLite / DuckDB ファイル、flag や pid など）

（注）上記は主なファイルの抜粋です。詳細はソースツリーを参照してください。

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では kill.flag / KILL_FLAG_CLEAR_ON_START 等の設定を慎重に扱ってください。KILL_FLAG_CLEAR_ON_START=1 は本番で危険です。
- .env は絶対に Git にコミットしないでください。
- ログディレクトリや DB ファイルのパーミッションに注意してください。ログ出力に失敗した場合はコンソールに警告が出ます。
- AI 機能を使う場合は API コスト・レート制限を考慮してください（モジュール内でリトライやバッチ処理を実装しています）。
- Execution / Monitoring はプロセスマネージャ（systemd / supervisor / Docker / Kubernetes 等）で管理することを推奨します。

---

## ライセンス / バージョン

- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

---

READMEはここまでです。より詳しい使い方や内部設計（PortfolioConstruction.md、StrategyModel.md の参照がコード内に記載されています）はプロジェクトのドキュメントディレクトリや設計文書を参照してください。必要であれば README に追加すべき項目（例: サービス unit ファイル例、Docker 化手順、CI 設定等）を教えてください。