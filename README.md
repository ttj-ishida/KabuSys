# KabuSys

日本株自動売買システムのパイロット実装 (読み取り専用ドキュメント: コードベースから自動生成)。

この README はリポジトリ内の主要スクリプト・モジュールの概要、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

注意: .env は機密情報（API トークン等）を含みます。絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買 / 研究パイプラインを想定したモジュール群です。主な機能は次のとおりです。

- ExecutionEngine（発注エンジン）: ブローカークライアントを通じた注文管理、リスク管理、注文調整（本番/ペーパー両対応）。
- Monitoring: システム稼働状態・データ鮮度・注文ログ等の監視、Kill Switch による安全停止。
- Portfolio Construction: 候補選定、重み付け、ポジションサイズ計算、セクター制約などの純粋関数群。
- Research / Features: ファクター計算（モメンタム・バリュー・ボラティリティ等）、特徴量探索、IC 計算。
- AI モジュール: ニュースを LLM（OpenAI）でスコアリング、マクロセンチメントから市場レジーム判定。
- ユーティリティ: ログ設定、プロセス優先度設定、.env ウィザード、設定検証 CLI、レポート生成ツールなど。
- 永続化: DuckDB（分析用）と SQLite（監視 / 発注ログ）を利用。

設計上のポイント:
- Paper trading（ペーパートレード）と live（本番）は DB を分離して安全性を確保。
- Watchdog / Kill Switch により、ドローダウンやポジション上限超過時に ExecutionEngine を安全停止可能。
- LLM 呼び出しはリトライやバリデーションを備え、失敗時はフェイルセーフで継続する設計。

---

## 機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution: 発注エンジンを起動
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
  - python -m kabusys.run_monitoring: 監視ループを起動（ポーリング監視）
- 設定支援 / 検証
  - python -m kabusys.config_setup: .env を対話式で生成・更新するウィザード
  - python -m kabusys.validate_config: .env と config/*.yaml の検証ツール
- ツール
  - python -m kabusys.tools.paper_verification_report: ペーパートレード検証レポートを生成
- モジュール
  - kabusys.portfolio: 候補選定・重み付け・ポジションサイズ計算
  - kabusys.research: ファクター計算（momentum/value/volatility）・特徴量解析
  - kabusys.ai: news_nlp（ニューススコアリング）、regime_detector（市場レジーム判定）
  - kabusys.monitoring: system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_engine
  - kabusys.utils: logging_setup（統一ログ設定）、process_priority（優先度/affinity 対応）

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成します。
   - 例:
     - git clone <repo_url>
     - cd <repo>
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（プロジェクトに requirements.txt がある場合はそれを利用してください）。
   - 最低限必要になる主要ライブラリ（例）:
     - duckdb
     - psutil
     - openai
     - pyyaml (設定検証で任意)
   - 例:
     - pip install duckdb psutil openai pyyaml

3. .env を作成します（対話式ウィザード推奨）。
   - python -m kabusys.config_setup
   - ウィザード後、.env がプロジェクトルートに保存されます。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（例とデフォルト）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db（paper_trading 用）
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — LLM 機能を使う場合に必要

4. 設定を検証します。
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱いになります。

5. ログ / データディレクトリの準備
   - デフォルトでは以下パスが使われます。起動時に自動作成されますが、権限等で失敗する場合は手動で作成してください。
     - data/
     - logs/

---

## 使い方（主要コマンド）

- 発注エンジン起動
  - KABUSYS_ENV に応じて本番/ペーパーの挙動が切り替わります。
  - 実行:
    - python -m kabusys.run_execution
  - 停止方法:
    - ExecutionEngine は data/stop_requested.flag を監視しており、ファイル存在を検知すると停止します。
    - また監視側の KillSwitch が data/kill.flag を生成すると停止シグナルが送られます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止:
    - data/stop_requested.flag を作成すると run_monitoring のループが終了します（ファイルがあると run_execution も起動を控える挙動あり）。

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。環境変数 PAPER_TRADING_SQLITE_PATH または --db で上書き可。

- AI / レジーム判定・ニューススコアリング
  - モジュール関数を直接呼ぶ想定（スクリプトとしては未エクスポートの関数あり）。
  - OPENAI_API_KEY を設定して、適切な DuckDB 接続を渡して呼び出す。

ログ:
- ログは logs/<app_name>.log に日次ローテーションで保存されます（例: logs/execution.log, logs/monitoring.log）。
- setup_logging を各起動スクリプトで共通利用しています。

停止 / Kill Switch / PID:
- data/stop_requested.flag: 管理目的の停止フラグ（自動起動からの停止など）。
- data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine に停止を強制するために使用。
- data/execution.pid: ExecutionEngine の PID 管理ファイル（起動時に指定の場所へ出力）。

環境変数関連の注意:
- 自動で .env をロードする仕組みがあります（プロジェクトルートで .env/.env.local を探索）。テストや特殊用途で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・パッケージの構成（src/kabusys 以下）です。実際のリポジトリルートに合わせて読み替えてください。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / Settings 管理（自動 .env 読み込み含む）
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py                — ニュースの LLM スコアリング
      - regime_detector.py         — 市場レジーム判定（LLM + MA）
    - monitoring/
      - monitoring_db.py           — SQLite 永続層
      - monitoring_engine.py       — 各モニタの統括
      - system_monitor.py
      - trade_monitor.py           — （trade 関連の検出ロジック: ファイル未掲載部分）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py           — （メール/LINE 通知等、ファイル未掲載部分）
    - execution/
      - execution_engine.py        — ExecutionEngine（主要ロジック: ファイル未掲載部分）
      - broker_factory.py          — BrokerClientFactory（Mock/実ブローカ分岐）
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - その他発注関連モジュール
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
    - data/                         — 実行時に使用するファイル群（logs と同様に自動作成されることが想定）
      - *.db, *.pid, stop_requested.flag, kill.flag, など

注: 一部の実装（例えば trade_monitor.py の全内容や execution_engine の詳細）は README 中の抜粋に含まれていない場合があります。詳細は各モジュール内ドキュメントや docstring を参照してください。

---

## よくある運用上の注意 / トラブルシューティング

- .env を誤ってコミットしないこと。README 上では厳重注意しています。
- production（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨。自動クリアは危険です。
- ログディレクトリ作成に失敗した場合、コンソール出力のみになります。パーミッションを確認してください。
- ExecutionEngine を起動してもすぐに動かない（あるいは起動しない）場合:
  - data/stop_requested.flag または data/kill.flag が存在していないか確認してください。
  - .env の必須変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）がセットされているか確認してください。
- LLM 呼び出しが失敗する場合（OpenAI 関連）:
  - OPENAI_API_KEY が設定されているか確認。
  - ネットワーク制限やレート制限により失敗する場合はログを参照。実装はリトライ・フォールバックあり。

---

必要ならば README を拡張して、具体的な設定例（.env.example の抜粋）、systemd / Supervisor 用のサービスユニット例、より詳細な API 使用法（AI モジュール等）やテスト方法を追加できます。どの情報を追加したいか教えてください。