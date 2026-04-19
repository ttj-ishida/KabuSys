# KabuSys

日本株向けの自動売買システム（ライブラリ兼起動スクリプト群）。  
本リポジトリはトレーディングロジック（シグナル・ポートフォリオ構築）・実行エンジン・監視・AI（ニュース解析／レジーム判定）・各種ユーティリティを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つモジュール群から構成されています。

- 戦略／リサーチ: DuckDB 上の時系列データを使ったファクター計算・特徴量解析
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ算出、セクター制約など
- 実行系: ブローカークライアント抽象化を通じた発注ロジック（ペーパー・本番の分離）
- 監視系: システム状態、注文状況、リスク（ドローダウン等）を継続監視しアラート/キルスイッチを発動
- AI 支援: ニュースのセンチメント評価、マクロセンチメントを用いたレジーム判定（OpenAI）
- 開発支援: .env ウィザード、設定検証、ペーパートレード検証レポート生成ツール 等

設計の特徴:
- データ解析は DuckDB、永続ログは SQLite（monitoring）に分離
- Paper Trading は本番 DB から分離（data/paper_trading.db がデフォルト）
- 環境変数は .env / .env.local を自動ロード（必要に応じて無効化可能）
- 外部 API 呼び出しはフェイルセーフ／リトライ処理を持つ設計

---

## 主な機能一覧

- ファクター計算（momentum, volatility, value 等） — kabusys.research
- ファクター評価・IC 計算・統計サマリー — kabusys.research.feature_exploration
- ポートフォリオ構築（候補選定、等金額/スコア重み、リスクベース投下） — kabusys.portfolio
- ポジションサイズ算出（単元丸め・aggregate cap 調整） — kabusys.portfolio.position_sizing
- セクター集中制限・レジームに応じた投下乗数 — kabusys.portfolio.risk_adjustment
- 実行エンジン起動スクリプト（paper/live を切替） — run_execution.py
- 監視ループ起動スクリプト（SystemMonitor） — run_monitoring.py
- 監視 DB（SQLite）抽象化・永続化 API — kabusys.monitoring.monitoring_db
- RiskMonitor / SystemMonitor / KillSwitch / MonitoringEngine による自動監視と Kill Switch
- AI モジュール（news_nlp: ニュースのセンチメント、regime_detector: 市場レジーム判定）
- 設定ウィザード（.env 作成） — config_setup.py
- 設定検証 CLI（.env および config/*.yaml の基本チェック） — validate_config.py
- Paper Trading 検証レポート生成ツール — tools/paper_verification_report.py
- ログ設定ユーティリティ・プロセス優先度設定ユーティリティ — kabusys.utils

---

## セットアップ手順（開発環境向け）

想定 Python バージョン: 3.10+（型注釈で | 演算子を使用）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要な主要パッケージ（例）
     - duckdb
     - psutil
     - openai
     - (オプション) PyYAML（validate_config の YAML 検証に使用）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ 実際の requirements.txt がある場合はそれを使用してください。

4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env を手動で作成（後述のサンプル参照）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ等の作成（自動作成されることが多い）
   - デフォルトでは data/ や logs/ を使用します。必要に応じて手動で作成してください。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 任意:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading: 実際のブローカーを使わず MockBrokerClient を使用し、data/paper_trading.db に記録
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — デフォルト: logs/
- OPENAI_API_KEY — AI モジュール利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知用

監視系:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 本番での Kill Flag 自動クリア制御（0/1）

注意:
- run_monitoring は常に settings.sqlite_path（本番 sqlite_path）を使用して監視テーブルにアクセスします。Paper Trading の発注ログは paper_sqlite_path に分離されます。

サンプル .env（抜粋）
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

---

## 実行方法

主要なエントリポイント:

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用、paper_db に記録されます
  - 起動前に data/stop_requested.flag が存在すると起動を行いません

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）
  - 停止は data/stop_requested.flag を作成するか Ctrl-C（KeyboardInterrupt）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（デフォルト: env または data/paper_trading.db）

ライブラリ API（モジュール単位で利用可能）:
- kabusys.research.calc_momentum / calc_value / calc_volatility
- kabusys.research.calc_forward_returns / calc_ic / factor_summary
- kabusys.portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes
- kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime

ログ:
- setup_logging により stdout（コンソール）およびファイル出力（logs/<app_name>.log、日次ローテーション）が設定されます。
- LOG_DIR 環境変数でログディレクトリを変更可能（デフォルト: logs/）

停止／Kill Switch:
- run_execution / run_monitoring はプロセス監視やフラグファイル（data/stop_requested.flag, data/kill.flag）を用いて安全停止を管理します。
- KillSwitch はリスク条件（ドローダウン、ポジション上限）で data/kill.flag を書き込み、ExecutionEngine に停止を促します。

---

## ディレクトリ構成（主要ファイル）

（ルート: src/kabusys/ 以下）

- __init__.py
- config.py                     — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
- config_setup.py               — .env 対話式ウィザード
- validate_config.py            — 設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト

- ai/
  - news_nlp.py                 — ニュースを OpenAI でスコア化して ai_scores に保存
  - regime_detector.py          — マクロ + ETF MA200 を合成してレジーム判定

- research/
  - factor_research.py          — momentum/volatility/value 等のファクター計算
  - feature_exploration.py      — 将来リターン計算、IC、統計サマリー

- portfolio/
  - portfolio_builder.py        — 候補選定、重み計算
  - position_sizing.py          — ポジションサイズ算出（単元丸め・aggregate cap）
  - risk_adjustment.py          — セクターキャップ、レジーム乗数

- monitoring/
  - monitoring_db.py            — SQLite スキーマ初期化と簡易永続化 API
  - system_monitor.py           — システム状態・データ鮮度監視
  - risk_monitor.py             — ドローダウン / ポジション上限監視
  - kill_switch.py              — kill.flag の作成 / 管理
  - monitoring_engine.py        — 各 Monitor を束ねるエンジン
  - (trade_monitor 等 他の監視モジュール)

- utils/
  - logging_setup.py            — ログ初期化ユーティリティ
  - process_priority.py         — プロセス優先度 / CPU affinity 設定ユーティリティ

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

データ / 実行時ファイル（デフォルト）
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db
- data/execution.pid
- data/stop_requested.flag
- data/kill.flag
- logs/<app_name>.log

---

## 開発・運用上の注意点

- Python 権限: set_process_priority / cpu_affinity の呼び出しは OS 権限が必要な場合があります。失敗時は警告ログを出してスキップします。
- OpenAI API: news_nlp / regime_detector は OPENAI_API_KEY が必要です。API 呼び出しはリトライ・クリップ・パース厳格化など安全策を実装していますが、利用時はコスト・レート制限に注意してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存 DB に対して必要なカラム追加処理（簡易マイグレーション）を行いますが、本格的なマイグレーション戦略は別途検討してください。
- 本番運用: KABUSYS_ENV=live を設定する前に validate_config で全設定を再確認してください。特に LINE 通知や Kill Switch 設定は本番での挙動に重大な影響があります。
- テスト: モジュールの多くは純粋関数化（DB 参照を分離）されているため、ユニットテストを書きやすく設計されています。OpenAI 呼び出し部分はテスト時にモック差し替え可能です。

---

必要であれば README の英語版や、典型的な運用手順（systemd ユニット / Dockerfile / CI 設定）を追加できます。どの情報を追加したいか教えてください。