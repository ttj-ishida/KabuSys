# KabuSys

日本株自動売買システムのコアライブラリ／起動スクリプト群です。  
このリポジトリはトレード実行エンジン、監視コンポーネント、ポートフォリオ構築・リスク制御ロジック、研究用ファクター計算、ニュースNLP（LLM）連携などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。下記の主要な関心事を扱います。

- ExecutionEngine（発注ロジック）と Broker クライアント（実口座 / ペーパートレード切替）
- Monitoring（システム状態・注文状態・リスクの監視）と Kill Switch
- Portfolio Construction（銘柄選定、重み付け、ポジションサイジング）
- Research（DuckDB を使ったファクター計算・特徴量解析）
- AI連携（OpenAI を用いたニュースセンチメント評価、レジーム判定）
- ユーティリティ（設定ウィザード、設定検証、ロギング・プロセス優先度設定）

設計方針として、運用用（live）と検証用（paper_trading）を明確に分離し、データベース（SQLite / DuckDB）やログを扱いやすくしています。

---

## 機能一覧

主要機能の抜粋:

- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV に応じて paper_trading モードで MockBroker を使用）
  - run_monitoring: SystemMonitor のポーリングループを起動（ポーリング間隔は MONITOR_POLL_INTERVAL で調整）
- 設定管理
  - config_setup: 対話式ウィザードで .env を生成・更新
  - validate_config: .env や config/*.yaml の簡易検証 CLI
- 監視
  - system_monitor: CPU/メモリ/ディスク、データ鮮度、実行プロセスの有無チェック
  - risk_monitor: ドローダウン／ポジション上限監視、dashboard 更新、risk_logs への記録
  - kill_switch: 条件に応じた data/kill.flag 書き込み（ExecutionEngine 停止シグナル）
  - monitoring_engine: 各モニタを束ねアラート評価・Kill Switch 発動
  - monitoring_db: SQLite を用いた永続化レイヤ（system_status / trade_logs / positions / risk_logs / dashboard）
- ポートフォリオ構築
  - 銘柄選定、等重／スコア重み、セクター制限、ポジションサイズ計算（単元丸め・利用資金制限・aggregate cap）
- 研究（research）
  - ファクター計算（モメンタム／バリュー／ボラティリティ等）
  - 将来リターン計算、IC（スピアマン）や統計サマリ
- AI（OpenAI）
  - news_nlp: ニュース記事を LLM でセンチメント評価し ai_scores に書き込み
  - regime_detector: マクロ記事 + ETF MA200 を合成して日次レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を集計し検証レポートを出力

---

## セットアップ手順

1. リポジトリをクローン（例: プロジェクトルートが生成されることを前提）
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境作成と有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリをインストール
   必須パッケージ（代表例）:
   - duckdb
   - psutil
   - openai
   - PyYAML（validate_config の YAML 検証を使う場合）
   ```bash
   pip install duckdb psutil openai pyyaml
   ```
   （実際の requirements.txt がある場合はそれを使ってください）

4. ディレクトリ準備
   デフォルトで使用するディレクトリ:
   - data/           （SQLite や PID/flag ファイル用）
   - logs/           （ログ出力）
   自動で作成されますが、手動で作る場合:
   ```bash
   mkdir -p data logs
   ```

5. .env を作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークンや kabuステーション API パスワードなど必須項目を順に入力して .env を作成します。

6. 設定検証（任意、起動前に推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗として扱いたい場合:
   python -m kabusys.validate_config --strict
   ```

注意:
- 自動で .env を読み込む仕組みがあり（プロジェクトルートの .env / .env.local）、必要があれば環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- OpenAI を使う機能を利用する場合は OPENAI_API_KEY を .env に設定してください。

---

## 主要な環境変数（代表）

- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、run_execution は MockBrokerClient を使用し、ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb） — DuckDB ファイルパス
- SQLITE_PATH（デフォルト: data/monitoring.db） — 監視用 SQLite（Monitoring は環境にかかわらず本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db） — ペーパートレード専用 SQLite
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒（デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 実行時に kill.flag を自動でクリアするか（"1" で有効。運用では "0" 推奨）

---

## 使い方（起動例）

- ExecutionEngine を起動（通常モード / paper_trading は KABUSYS_ENV を指定）
  ```bash
  # 例: ペーパートレードで起動
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Monitoring を起動（デフォルト 60 秒間隔）
  ```bash
  # MONITOR_POLL_INTERVAL で秒を上書き可能
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
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を直接指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

停止方法 / フラグ:
- run_execution / run_monitoring はプロジェクト内の data/stop_requested.flag を検出すると順次停止します（stop_requested.flag を作成することで停止をリクエストできます）。
- KillSwitch は条件を満たすと data/kill.flag を書き込みます（ExecutionEngine 停止のための外部シグナル）。KILL_FLAG_CLEAR_ON_START を使うと（設定次第で）起動時に自動クリアできますが、本番環境では注意して使用してください。

ログ:
- setup_logging により stdout と logs/<app_name>.log（日次ローテーション、30 日保持）に出力されます。

プログラム的な呼び出し:
- AI / 研究 / ポートフォリオの関数群はモジュールとして利用できます。例:
  - from kabusys.ai import score_news
  - from kabusys.research import calc_momentum, calc_value, calc_volatility
  - from kabusys.portfolio import select_candidates, calc_position_sizes

---

## ディレクトリ構成（抜粋）

（ソースは src/kabusys 以下に配置されています）

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 設定検証 CLI
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
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
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - (その他: execution/*.py, data/*.py など実行ロジックに関するモジュールが存在する想定)

- data/      — データベースファイルやフラグ、PID ファイル（実行時に生成）
- logs/      — ログファイル出力先

---

## 運用上の注意

- 監視（Monitoring）は KABUSYS_ENV にかかわらず常に本番の sqlite_path（SQLITE_PATH）を使用します。ペーパートレードの Execution は PAPER_TRADING_SQLITE_PATH を使用して本番 DB と分離しています。
- OpenAI 等外部 API キーは秘匿情報のため .env ファイルを Git にコミットしないでください。
- Kill Switch / stop フラグの取り扱いは慎重に（特に本番環境: KABUSYS_ENV=live 時）。
- ログディレクトリの作成に失敗した場合はコンソール出力のみになります。パーミッション等を事前に確認してください。
- psutil によるプロセス優先度設定や CPU affinity は OS によって動作が異なり、権限不足で警告が出ますが続行されます。

---

この README はコードベースの主要機能と利用方法の要点をまとめたものです。各モジュールの詳細実装やさらに細かい設定はソースコードの docstring と関数コメントを参照してください。必要であれば、導入手順の自動化（Docker / systemd ユニット / supervisor）やテスト手順の追記も行えます。