# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README。  
このドキュメントはリポジトリ内のスクリプトとモジュール構成をもとに、セットアップと基本的な使い方を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／リサーチ基盤です。主要機能は以下を含みます。

- 戦略の研究（ファクター計算・特徴量解析）
- ポートフォリオ構築（銘柄選定・重み付け・株数決定）
- ExecutionEngine（発注ロジック・リスク管理）
- 監視（System / Trade / Risk のポーリング監視、Kill Switch）
- Paper Trading 向けの分離された DB とモックブローカー
- AI によるニュースセンチメント評価（OpenAI を利用）
- 各種ユーティリティ（設定ウィザード、設定検証、検証レポート生成等）

設計方針として「本番データベースとペーパートレードを分離」「ルックアヘッドバイアスを避ける」「冪等操作・フェイルセーフ重視」が反映されています。

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成/更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml のチェック）
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper DB（data/paper_trading.db）へ記録
- 監視ループ起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整（デフォルト 60 秒）
  - 監視は環境にかかわらず production の sqlite_path を使用
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- AI モジュール
  - kabusys.ai.news_nlp: ニュースを OpenAI に送って銘柄ごとのセンチメントを ai_scores に書込
  - kabusys.ai.regime_detector: マクロセンチメント と ETF MA200 乖離から市場レジーム判定
- Portfolio モジュール
  - 銘柄選定（select_candidates）、等比率/スコア重み計算、株数決定（risk_based 等）、セクター制限、レジーム乗数
- 監視（monitoring）モジュール
  - system_monitor, trade_monitor, risk_monitor, kill_switch, alert_manager（通知部分は設定依存）

---

## セットアップ手順

前提: Python 3.9+ を想定（コードは型注釈や一部の新しい標準機能を使用）。環境に合わせて仮想環境を作成してください。

1. リポジトリをクローンしてルートに移動
   - git clone <repo>
   - cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 推奨パッケージ（抜粋）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config/*.yaml の内容検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   > 補足: requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で .env を作成
   - 自動ロード: モジュール起動時にプロジェクトルート（.git または pyproject.toml）を検出できれば `.env` / `.env.local` が自動で読み込まれます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いにできます。

6. ログディレクトリ
   - デフォルト logs/ にアプリごとのログ（execution.log, monitoring.log など）を日次ローテーションで保存します。`LOG_DIR` で変更可。

---

## 環境変数（主要）

必須（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要なオプション（主なもの）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを利用する場合）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant, partial, never, reject）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

監視関連
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: Settings での調整可能

注意点:
- .env ファイルは絶対に Git にコミットしないでください。
- `config/*.yaml` が存在する場合は内容を確認してください（validate_config でチェック可能）。

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番/ペーパー共通）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
    - 起動前に data/stop_requested.flag があると起動しません。
    - 実行中は data/execution.pid に PID が書き込まれます（Settings.pid_file_path で変更可）。
    - 停止は stop_requested.flag の作成または kill.flag（Kill Switch）により行われます。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（デフォルト 60 秒）。
  - 監視は Settings.sqlite_path（監視 DB）を使用し、環境にかかわらず production の sqlite_path を参照する実装になっています。
  - 停止は data/stop_requested.flag による検出でループを終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --from YYYY-MM-DD: レポート開始日
    - --to YYYY-MM-DD: レポート終了日
    - --db PATH: DB ファイルパス（環境変数 PAPER_TRADING_SQLITE_PATH を上書き）

- AI モジュール呼び出し（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キーが必要（引数で渡すか環境変数 OPENAI_API_KEY を利用）

---

## 制御フラグ・ファイル

- data/stop_requested.flag
  - run_execution / run_monitoring がこのファイルの存在を検知すると適切に停止処理を行うための外部制御フラグ（手動停止等）。

- data/kill.flag
  - KillSwitch（監視モジュール）が条件を満たした際に書き込むファイル。ExecutionEngine 停止のトリガーとして機能します。
  - Settings.kill_flag_clear_on_start により起動時に自動クリアする設定が可能（本番では 0 推奨）。

---

## ロギング

- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" など)
  - デフォルトは stdout 出力 + 日次ローテーションで logs/<app_name>.log（30日保持）
  - LOG_DIR 環境変数または引数でログディレクトリを変更可
  - LOG_LEVEL でログレベルを制御

---

## 開発・運用上の注意

- Paper Trading と本番 DB は完全に分離して運用してください（PAPER_TRADING_SQLITE_PATH を設定）。
- AI 呼び出しはレート制限・不安定さに配慮して実装（リトライやフェイルセーフあり）。API キー管理は厳重に。
- .env の自動読み込みはルート検出（.git または pyproject.toml）に依存します。CI/特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して明示的に環境変数を注入してください。
- validate_config は事前に必ず実行し、設定ミスや欠損を検出してください（特に KABUSYS_ENV=live の場合は警告が多くなります）。

---

## ディレクトリ構成（抜粋）

リポジトリの主要なファイル・ディレクトリ構成の概要（実際のファイル数・階層は変わる可能性があります）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照実装がある前提)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照実装がある前提)
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - portfolio/ (上記参照)
  - その他: data/（runs 時に使用するファイル群: *.db, kill.flag, stop_requested.flag, execution.pid）, logs/

---

## よくある質問 / トラブルシューティング

- Q: .env が自動で読み込まれない
  - A: プロジェクトルートが .git または pyproject.toml を基準に検出されます。見つからない場合は自動ロードをスキップします。明示的に読み込みたい場合は環境変数を直接エクスポートしてください。

- Q: run_monitoring のポーリング間隔を変えたい
  - A: 環境変数 `MONITOR_POLL_INTERVAL` を秒数で設定してください（1 以上）。無効値はデフォルト 60 秒にフォールバックします。

- Q: Paper Trading と本番の DB が混ざるのを防ぐには？
  - A: KABUSYS_ENV=paper_trading を設定すると run_execution は PAPER_TRADING_SQLITE_PATH を使用して完全に分離された DB に記録します。

- Q: OpenAI 呼び出しが失敗したときどうなる？
  - A: ニューススコアやレジーム判定はリトライとフェイルセーフ（失敗時はスコア0やスキップ）を組み込んでいます。例外は上位に上がらない設計です。

---

この README はリポジトリ内のコードから抽出した情報に基づいています。実際の追加モジュールや変更はリポジトリの最新ソースを参照してください。必要であれば、各モジュール（ExecutionEngine / TradeMonitor / AlertManager 等）の使い方や設定例を追記します。