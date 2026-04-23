# KabuSys

日本株自動売買システムのモジュール群（ライブラリ＋起動スクリプト群）。

この README はリポジトリ内の主な機能・セットアップ手順・使い方・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアロジック、監視、リサーチ、ペーパートレード検証、AIベースのニューススコアリング等を含むモジュール群です。主な役割は以下です。

- 注文実行エンジン（ExecutionEngine）とそれを止める Kill Switch / Risk Monitor
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート管理
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限）
- リサーチ（ファクター計算、将来リターン・IC 計算）
- AI モジュール（OpenAI を用いたニュースセンチメント、レジーム判定）
- ペーパートレードの検証レポート生成ツール

設計方針として、DB（DuckDB / SQLite）を用いたデータ参照、.env による設定管理、フェイルセーフ（API失敗時はフォールバック）等が組み込まれています。

---

## 主な機能一覧

- 実行系
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV によりペーパートレード/本番を切り替え）
    - paper_trading 環境では MockBroker を使用し、data/paper_trading.db に記録して本番 DB と分離
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch による総合監視
  - 監視ログは SQLite（デフォルト: data/monitoring.db）へ永続化
- 構成サポート
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の静的検証（--strict オプションあり）
- リサーチ / ポートフォリオ
  - research: ファクター計算（momentum/value/volatility）、特徴量探索、IC 計算
  - portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター上限・レジーム補正
- AI（OpenAI）
  - ai.news_nlp: raw_news を集約して OpenAI に送信、銘柄ごとの ai_score を ai_scores テーブルへ書込
  - ai.regime_detector: マクロ記事 + ETF MA200 による market_regime 判定、DB へ永続化
- ツール
  - tools/paper_verification_report.py: ペーパートレードの稼働率・成功率・レイテンシ等の検証レポート生成

---

## 依存関係（主なライブラリ）

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を有効にする場合）
- （必要に応じて）その他のランタイム依存

例（venv 作成後）:
```
pip install duckdb psutil openai PyYAML
```

requirements.txt があればそちらを利用してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb psutil openai PyYAML
   ```
3. .env を作成（推奨: 対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 実行環境: KABUSYS_ENV (development / paper_trading / live)
   - OpenAI を使用する場合は OPENAI_API_KEY を環境変数で設定してください。
4. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も含めて厳密にチェックする場合:
   python -m kabusys.validate_config --strict
   ```
5. 必要ディレクトリの作成（通常は起動時に自動作成されますが手動で作ることも可）
   - data/ （SQLite や PID / フラグファイル保存用）
   - logs/ （ログファイル）
6. （AI 機能を使う場合）OPENAI_API_KEY を設定
   ```
   export OPENAI_API_KEY="sk-..."
   ```

---

## 使い方（起動方法）

※パッケージが `src` 配下のモジュールとして実行できる前提（path を通すか package としてインストール）

- 実行エンジン起動（ExecutionEngine）
  - 本番／ペーパートレードは KABUSYS_ENV に従う
  ```
  # 例: systemd / Supervisor 等で常駐起動する想定
  python -m kabusys.run_execution
  ```
  - ペーパートレード時は settings.paper_sqlite_path（デフォルト: data/paper_trading.db）を使用します。
  - 実行中に data/stop_requested.flag を作成すると処理は安全に停止します。
  - 実行中は PID ファイル（data/execution.pid デフォルト）を使用します。

- 監視プロセス起動
  ```
  # デフォルト 60 秒間隔。MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は常に本番 sqlite_path（data/monitoring.db デフォルト）を使用します（KABUSYS_ENV に依らず）。
  - 監視中に data/stop_requested.flag を作成するとループを終了します。

- 設定ウィザード・検証
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config [--strict]
  ```

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を直接指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI スコアリング / レジーム判定（ライブラリ API として利用）
  - ai.score_news / ai.regime_detector.score_regime は DuckDB 接続と target_date, api_key を受け取ります（スクリプト化はされていませんが CLI から呼ぶことも可能です）。

---

## 環境変数（主要なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）、デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 本番起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- KILL_FLAG_PATH: data/kill.flag のパス（デフォルト: data/kill.flag）

---

## 停止・キルフラグ挙動

- data/stop_requested.flag: run_execution / run_monitoring が存在を検知すると安全にシャットダウンします（外部から停止する用途）。
- data/kill.flag: KillSwitch（監視ロジック）によって書き込まれると ExecutionEngine に対して停止シグナルを送ります。KILL_FLAG_CLEAR_ON_START=1 の場合、ExecutionEngine 起動時に自動クリアされます（本番では無効化推奨）。

---

## ロギング

- kabusys.utils.logging_setup.setup_logging を通じてルートロガーを設定します。
- 出力: stdout（常時） + 日次ローテートファイル（logs/<app_name>.log、30日保持）
- LOG_LEVEL / LOG_DIR で調整可能。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

---

## ディレクトリ構成（主なファイル）

以下はソースツリー（src/kabusys 以下）の主要ファイル・モジュールです。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード）
  - config_setup.py          — .env 対話式作成ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — monitoring 用 SQLite の作成・I/O
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 操作ユーティリティ
    - ... (TradeMonitor, AlertManager 等 他ファイル想定)
  - execution/
    - execution_engine.py    — ExecutionEngine（エンジン本体）
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
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py
  - data/                    — 実行時に使用されるデータディレクトリ（DB/flags/PID 等）

（実際の細かいファイルはリポジトリを参照してください）

---

## 注意点 / 運用上のヒント

- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を強く推奨します。自動クリアは危険です。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup.py にも注意書きあり）。
- OpenAI を利用する部分は API キーが必要で、API の呼び出しはレート制限・エラーによるリトライロジックを備えていますが、費用とレートに注意してください。
- DuckDB / SQLite のパスは設定可能です。production ではバックアップやファイル配置に注意してください。
- プロセスの優先度設定はプラットフォーム依存で失敗する場合があります（権限不足など）。その際は警告がログに出ますが処理は継続します。

---

もし README に加えたい具体的な例（systemd ユニットや docker-compose 定義、より詳細な設定例ファイル、CI 用のテスト手順など）があれば教えてください。追加でサンプルを作成します。