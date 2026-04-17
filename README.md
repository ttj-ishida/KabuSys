# KabuSys

日本株自動売買システムの部分実装（ライブラリ／ツール群）。  
この README はリポジトリ内の主要スクリプト・モジュールに基づいて、ローカルでのセットアップと基本的な使い方をまとめたものです。

注意: このリポジトリは実運用を想定した設計を含みます。実際に「live」環境で使用する前に設定やセキュリティ、バックテスト等を十分に確認してください。

---

## 概要

KabuSys は以下の機能を含むモジュール群を提供します（抜粋）:

- 実行エンジン（ExecutionEngine）および監視（Monitoring）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リスク制御（ドローダウン監視、ポジション上限）
- 監視ログの永続化（SQLite ベース）
- 研究用モジュール（ファクター計算、特徴量解析）
- AI を使ったニュース NLP（OpenAI API 経由のセンチメント評価）
- ペーパートレード用レポート生成ツール

主要なランタイム・スクリプト:
- python -m kabusys.run_execution : ExecutionEngine を起動（KABUSYS_ENV に応じて paper_trading では MockBroker を使用）
- python -m kabusys.run_monitoring : SystemMonitor をポーリングで起動
- python -m kabusys.config_setup : .env を対話式に作成・更新
- python -m kabusys.validate_config : 設定の事前検証（.env と config/*.yaml）
- python -m kabusys.tools.paper_verification_report : Paper Trading 検証レポート出力

---

## 機能一覧

- 設定管理
  - 自動でプロジェクトルートの .env / .env.local を読み込む（必要に応じて無効化可能）
  - Settings クラスで環境変数を安全に取得・検証
- Execution / Broker
  - 本番（live）・ペーパー（paper_trading）環境の分離（ペーパー時は専用 SQLite に記録）
- 監視
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID、データ鮮度をチェックし SQLite に記録
  - TradeMonitor: 滞留注文・約定異常価格を検知しリスクログに記録
  - RiskMonitor: ドローダウン・ポジション上限を監視し kill.flag を書く等のアクションを取れる
  - MonitoringEngine: 各 Monitor を束ねてポーリング、アラート送信や Kill Switch のトリガーに対応
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、リスクベースのポジションサイズ計算、セクターキャップ適用、レジーム乗数
- 研究用
  - ファクター（モメンタム、バリュー、ボラティリティ等）計算、Forward returns、IC 計算、統計サマリ
- AI（OpenAI）
  - ニュース記事を集約して LLM に渡し銘柄ごとのセンチメント（ai_score）を生成
  - マクロ記事を LLM でスコア化し市場レジーム（bull/neutral/bear）を判定
- ツール
  - Paper Trading 検証レポート（uptime、fill rate、latency 等の指標）生成

---

## 前提・依存関係

推奨 Python バージョン: 3.10+（コード内に union 型等を使用）  
主な依存パッケージ（例）:
- duckdb
- psutil
- openai
- PyYAML（validate_config の YAML 検証に必要）
その他、プロジェクト特有のライブラリがある場合は requirements.txt を参照してください（本コードサンプルには含まれていません）。

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成して依存パッケージをインストール（上記参照）
3. 環境変数の準備
   - 対話式ウィザードで .env を作成:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env の既存値を読み込み、必要なキーの入力を促します。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - オプション／運用変数
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能使用時必須）
     - LOG_LEVEL（DEBUG/INFO/...）
     - KILL_FLAG_CLEAR_ON_START（起動時 kill.flag を自動クリアするか。デフォルト 0）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）
4. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリ作成（必要なら）
   ```
   mkdir -p data
   ```

.env の自動読み込みについて:
- 既定ではプロジェクトルート（.git または pyproject.toml がある場所）を探索して .env/.env.local を自動読み込みします。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方

基本的な起動例と説明を示します。

- ExecutionEngine の起動
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、デフォルトで data/paper_trading.db に記録します。本番設定（live）では本物のブローカークライアントが使われます。
    - 実行中は pid ファイル（data/execution.pid）を書きます。プロセスの状態は SystemMonitor が参照します。
    - 停止は run_execution が監視するフラグファイル data/stop_requested.flag を作成するか、ExecutionEngine 側に用意された停止方法で行います。

- Monitoring の起動
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - 環境変数:
    - MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒）。デフォルト 60。1 以上の整数で指定してください。
  - 特記事項:
    - Monitoring は常に本番用の sqlite_path を使用して監視ログを記録します（KABUSYS_ENV に依存せず）。
    - 停止はプロジェクトの data/stop_requested.flag による検出でループを終了します。

- Paper Trading 検証レポート
  - 実行例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB 指定:
    - --db オプション、または環境変数 PAPER_TRADING_SQLITE_PATH で SQLite DB のパスを指定できます。デフォルトは data/paper_trading.db。
  - 出力: 標準出力に期間の指標（稼働率、注文成功率、レイテンシ等）と PASS/FAIL 判定を出力します。

- AI 機能（ニュース NLP / レジーム判定）
  - 必須: OPENAI_API_KEY を環境変数に設定
  - ニューススコアリング:
    - kabusys.ai.news_nlp.score_news を呼ぶと ai_scores テーブルへ書き込みます（DuckDB 接続が必要）。
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime を呼ぶと market_regime テーブルへ書き込みます。
  - 注意:
    - OpenAI API 呼び出しはリトライやフェイルセーフを備えていますが、API キーの料金や利用制限に注意してください。

制御フラグ:
- data/kill.flag — KillSwitch による ExecutionEngine 停止シグナル（KillSwitch が書き込む）
- data/stop_requested.flag — run_monitoring / run_execution がチェックする停止フラグ（存在するとループ終了）
- KILL_FLAG_CLEAR_ON_START 環境変数が 1 のとき、Execution 起動時に kill.flag を自動クリアする（本番では 0 推奨）

ログレベル:
- 環境変数 LOG_LEVEL で制御（INFO デフォルト）

---

## 主要ファイル / ディレクトリ構成

リポジトリの主要モジュール（src/kabusys 以下）の構成と簡単な説明:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み取り、自動 .env ロード、Settings クラス
  - config_setup.py
    - .env を対話式に生成・更新するウィザード
  - validate_config.py
    - 起動前の設定検証 CLI（必須変数チェック・YAML ファイル検証など）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper/live の差分対応、pid/stop flag 管理）
  - run_monitoring.py
    - SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL 対応）
  - utils/
    - __init__.py
    - process_priority.py — プロセス優先度 / CPU affinity を OS 間で吸収して設定
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, order_record.py, ...（発注ロジック、ブローカー抽象化）
  - monitoring/
    - monitoring_db.py — SQLite のテーブル初期化 / 永続化 API
    - system_monitor.py — CPU/メモリ/ディスク、データ鮮度、PID チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の書き込み / クリア
    - monitoring_engine.py — 複数モニタのポーリング進行
    - alert_manager.py — （アラート送信の抽象・実装）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — シェア数計算・制限・丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - data/
    - pipeline.py, stats.py, （DuckDB / データパイプライン関連）
  - ai/
    - news_nlp.py — ニュースセンチメントの LLM スコアリング（OpenAI）
    - regime_detector.py — マクロ + ETF MA200 を合成したレジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py — ペーパートレード向け検証レポート生成

（上記は抜粋です。実コードベースにはさらに細かいモジュールが含まれます）

---

## .env の最小例

.env は Git に含めないでください（機密情報を含むため）。ウィザードで生成するか、以下例を参考に作成してください。

```
# 基本
KABUSYS_ENV=development
LOG_LEVEL=INFO

# API
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
OPENAI_API_KEY=sk-...

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# Kill switch
KILL_FLAG_CLEAR_ON_START=0

# Paper trading settings
PAPER_FILL_MODE=instant
```

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）などアラート経路の確認を行ってください。validate_config は live 時に追加の警告を出します。
- kill.flag が自動でクリアされる設定（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。通常は 0 を推奨します。
- OpenAI API キーは料金・レート制限が発生するため、テスト時は慎重に扱ってください。
- DuckDB / SQLite のパスは運用環境のバックアップや権限に注意してください。
- process_priority の設定はプラットフォーム依存で失敗する場合があります（権限不足など）。警告ログを確認してください。

---

もし特定のモジュール（例: ExecutionEngine の構成、OrderRepository の API、AI モジュールのテスト方法、DuckDB のスキーマなど）について詳しい README 追記をご希望でしたら、どのトピックを優先するか教えてください。