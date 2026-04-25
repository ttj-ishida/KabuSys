# KabuSys

日本株向け自動売買・研究基盤（パッケージ化されたモジュール群）の README。  
このリポジトリは取引エンジン、監視、ポートフォリオ構築、ファクター計算、AI ベースのニュース解析など複数のコンポーネントから構成されています。

注意: 実行には環境変数の設定が必要です。機密情報（API トークン等）は .env に保存し、Git へコミットしないでください。

## プロジェクト概要
KabuSys は日本株のアルゴリズム取引・調査を支援するライブラリ兼実行環境です。主要な機能は次の通りです。

- ExecutionEngine（発注処理、リスク管理、注文管理）
- Monitoring（システム・注文・リスク監視 + Kill Switch）
- Portfolio construction（銘柄選定、ウェイト計算、株数決定）
- Research（ファクター計算、将来リターン・IC 計算）
- AI モジュール（ニュースセンチメント、レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード・検証）

設計方針の一部:
- 本番とペーパートレードは分離（DB 等を切り替え）
- DuckDB を分析用に利用、SQLite を監視・注文ログ用に利用
- LLM 呼び出し（OpenAI）は失敗時に安全にフォールバック・リトライを行う

## 主な機能一覧（抜粋）
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- 実行エンジン起動スクリプト: src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading DB に記録
- 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - Monitoring は常に本番の sqlite_path を使用する点に注意
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- Portfolio モジュール:
  - 銘柄選定（select_candidates）
  - 重み計算（等金額・スコア重み）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）
- AI モジュール:
  - ニュースのセンチメントスコアリング（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 監視 DB レイヤ（SQLite）: テーブル作成・マイグレーション・読み書きユーティリティ
- ロギング設定ユーティリティ（統一的な Stream + 日次ローテートファイル）

## セットアップ手順（例）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール（requirements.txt が存在する場合）
   - pip install -r requirements.txt
   - 必要な依存（コードから推定）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例（最小）:
     - pip install duckdb psutil openai

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で作成する場合、最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 推奨（例）:
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=（AI 機能を使うなら設定）

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. データディレクトリの確認
   - data/ や logs/ は自動作成されますが、権限等を確認してください

## 使い方（主要コマンド例）
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を上書き（秒単位）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジンを起動（発注ループ）
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって動作が変わります:
    - development: 発注を行わない（開発用）
    - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録
    - live: 実ブローカーへ発注（注意して使用）

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラムAPI）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)

- ログ
  - デフォルト: logs/<app_name>.log（app_name は run 時に設定される: "execution" / "monitoring" 等）
  - 環境変数 LOG_DIR で保存先を指定可能

## 停止・Kill Switch の運用
- ExecutionEngine / Monitoring はフラグファイルを用いて制御します:
  - data/stop_requested.flag: run_monitoring/run_execution の外部停止用（両スクリプトで監視）
  - data/kill.flag: Kill Switch による ExecutionEngine 停止シグナル（KillSwitch により書き込まれる）
- KillSwitch の動作:
  - RiskMonitor などが閾値超過を検出すると KillSwitch が kill.flag を書き込み、ExecutionEngine に停止を要求します
  - Settings で KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアする挙動を許可できます（本番では 0 推奨）

## 主要環境変数一覧（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading モード）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行時に使用するパス（Settings からカスタマイズ可）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant/partial/never/reject）

## 注意点 / 実運用メモ
- Monitoring は sqlite_path を常に本番用のパスで初期化します（環境に依存せず本番監視 DB を使うため注意）
- Paper Trading は paper_sqlite_path を使用して本番 DB と分離されます
- OpenAI を利用する機能は API レート制限やネットワーク障害に備えたリトライロジックを備えていますが、API キーの管理とコストに注意してください
- ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソールのみになります
- process_priority の変更は psutil に依存し、権限や OS によって成功しない場合があります

## ディレクトリ構成（重要ファイルのみ抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数読み込み / Settings クラス
    - config_setup.py           — .env 対話ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py        — ログ設定ユーティリティ
      - process_priority.py     — 優先度・CPU affinity ユーティリティ
    - execution/                 — 実行・発注関連（Engine, BrokerFactory, OrderManager 等）
    - monitoring/
      - monitoring_db.py        — SQLite に対する永続化層
      - system_monitor.py       — システム状態監視
      - trade_monitor.py        — 注文監視（滞留注文・約定異常等）
      - risk_monitor.py         — ドローダウン・ポジション制限監視
      - kill_switch.py          — kill.flag の作成/管理
      - monitoring_engine.py    — 各 Monitor を束ねる
      - alert_manager.py        — アラート送信（LINE 等統合）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py      — Momentum/Value/Volatility 等の計算
      - feature_exploration.py  — 将来リターン、IC、統計サマリ
    - ai/
      - news_nlp.py             — ニュースセンチメント（OpenAI）処理
      - regime_detector.py      — レジーム判定（MA + マクロセンチメント）
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート
    - data/                      — 実行時に使用するフラグ/PID/DB 等（推奨 .gitignore に追加）

（リポジトリにある全ファイルは上記と一致しない場合があります。上位ディレクトリや追加のサブモジュールを参照してください）

## 追加情報 / トラブルシュート
- PyYAML が無いと config/*.yaml のパース検証はスキップされ、警告が出ます。設定ファイルの厳密検証を行いたい場合は `pip install pyyaml` を追加してください。
- DuckDB のバージョンによっては executemany の空リストがエラーになるため、ai/news_nlp.py などでは空リストチェックを行っています。
- run_execution/run_monitoring はプロセス優先度を「high」に設定しようとします（set_process_priority）。権限不足で失敗した場合はワーニングが出ますが実行自体は続行します。

---

この README はコード内の docstring と実装に基づいて作成しています。実運用する際は環境に合わせて .env と config/*.yaml を適切に準備し、まずは development モードで動作確認を行ってください。必要であれば README をプロジェクト固有の運用手順に合わせて追記してください。