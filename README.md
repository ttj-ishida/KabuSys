# KabuSys

バージョン: 0.1.0

軽量な日本株自動売買システムのコードベースです。戦略、発注実行（実口座 / ペーパートレード）、監視、リサーチ、AI を用いたニュース解析などの主要機能をモジュール化して提供します。

注意: このリポジトリは .env に機密情報（API トークン・パスワード等）を保持する設計になっています。.env の内容は絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は以下の機能群を組み合わせて自動売買ワークフローを実現します。

- データ基盤（DuckDB / SQLite）を用いた価格・財務・ニュースの蓄積
- ファクター計算・特徴量解析（research パッケージ）
- ポートフォリオ構築（候補選定・配分・リスク調整・ポジション決定）
- ExecutionEngine（発注処理） — 実口座またはペーパートレード（分離された DB）
- 監視（system / trade / risk）と Kill Switch による自動停止
- AI（OpenAI）を用いたニュースセンチメント評価と市場レジーム判定
- 各種 CLI ユーティリティ（.env ウィザード・設定検証・ペーパートレード検証レポート 等）

---

## 主な機能一覧

- run_execution: ExecutionEngine を起動。KABUSYS_ENV に応じて実ブローカー or MockBroker を選択。ペーパートレード時は data/paper_trading.db に完全分離して記録。
- run_monitoring: SystemMonitor をポーリングして system_status / risk_logs / trade_logs 等に永続化。MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）。
- monitoring: RiskMonitor / TradeMonitor / SystemMonitor / KillSwitch / AlertManager などの監視ロジック。
- ai: news_nlp（ニュースの LLM センチメント評価）、regime_detector（市場レジーム判定）。
- research: ファクター計算（モメンタム、ボラティリティ、バリュー）や特徴量解析（IC、将来リターン等）。
- portfolio: 候補選定、重み算出、リスク調整、ポジションサイジング。
- utils: ロギング設定、プロセス優先度 / CPU affinity 設定、設定読み込みロジック等。
- tools.paper_verification_report: ペーパートレードログから検証レポート（稼働率、成功率、レイテンシ等）を生成。
- config_setup: 対話式 .env 生成ウィザード。
- validate_config: .env と config/*.yaml を起動前に検証する CLI。

---

## セットアップ手順

前提:
- Python 3.10+ を推奨
- システムに sqlite3, pip が利用可能であること

1. リポジトリをクローン / 配布パッケージを展開する

2. 仮想環境を作成・有効化（任意だが推奨）
   - Linux / macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 必要パッケージをインストール
   - 最低限の依存（主要ライブラリ例）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (validate_config で YAML の検証を行う場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合はそれを使用してください）

4. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考にして手動で作成
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - その他（デフォルト値あり）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の専用 DB）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（デフォルト: INFO）

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 問題があれば修正する。--strict を使うと警告も失敗扱いになる:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - デフォルトで data/ 以下に DB やフラグファイルが作成されます。アクセス権に注意してください。

---

## 使い方

以下は代表的なコマンド例です。各コマンドはパッケージモードで実行できます。

- ExecutionEngine を起動（通常モード / 実行用）:
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。

- Monitoring を起動（ポーリング）:
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30  # 30 秒間隔
  - 監視は常に本番用の sqlite_path を使用します（KABUSYS_ENV に依存しません）。
  - 停止方法: data/stop_requested.flag を作成すると監視ループが検知して終了します。

- .env の対話式セットアップ:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH で既定値を上書き可能

- AI 関連（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY か関数引数で指定）
  - モジュール API 例:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime

- ログ
  - デフォルト: logs/<app_name>.log（日次ローテート、30 日保持）
  - ログディレクトリは環境変数 LOG_DIR または setup_logging の引数で変更可能
  - ログレベルは LOG_LEVEL で制御

- Kill Switch / Stop フラグ
  - KillSwitch は settings.kill_flag_path（デフォルト data/kill.flag）を作成して ExecutionEngine に停止指示を送ります（ExecutionEngine は起動時に kill.flag のクリアを行うオプションあり）。
  - 手動停止用フラグ: data/stop_requested.flag を作成すると run_execution/run_monitoring のループが終了します。
  - PID ファイル:
    - ExecutionEngine は data/execution.pid に PID を書きます（停止/状態確認に利用）。

---

## 主要な環境変数（抜粋とデフォルト）

- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — data/paper_trading.db
- OPENAI_API_KEY — OpenAI 利用時に必須
- LOG_LEVEL — INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — デフォルト logs/
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1、デフォルト 0。本番では 0 推奨）

---

## ディレクトリ構成

リポジトリの主要ファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定（AI + MA）
  - monitoring/
    - monitoring_db.py      — SQLite テーブル作成 / 永続化 API
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - system_monitor.py     — システム状態・データ鮮度の監視
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - trade_monitor.py      — （存在する想定、trade 監視）
    - kill_switch.py
    - alert_manager.py      — （通知処理、LINE 等）（実装場所）
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
  - execution/               — Execution 系の実装（broker_factory 等）
  - data/                    — データ関連コード（pipeline, stats 等）
  - monitoring/              — 監視関連（上記と重複するサブモジュール群）
  - ...（その他モジュール）

data/ と logs/ は実行時に作成されることが多いです。

---

## 開発者向けメモ / 注意事項

- ペーパートレード:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパー用 DB に記録します。本番 DB と完全分離されています。
- OpenAI:
  - news_nlp と regime_detector は OpenAI API を利用します。API 呼び出しにはレート制限やエラーが発生するため、各所で指数バックオフやフォールバック挙動を実装しています。OPENAI_API_KEY が必要です。
- ログ / 権限:
  - プロセス優先度設定（psutil を使用）は OS 権限に依存します。権限不足の場合は警告を出してスキップします。
  - ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブルを作成し、必要なカラムがない場合は ALTER TABLE で追加する簡易マイグレーションを行います。
- テスト:
  - 外部 API 呼び出しはユニットテスト時にモック化しやすいように内部呼び出しを分離しています（例: _call_openai_api を patch）。

---

## トラブルシューティング

- run_monitoring のポーリング間隔が無効な値のとき:
  - MONITOR_POLL_INTERVAL は正の整数で設定してください。無効な場合はデフォルト 60 秒にフォールバックします。
- OpenAI 未設定:
  - AI 機能を呼ぶと ValueError が上がります。OPENAI_API_KEY を設定してください。
- ファイル/ディレクトリのパーミッションエラー:
  - data/ や logs/ の書き込み権限を確認してください。
- kill.flag による誤停止:
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨します。必要時は data/kill.flag を手動で削除してください。

---

本 README はコードベースの主要点をまとめたものです。詳細な実装や追加オプションは各モジュールの docstring / ソースコードを参照してください。必要であれば、README に実行例や開発フロー、CI 連携手順などを追記できます。どの情報を追加したいか教えてください。