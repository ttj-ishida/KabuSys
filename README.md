# KabuSys

日本株自動売買システムの Python コードベース。戦略の研究・ファクター計算、ポートフォリオ構築、注文実行（実運用 / ペーパートレード）、および運用監視を含むコンポーネント群で構成されています。

以下はリポジトリの主要な機能・使い方・セットアップ手順をまとめた README.md です。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群から成ります:

- 研究（research）: DuckDB 上の時系列データからファクターや将来リターンを計算するツール
- ポートフォリオ構築（portfolio）: 候補選定、重み付け、リスク調整、数量決定など純粋関数群
- 注文実行（execution）: ブローカークライアント経由で発注を管理する ExecutionEngine（実運用 / ペーパートレード対応）
- 監視（monitoring）: システム状態・注文状況・リスクをポーリングしてログ保存・アラート・KillSwitch 発動を行う
- AI（ai）: OpenAI を使ったニュースのセンチメント評価や市場レジーム判定
- ユーティリティ（utils）: ロギング設定やプロセス優先度設定などの共通ユーティリティ
- ツール（tools）: ペーパートレード検証レポート生成などの補助ツール

設計方針の一部:
- DuckDB／SQLite をデータ層に使用（分析／監視に分離）
- 環境変数（.env）による設定管理
- ペーパートレードは本番 DB と分離される（PAPER_TRADING_SQLITE_PATH）
- OpenAI 統合はフェイルセーフ設計（API 失敗時に影響最小化）

---

## 主な機能一覧

- 環境設定ウィザード: `kabusys.config_setup` による .env 生成/更新
- 設定検証 CLI: `kabusys.validate_config` で環境変数と config/*.yaml を検証
- 実行エンジン起動スクリプト: `run_execution.py`（本番 / paper_trading を切替）
- 監視ループ起動スクリプト: `run_monitoring.py`（MONITOR_POLL_INTERVAL による間隔指定）
- 監視 DB 永続化（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard
- リスク監視（ドローダウン／ポジション上限）・自動 Kill Switch 発動
- ポートフォリオ構築: 候補選定、等配分・スコア配分、リスク制限、切り上げ/単元調整
- Research: momentum/volatility/value 等のファクター計算、IC/統計解析
- AI モジュール: ニュースセンチメント（OpenAI）→ ai_scores、レジーム判定（market_regime）
- ツール: ペーパートレード検証レポート生成スクリプト

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 無ければ最低限以下を入れてください:
     - pip install duckdb psutil openai PyYAML
   - （実際のプロジェクトでは追加パッケージが必要な場合があります）

3. プロジェクトルートに `.env` を作成
   - 自動で読み込まれます（起動スクリプト実行時。OS 環境変数が優先）。
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY（AI 機能を使う場合）
   - そのほか:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信用、任意）

   - 例 .env（抜粋）:
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

5. 設定検証
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - 通常（KABUSYS_ENV に基づき本番 or paper_trading 判定される）:
    - python -m kabusys.run_execution
  - ペーパートレードとして起動するには:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止はプロジェクトルートの data/stop_requested.flag を作成するとエンジンが検知して停止します。
  - 実行中は data/execution.pid に PID が書かれます（設定による）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を上書きする:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path を使用（環境に依らず監視 DB は同じファイルを参照します）。
  - 停止は data/stop_requested.flag を作成すると監視ループが終了します。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（コード呼び出し）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジームスコア:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。

---

## 運用上のファイル・フラグ

- data/stop_requested.flag
  - run_monitoring / run_execution が監視している汎用停止フラグ（存在すれば安全に終了）

- data/kill.flag
  - KillSwitch が書き込む停止要求フラグ（ExecutionEngine に対する強制停止シグナル）
  - 本番環境では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨

- data/execution.pid
  - ExecutionEngine が PID を書き込むファイル（設定により変更可能）

- ログディレクトリ
  - デフォルト: logs/
  - ログ出力は stdout と日次ローテートファイル（TimedRotatingFileHandler）に送られます

---

## 設定項目（主要な環境変数）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨/主要:
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH (default data/kabusys.duckdb)
- SQLITE_PATH (default data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default data/paper_trading.db)
- OPENAI_API_KEY（AI 機能）
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、"0"/"1"）

.env の自動ロード:
- プロジェクトルートにある `.env` / `.env.local` を自動でロードします（ただし OS 環境変数が優先）
- 自動ロードを無効にするには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## ディレクトリ構成（主なファイルと説明）

- src/kabusys/
  - __init__.py
  - __version__ 定義
  - config.py
    - 環境変数の読み込み、自動 .env ロード、Settings クラス
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - 環境・設定ファイル検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 判定あり）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - ペーパートレードの検証レポート生成スクリプト
  - ai/
    - news_nlp.py
      - ニュースを OpenAI でスコア化して ai_scores に書き込むロジック
    - regime_detector.py
      - ETF MA とマクロニュースを合成して市場レジーム判定
  - research/
    - factor_research.py
      - モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB ベース）
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリーなど
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
      - SQLite を使った監視ログの永続化（初期化 / CRUD）
    - system_monitor.py
    - trade_monitor.py (リポジトリに実装あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (ログのアラート送信機能など)
  - utils/
    - logging_setup.py
      - 共通ログ設定（stdout + 日次ローテート）
    - process_priority.py
      - psutil を使ったプロセス優先度 / CPU affinity 設定

---

## 開発・運用上の注意点

- DB の切り分け:
  - ペーパートレード実行時は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離します。
- OpenAI 利用:
  - API エラーはリトライやフォールバックするよう設計されていますが、API キーは安全に管理してください。
- ログ:
  - logs/ 配下に日次ローテートでログが出力されます。ログディレクトリの作成失敗時はコンソール出力のみ継続します。
- Kill Switch:
  - 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 に設定し、誤って Kill Switch をクリアしないように注意してください。
- プロセス優先度:
  - run_* スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。権限不足や未対応 OS の場合は警告を出してスキップします。

---

## よく使うコマンドまとめ

- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

もし README に追加したい情報（例: requirements.txt の正確な内容、デプロイ / systemd/cron による運用例、API の詳細仕様、テストの実行方法など）があれば教えてください。必要に応じて追記・整備します。