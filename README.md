# KabuSys

日本株自動売買システムのパッケージ（コードベースの抜粋）。この README はプロジェクトの概要、主要機能、セットアップ手順、使い方（起動コマンド例）、およびディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買（Execution）・監視（Monitoring）・リサーチ（Research）・AI（ニュース NLP）機能を含むパッケージです。  
主な設計方針は以下のとおりです。

- モジュール化されたコンポーネント群（ExecutionEngine、MonitoringEngine、Portfolio Construction、Research、AI）  
- 環境変数 / .env による設定管理（`.env` 自動ロード機能あり）  
- SQLite（監視ログ）・DuckDB（分析向け）による永続化  
- Paper Trading 環境は本番 DB と分離（別 SQLite）  
- OpenAI を用いたニュースセンチメント / レジーム判定機能（API キー必須）

---

## 主な機能一覧

- Execution（発注エンジン）
  - ExecutionEngine による発注・注文管理
  - Paper Trading 時は MockBrokerClient を利用し、paper_trading DB に記録
  - リスク管理（max_position_pct / max_utilization 等）

- Monitoring（監視）
  - SystemMonitor：CPU・メモリ・ディスク・プロセスの監視、データ鮮度チェック
  - TradeMonitor：注文・約定ログの監視（滞留注文・異常約定の検出）
  - RiskMonitor：ドローダウンや保有上限の監視、kill switch 発火
  - MonitoringEngine：各モニタを定期ポーリングしアラート・Kill Switch を評価

- Portfolio（ポートフォリオ構築）
  - 候補選定（スコア降順）、等金額・スコア加重の重み化
  - セクター上限適用、レジーム乗数、ポジションサイズ計算（単元丸め・aggregate cap）

- Research（研究・分析）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC（Information Coefficient）や統計サマリー

- AI（ニュース NLP / レジーム判定）
  - raw_news を OpenAI（gpt-4o-mini 等）で評価し銘柄別スコアを ai_scores テーブルへ書込
  - ETF を用いた ma200 ベースの指標 + マクロニュースの LLM 評価で市場レジーム判定
  - API 呼び出しはリトライ／フェイルセーフ実装

- ユーティリティ
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）
  - ロギング設定・プロセス優先度設定ユーティリティ

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、Python 仮想環境を用意します。
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストールします（プロジェクトに requirements.txt がある前提、無ければ下記ライブラリをインストール）。
   推奨ライブラリ（抜粋）:
   - duckdb
   - psutil
   - openai
   - PyYAML（設定検証で使用。必須ではない）
   ```bash
   pip install duckdb psutil openai PyYAML
   ```

3. .env を作成します（ウィザード推奨）。
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードが出力する `.env` をプロジェクトルートに保存してください（.env は Git にコミットしないでください）。

4. 設定を検証します。
   ```bash
   python -m kabusys.validate_config
   # 警告を厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリとログディレクトリを作成（必要に応じて）。
   ```bash
   mkdir -p data logs
   ```

注意:
- 自動的に `.env` を読み込む機能はデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- OpenAI を使う機能は環境変数 `OPENAI_API_KEY` を設定してください。

---

## 使い方（起動・主要コマンド）

主要スクリプトはパッケージモジュールとして実行できます。

- ExecutionEngine（発注エンジン）起動
  - 本番・開発は KABUSYS_ENV に依存
  - Paper Trading（KABUSYS_ENV=paper_trading）は MockBrokerClient を使い、data/paper_trading.db に記録される
  ```bash
  # 例: 開発/ローカル実行
  export KABUSYS_ENV=development
  python -m kabusys.run_execution

  # 例: ペーパートレード
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Monitoring（監視ループ）起動
  - デフォルトポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒単位）。
  - 監視は環境にかかわらず production の sqlite_path を使って監視 DB を初期化します。
  ```bash
  # 例: 30秒間隔で監視
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- .env 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 別 DB を指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（環境変数 `OPENAI_API_KEY` または関数引数で指定）
  - プログラムからは `kabusys.ai.score_news` や `kabusys.ai.regime_detector.score_regime` を呼び出します

停止・Kill Switch:
- 実行中の Engine/Monitor を外部で止めるにはプロジェクト内の flag ファイルを利用します。
  - 停止要求フラグ: data/stop_requested.flag（run_* スクリプトで監視）
  - Kill Switch の発火・監視: data/kill.flag（KillSwitch が作成）
  - PID ファイル: data/execution.pid など（Settings.pid_file_path で指定可能）

ログ:
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション）に出力されます。
- ログディレクトリは `LOG_DIR` 環境変数や setup_logging の引数で変更可能。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper trading の約定挙動（instant | partial | never | reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring で利用）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

---

## ディレクトリ構成（抜粋）

以下はパッケージの主要ファイル・ディレクトリの概要（src/kabusys 配下）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite を使った監視ログ永続化
    - system_monitor.py      — システム状態監視
    - trade_monitor.py       — 注文/約定監視（ファイルに含まれないが同階層に想定）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書込ユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — アラート送信（ファイルに含まれないが存在が想定される）
  - execution/
    - execution_engine.py    — ExecutionEngine 実装（ファイル抜粋内に参照あり）
    - broker_factory.py      — BrokerClientFactory（Mock/実ブローカー切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数計算・単元丸め・aggregate cap
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum, volatility, value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼出し、ai_scores 書込）
    - regime_detector.py     — レジーム判定（ma200 + macro sentiment）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

- data/                      — 実行時に使う SQLite / PID / flag 等（プロジェクトルート）
- logs/                      — ログ出力先（デフォルト）

---

## 運用上の注意 / 既知の挙動

- run_monitoring は MONITOR_POLL_INTERVAL を環境変数で上書きできます。0 や負の値は無効扱いでデフォルト（60秒）にフォールバックします。
- 監視（monitoring）モジュールは、環境に関わらず production 用の sqlite_path を使用して監視テーブルを初期化します（init_monitoring_db を実行）。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離するため、必ず `PAPER_TRADING_SQLITE_PATH` を確認してください。デフォルトは data/paper_trading.db です。
- OpenAI/API 呼び出し部分はリトライ・バックオフ・パース検証を行いますが、API キー未設定時や致命的な失敗時は機能をスキップする（もしくは例外を上げる）場合があります。AI 機能を使う際は `OPENAI_API_KEY` を設定してください。
- .env はプロジェクトルートの .git / pyproject.toml を基準に自動ロードされます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 本 README はコードベースの抜粋に基づいて作成しています。実際の運用時はプロジェクトのドキュメントや config/*.yaml を参照してください。

---

必要であれば、この README を元に「デプロイ手順（systemd / supervisor 用の unit ファイル例）」「監視アラートの設定方法（LINE 通知の例）」「詳しい DB スキーマ説明」などの追加章も作成できます。どの情報を優先して補足しますか？