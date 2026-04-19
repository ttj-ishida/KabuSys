# KabuSys

日本株自動売買システムのサンプル実装 (KabuSys)

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買・運用支援を目的としたモジュール群です。  
主な機能は以下の通りです。

- 注文実行エンジン (ExecutionEngine) — ブローカーとのやりとり、注文管理、リスク管理
- 監視サブシステム (Monitoring) — システム状態・注文状態・リスク監視、Kill Switch
- ポートフォリオ構築ロジック — 候補選定、重み付け、株数計算、セクター制約
- 研究用モジュール — ファクター計算、特徴量解析、IC 計測
- AI 連携機能 — ニュースの NLP スコアリング、レジーム判定（OpenAI を利用）
- ツール群 — ペーパートレード検証レポート等

設計方針として、本番 DB とペーパートレード DB は明確に分離され、DuckDB を分析用途に使用します。設定は .env で管理し、設定ウィザード・検証ツールを備えています。

---

## 機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録（本番 DB と完全分離）。
  - 停止は data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）で制御。
- run_monitoring.py
  - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を使用する（環境に依らず）。
- monitoring package
  - SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, MonitoringDB など。
- portfolio package
  - 銘柄選定・重み付け・株数決定・セクター制約・レジーム乗数。
- research package
  - DuckDB を使ったファクター計算 (momentum/value/volatility)、forward return、IC、統計サマリ等。
- ai package
  - news_nlp: OpenAI を用いたニュースセンチメント付与 → ai_scores へ保存
  - regime_detector: ETF(1321) の MA 指標とマクロニュースで市場レジームを判定
- tools
  - paper_verification_report: ペーパートレード DB から PASS/FAIL 判定付きレポートを出力
- 設定関連
  - config_setup.py: .env を対話式に作成/更新するウィザード
  - validate_config.py: .env と config/*.yaml を起動前に検証する CLI

---

## 必要条件 / 前提

- Python 3.10 以上（typing の表記を使用）
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の厳密検証に必要、なくても動作は一部制限）
- その他、実稼働では J-Quants / kabuステーション 等の API キーや資格情報が必要

例（仮想環境作成・パッケージインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## 環境変数（主なもの）

*.env ファイルで管理します。`python -m kabusys.config_setup` で対話的に作成できます。主なキー:

必須
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / デフォルト有り
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート通知用（任意）
- OPENAI_API_KEY — AI 機能を使う場合に必須

監視関連
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアする（0/1、デフォルト 0）

ログ
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs）

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化・依存モジュールインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai PyYAML
   ```

3. .env の作成（対話式）
   ```bash
   python -m kabusys.config_setup
   ```
   作成後、`python -m kabusys.validate_config` で検証できます。

4. DB ディレクトリ等の作成（必要に応じて）
   ```bash
   mkdir -p data logs
   ```

5. OpenAI を使う機能を利用する場合は OPENAI_API_KEY を .env に設定するか環境変数で指定してください。

---

## 使い方（主要コマンド）

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も FAIL として扱う
  ```

- ExecutionEngine 起動
  - 本番
    ```bash
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - ペーパートレード（MockBrokerClient を使用し、data/paper_trading.db に記録）
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```

  停止方法:
  - 外部から実行を止める（Ctrl+C）
  - 停止フラグファイルを作成: data/stop_requested.flag（存在を検知してループを終了）
  - KillSwitch により data/kill.flag が書き込まれた場合は ExecutionEngine 側で検知して停止できます。

- Monitoring 起動
  ```bash
  # ポーリング間隔を変更する場合
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連（ニューススコア / レジーム判定）
  - OPENAI_API_KEY を設定してから呼び出します（基本は内部呼び出しで使用）。
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をスクリプトやジョブから呼ぶ。

注意:
- monitoring は設定にかかわらず sqlite_path（デフォルト data/monitoring.db）を使用します。
- run_execution は環境が paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。

---

## ディレクトリ構成（主要ファイル・簡易説明）

src/kabusys/
- __init__.py — パッケージエントリ（バージョン等）
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

パッケージ群:
- execution/ — (placeholder) ブローカー・エンジン・注文管理（実装の起点）
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py などが起動時に利用される設計（今回のコードベースでは参照のみ）
- monitoring/
  - monitoring_db.py — SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム状態 / データ鮮度監視
  - trade_monitor.py — 注文状態監視（参照されるが今回抜粋に一部）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - alert_manager.py — アラート送信（LINE 等を想定）
  - monitoring_engine.py — 各モニタをまとめて実行
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・キャップ・丸め処理
  - risk_adjustment.py — セクター制約・レジーム乗数
- research/
  - factor_research.py — momentum/value/volatility ファクター計算（DuckDB 利用）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリング（ai_scores へ書き込み）
  - regime_detector.py — マクロ + MA200 を用いた市場レジーム判定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py — ログ設定ユーティリティ（コンソール + 日次ローテーション）
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

その他:
- data/ — 実行時に作成される DB、pid、flag ファイルを置く場所（デフォルトパス）
  - data/monitoring.db (SQLite)
  - data/paper_trading.db (ペーパートレード)
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag
- logs/ — ログファイル置き場（デフォルト: logs/<appname>.log、日次ローテーション）

---

## 運用上の注意点

- 本番環境で KABUSYS_ENV=live を設定する際は、LINE 通知や Kill Switch 設定等を十分に確認してください（validate_config は live 環境で警告を出します）。
- .env は絶対に Git にコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。
- AI（OpenAI）関連は API 呼び出しに失敗した場合フェイルセーフを備えていますが、キーの管理やコストに注意してください。
- process_priority.set_process_priority は権限により失敗する場合があります（警告ログによりスキップ）。
- DuckDB / SQLite のパスはデフォルトで data ディレクトリに書き込みます。必要に応じて権限・バックアップを検討してください。

---

## 開発 / テストのヒント

- 設定の自動ロードは config.py 内で行われます。テスト時に自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- run_monitoring/run_execution は stop フラグ（data/stop_requested.flag）を見て終了します。CI 等で短時間実行したい場合は該当ファイルの作成/削除で制御できます。
- DuckDB を使う研究機能は、prices_daily / raw_financials / raw_news 等のテーブルが必要です。サンプルデータを用意してテストしてください。

---

必要があれば、README に起動シナリオ例（systemd ユニット、docker-compose、cronジョブ等）やより詳細な環境変数一覧、API 仕様の追記も作成できます。どの情報を追加したいか教えてください。