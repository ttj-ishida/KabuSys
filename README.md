# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買・研究・監視を目的とした Python モジュール群です。  
戦略のシグナル生成、ポートフォリオ構築、発注エンジン（本番 / ペーパートレード）、監視・アラート、AI を用いたニュース評価などのコンポーネントを含みます。

以下は本コードベースの README（日本語）です。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要コマンド / 実行フロー）
- 環境変数（主要項目）
- ディレクトリ構成（主なファイル説明）
- 運用上の注意

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローをサポートするライブラリ／実行環境です。  
主な役割は次の通りです。

- ファクター計算・特徴量生成（DuckDB を用いた時系列処理）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- ExecutionEngine（ブローカークライアントを抽象化し本番 / ペーパートレードを分離）
- 監視（System / Trade / Risk）と Kill Switch
- AI ベースのニュースセンチメント（OpenAI API 経由）
- 検証ツール（Paper Trading レポート等）
- 環境設定ウィザード、設定検証 CLI

設計方針として「本番データに対するルックアヘッドを排除」「DB は DuckDB/SQLite を利用」「外部 API 呼び出しは明示的に管理（OpenAI 等）」などの配慮がなされています。

---

## 主な機能一覧

- portfolio
  - 候補選定（select_candidates）
  - 等重・スコア重みの計算（calc_equal_weights / calc_score_weights）
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - 銘柄ごとのポジションサイズ決定（calc_position_sizes）

- research
  - モメンタム / ボラティリティ / バリューのファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- execution
  - ExecutionEngine（本番 / ペーパートレード分離）
  - BrokerClientFactory により Mock / 実ブローカーの切替（KABUSYS_ENV に依存）
  - OrderRepository / OrderManager / RiskManager / Reconciler

- monitoring
  - SystemMonitor：プロセス生存、CPU/メモリ/ディスク、データ鮮度監視
  - TradeMonitor：滞留注文、約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：各 Monitor をまとめてポーリング、AlertManager 経由で通知

- ai
  - news_nlp.score_news：ニュース記事を LLM（OpenAI）でセンチメント化して ai_scores に格納
  - regime_detector.score_regime：ETF の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定

- tools
  - paper_verification_report：ペーパートレード DB を解析し、稼働率・約定率・レイテンシ等の検証レポートを生成

- 設定関連
  - config_setup：.env を対話式で生成 / 更新するウィザード
  - validate_config：.env と config/*.yaml の事前検証 CLI

---

## セットアップ手順

前提
- Python 3.9+ を推奨（厳密なバージョン要件はプロジェクト方針に合わせてください）
- system-level: SQLite は標準ライブラリで使用。psutil はプロセス制御・CPU情報取得に必要。

推奨手順（例）

1. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - pip install duckdb psutil openai
   - PyYAML は設定ファイルの検証に任意で必要（validate_config が YAML を検証する場合）
     - pip install pyyaml

   （もし requirements.txt が用意されている場合は `pip install -r requirements.txt` を実行してください。）

3. プロジェクトルートに移動して .env を作成
   - python -m kabusys.config_setup
   - もしくは `.env.example` を参照して手動で `.env` を作る

4. 設定の検証
   - python -m kabusys.validate_config
   - 本番運用時は `python -m kabusys.validate_config --strict` を推奨（警告もエラー扱い）

5. DB 初期化
   - 実行スクリプト（run_execution / run_monitoring）が起動時に必要なテーブルを作成します。
   - DuckDB と SQLite のファイルはデフォルトで data/ 以下に作成されます。

---

## 使い方

主要な CLI / 実行モード

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_sqlite_path（デフォルト data/paper_trading.db）へ記録します。
    - 実行中は data/execution.pid に PID を書きます。stop フラグ（data/stop_requested.flag）を監視し停止します。

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用して monitoring データを記録します。

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - データベース指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール（プログラム的に呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # APIキーは引数または OPENAI_API_KEY
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- 停止 / Kill Switch
  - KillSwitch はリスク条件を満たすと data/kill.flag に理由を書き込みます。ExecutionEngine は起動時および実行中にこのフラグを検知して停止します。
  - 実行停止フラグ（管理用）: data/stop_requested.flag（run_execution / run_monitoring が検知して終了）

注意: 実際のブローカークライアントや外部 API の利用には必要な環境変数（APIキー等）の設定が必要です。以下の環境変数一覧を参照してください。

---

## 環境変数（主要項目）

必須（起動検証でチェックされる）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

主要なオプション / 説明
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant | partial | never | reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH — 実行エンジンの PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1、デフォルト: 0）

設定の不足や不正な値は `python -m kabusys.validate_config` で事前にチェックしてください。

---

## ディレクトリ構成（主要ファイルの説明）

（プロジェクトの src/kabusys 以下の主要ファイルを抜粋）

- kabusys/__init__.py
  - パッケージ定義、バージョン情報

- kabusys/config.py
  - 環境変数の自動読み込み（.env / .env.local）
  - Settings クラス（全設定の集中参照）

- kabusys/config_setup.py
  - .env を対話式に作成・更新するウィザード

- kabusys/validate_config.py
  - 起動前に .env / config/*.yaml を検証する CLI

- run_execution.py
  - ExecutionEngine を起動するエントリポイント
  - ペーパートレード時は paper DB に分離

- run_monitoring.py
  - SystemMonitor のポーリングループを起動するエントリポイント

- kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - ポートフォリオ構築とポジションサイズ算出ロジック

- kabusys/research/
  - factor_research.py, feature_exploration.py
  - ファクター計算・IC・統計解析

- kabusys/execution/
  - Execution エンジン関連（BrokerFactory, OrderManager, RiskManager 等） — （実装ファイルは省略していますがインターフェースとして利用）

- kabusys/monitoring/
  - monitoring_db.py — SQLite を使った監視ログ永続化
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py
  - 監視・Kill Switch・アラート関連

- kabusys/ai/
  - news_nlp.py — OpenAI でニュースをスコアリング
  - regime_detector.py — マクロセンチメント + MA200 乖離でレジーム判定

- kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート

- kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/
  - 実行時に生成される DB / PID / flag ファイル（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）での運用前に validate_config で設定を十分に検証してください。特に LINE 通知・Kill Switch の設定は重要です。
- .env ファイルは機密情報（API キー等）を含むため絶対に Git 等へコミットしないでください。
- OpenAI API 呼び出しはコストとレート制限があります。news_nlp / regime_detector はリトライとフェイルセーフ（失敗時はスコア 0.0 など）を実装していますが、運用ポリシーを決めてください。
- PID / flag ファイル（data/execution.pid, data/kill.flag, data/stop_requested.flag）はプロセス制御に使われます。手動で削除する際は注意してください。
- DuckDB / SQLite のファイルはバックアップや容量管理を検討してください。monitoring.db は監視ログで肥大化する可能性があります。

---

README はここまでです。必要に応じて「requirements.txt」や「.env.example」を追加し、CI/デプロイ手順（systemd / supervisor / Docker 等）を補足すると運用がより容易になります。質問や追加で記載したい項目があれば教えてください。