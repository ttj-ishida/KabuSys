# KabuSys

日本株向け自動売買システムのリポジトリ（抜粋）。この README は、提供されたコードベースに基づきプロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。主な役割は以下の通りです。

- ExecutionEngine：発注ロジック（本番 / ペーパートレード切替）
- Monitoring：システム稼働状況・データ鮮度・リスク監視とアラート、Kill Switch
- Research：DuckDB を使ったファクター計算・特徴量解析
- AI：ニュースを LLM（OpenAI）でスコアリングし、市場レジーム判定へ利用
- Portfolio：銘柄選定・重み計算・ポジションサイズ計算
- ユーティリティ：ログ設定・プロセス優先度設定・設定読み込みウィザードなど
- ツール：ペーパートレード検証レポート生成等のユーティリティスクリプト

設計方針の例：
- DuckDB / SQLite をデータ層として使用（分析用 DB と監視用 DB を分離）
- 環境変数 / .env ベースの設定管理
- 本番とペーパートレードを明確に分離（ペーパートレードは別 SQLite）
- LLM 呼び出しは明示的に API キーを要求し、失敗時は安全側にフォールバックする

---

## 主な機能一覧

- 環境設定ウィザード（.env の生成 / 更新）
- 設定検証 CLI（.env および config/*.yaml の存在・妥当性チェック）
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて MockBrokerClient（paper_trading）と本番クライアントを切り替え
  - paper_trading の場合は専用 DB（デフォルト: data/paper_trading.db）を使用
  - 停止フラグ / PID 管理を備える
- Monitoring 起動スクリプト（run_monitoring.py）
  - システムリソース、Execution 停止検出、データ鮮度の定期チェック
  - MONITOR_POLL_INTERVAL によりポーリング間隔を調整可能
- MonitoringEngine：各モニタ（System / Trade / Risk）を束ねる
- KillSwitch：リスク条件に応じて data/kill.flag を書き込み Execution を停止させる
- RiskMonitor：ドローダウンやポジション上限の監視とログ記録
- MonitoringDB：SQLite ベースの永続化レイヤ（テーブル作成・マイグレーション含む）
- Research：momentum/volatility/value 等のファクター計算（DuckDB）
- AI：
  - news_nlp: ニュース記事を LLM に送り銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: ma200 + マクロニュースにより市場レジームを判定し DB に保存
- Portfolio：候補選定・重み・ポジションサイズ計算の純粋関数群
- ツール：Paper Trading 検証レポート生成（paper_verification_report）

---

## セットアップ手順

前提：Python 3.9+（プロジェクトの依存に合わせて調整してください）

1. リポジトリをクローン／配置し、仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate.bat  # Windows
   ```

2. 必須パッケージをインストール（代表的なパッケージ）
   ```bash
   pip install duckdb psutil openai PyYAML
   ```
   補足：
   - openai: news_nlp / regime_detector で使用
   - PyYAML: validate_config が config/*.yaml を parse する場合に使用
   - psutil: プロセス優先度 / CPU 情報取得などで使用

   （リポジトリに requirements.txt があればそれを使ってください）

3. 初期設定ファイル (.env) を作成
   対話式ウィザードを実行して `.env` を生成できます。
   ```bash
   python -m kabusys.config_setup
   ```

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告も fail 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. ディレクトリ準備
   - `data/` と `logs/` は自動作成されることが多いですが、必要に応じて手動作成して権限を確認してください。
   - 実行時にログディレクトリ作成に失敗した場合はコンソールロギングのみになります。

---

## 使い方

※ 以降はパッケージをインポート可能な場所（プロジェクトルート）から実行することを想定しています。

基本的にモジュールはパッケージとして起動できます。

- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV で切替）
  ```bash
  # ペーパートレードで起動（環境変数を設定）
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution

  # 本番環境で起動
  export KABUSYS_ENV=live
  python -m kabusys.run_execution
  ```

  補足:
  - paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH により変更可）へ記録されます。
  - 実行中の停止は `data/stop_requested.flag` を作成することで検出して優雅に停止します（run_execution/run_monitoring 共通）。

- Monitoring を起動
  ```bash
  # ポーリング
  python -m kabusys.run_monitoring

  # MONITOR_POLL_INTERVAL（秒）を環境変数でオーバーライド可能
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポートを生成
  ```bash
  # デフォルト DB を使用
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB パス指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュールを使う（OpenAI API）
  - 環境変数に OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡してください。
  - 例: news_nlp.score_news / regime_detector.score_regime を呼び出す際に API キーが必要。

- ログ
  - ログはデフォルトで `logs/<app_name>.log` に日次ローテーションで保存されます（30日分保持）。
  - コンソール出力は標準出力（stdout）に出ます。

- 停止 / Kill スイッチ
  - ExecutionEngine を外部から強制停止させるシグナルは `data/kill.flag` を作成することで通知できます（KillSwitch が評価してファイルが書かれることもある）。
  - run_* スクリプトは `data/stop_requested.flag` の存在を監視して優雅に終了します。

---

## 代表的な環境変数（例・デフォルト）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）

- データベース
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）

- AI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）

- その他
  - MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"0" または "1"、本番では "0" 推奨）

例（.env の一部）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下にある主要モジュールの構成（提供コードから抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義・永続化 API
    - monitoring_engine.py   — 複数 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — （trade_monitor 実装あり）発注監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag の管理
    - alert_manager.py       — （アラート送信処理）
  - execution/
    - execution_engine.py    — ExecutionEngine（起動処理は run_execution で）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
    - __init__.py

（実際のリポジトリには上記以外のファイル / モジュールがある可能性があります）

---

## 注意点 / 運用上のヒント

- 本番運用時は KABUSYS_ENV=live を設定し、.env の値（特に API キー / トークン）を厳重に管理してください。
- validate_config を使って起動前に設定とファイルパスをチェックすることを推奨します。
- logs ディレクトリのパーミッション（書き込み権限）を起動ユーザーが持っているか確認してください。
- OpenAI を利用する機能は API 費用が発生します。rate limit や失敗時のフォールバックが実装されていますが、実運用ではコスト管理が必要です。
- run_execution/run_monitoring は stop flag（data/stop_requested.flag）を監視します。外部で停止させる場合はこのファイルを作成してください。KillSwitch はリスク条件に応じて data/kill.flag を書き込みます。

---

必要であれば、README にサンプル .env.example、起動スクリプトの systemd / supervisor 用ユニット例、より詳細な API 使用例や DB スキーマのドキュメントを追加できます。どの追加情報が必要か教えてください。