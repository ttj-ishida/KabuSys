# KabuSys

日本株向け自動売買システムのコードベース（ドキュメント）。ここではリポジトリ内の主要コンポーネント、セットアップ手順、実行方法、ディレクトリ構成をまとめています。

---
目次
- プロジェクト概要
- 主な機能
- 動作要件（依存ライブラリ）
- セットアップ手順
- 環境変数と設定
- 実行方法（主要スクリプト）
- 運用メモ（Kill Switch / 停止フラグ / Paper Trading）
- ディレクトリ構成（主要ファイルの説明）

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムのコアライブラリ群です。
- 発注エンジン（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築・ファクター計算・AI を用いたニュースセンチメントなど、トレーディングの主要機能を含みます。
- DuckDB を分析用 DB に、SQLite を監視・注文ログ用に使用します。
- 設定は .env ファイル（環境変数）で管理し、対話式ウィザードや検証ツールが用意されています。

主な機能
- Execution
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - ブローカークライアント抽象化（本番・ペーパートレード切替）
  - 注文管理（OrderManager / OrderRepository / Reconciler / RiskManager）
- Monitoring
  - SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine（定期ポーリング）
  - SQLite ベースの monitoring DB（system_status, trade_logs, positions, risk_logs, dashboard）
  - Kill Switch（条件達成時に data/kill.flag を生成して ExecutionEngine を停止）
  - LINE へのアラート送信（AlertManager）
- Portfolio
  - 候補選定、重み計算、ポジションサイズ算出、セクターキャップやレジーム乗数の適用
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - ニュース NLP による銘柄センチメント（OpenAI API 経由）
  - 市場レジーム判定（ETF MA とマクロニュースの LLM センチメントの合成）
- Tools
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- Utilities
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）
  - config の自動読み込み / .env ウィザード / 設定検証ツール

動作要件（依存ライブラリ・推奨）
- Python 3.10+
- 必須（機能による）:
  - duckdb
  - psutil
  - requests
- AI 機能を利用する場合:
  - openai（OpenAI の新しい SDK を使用）
- 開発時 / 設定検証:
  - pyyaml（config/*.yaml の検証に使用。未インストール時はスキップされる）
- （実行環境に合わせて requirements.txt を用意する想定）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone ... && cd <repo>
2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate
3. 依存ライブラリをインストール
   - pip install duckdb psutil requests openai pyyaml
     - 必要に応じて requirements.txt を使ってください
4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話形式で .env を生成・更新します（.env は Git にコミットしないでください）
5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合は --strict を付ける
6. 必要なディレクトリ（data 等）の作成
   - 一部スクリプトは data/ にファイルを書き込みます（例: data/execution.pid, data/kill.flag, data/monitoring.db）
   - 例: mkdir -p data

主要な環境変数（代表）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 基本設定
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（default: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 実行時に使用）
- Paper Trading 固有
  - PAPER_FILL_MODE — instant | partial | never | reject（ペーパートレードの約定挙動）
- LINE（アラート）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- OpenAI（AI機能）
  - OPENAI_API_KEY
- 監視 / Kill Switch
  - PID_FILE_PATH（実行 PID ファイル）
  - KILL_FLAG_PATH（kill.flag のパス）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（1=有効、デフォルト0。live では注意）

実行方法（主要スクリプト）
- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番 DB と分離されます。
    - 起動時に data/execution.pid に PID を書き、停止時に削除されます。
    - 停止: data/stop_requested.flag を作成するとループが検知して停止します（停止フラグ位置はプロジェクトの data/ 配下）。
- 監視ループ起動（SystemMonitor 単独起動）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視ログは production DB に記録）
  - 停止: data/stop_requested.flag が存在するとループを終了
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト data/paper_trading.db を使用）
- AI 機能（例）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して OpenAI を利用（OPENAI_API_KEY 必須）

運用メモ / 重要事項
- Kill Switch
  - RiskMonitor が DRAWDOWN_ALERT や POSITION_LIMIT を検出すると KillSwitch.evaluate が data/kill.flag に理由を書き込みます（既存ファイルがあれば上書きしない）。
  - ExecutionEngine や運用担当は kill.flag の存在を検出して手動対応を行ってください。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag をクリアしますが、本番では危険なのでデフォルトは 0（無効）推奨。
- 停止フラグ / PID ファイル
  - run_execution.py / run_monitoring.py はプロジェクトの data/stop_requested.flag を定期チェックし、存在すると安全に停止します。
  - run_execution は data/execution.pid にプロセス PID を保存し（運用監視目的）、stale PID は SystemMonitor によって検出・削除されます。
- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading のときは paper_sqlite_path を使用し、本番の monitoring DB と完全に分離してログを保持します。
- OpenAI API
  - ニュース NLP やレジーム判定は OpenAI API を呼びます。API キー（OPENAI_API_KEY）を .env に設定してください。
  - API エラー時はフェイルセーフ（0.0 やスキップ）で継続する実装です。
- プロセス優先度
  - run_* スクリプトは起動時に set_process_priority("high") を呼んでプロセス優先度を上げます。psutil の権限や OS により失敗する場合があります（警告ログのみ）。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は既存 DB に対して冪等的にテーブルを作成し、必要に応じて簡易マイグレーション（カラム追加）を行います。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数・Settings 管理、自動 .env ロード
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 操作
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねるループ実行器
  - execution/ (発注周りの実装: ExecutionEngine, brokers, order_repository 等)
    - （実際のファイルはコードベースに依存）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み
    - position_sizing.py — 株数決定・スケール調整
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — モメンタム・ボラ・バリュー等
    - feature_exploration.py — 将来リターン・IC・統計
    - __init__.py
  - utils/
    - process_priority.py — psutil を使った優先度 / affinity 設定
    - __init__.py

補足（開発者向け）
- .env の自動ロード: config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動的に読み込みます。テスト時など自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 設定バリデーション: validate_config は必要な環境変数や config/*.yaml の存在（および YAML のパース）をチェックします。--strict モードで警告をエラー扱いにできます。
- テストのしやすさ: AI 呼び出し部は内部で _call_openai_api を分離しており、テスト時に patch して呼び出しを差し替えやすくなっています。

最後に
- .env には機密情報（API キー等）が含まれるため、絶対に Git にコミットしないでください。
- 本 README はコードベースから抽出した主要点をまとめたものです。各モジュールの docstring やソースを参照すると詳細な仕様やオプションが確認できます。

必要に応じて README の内容をプロジェクトの実態（requirements.txt、運用手順書、デプロイ方法）に合わせて補完してください。