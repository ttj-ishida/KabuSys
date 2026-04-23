# KabuSys

日本株向けの自動売買システム（プロトタイプ）。  
ポートフォリオ構築、発注エンジン、監視、リスク制御、研究用ファクター計算、AI によるニュースセンチメント評価などを含むモジュール群で構成されています。

以下はリポジトリ内のコードベースから作成した README です。

---

## 概要

KabuSys は次の機能を持つモジュール型の自動売買フレームワークです：

- シグナルに基づく銘柄選定・重み付け・株数決定（ポートフォリオ構築）
- 実取引 / ペーパートレード両対応の Execution Engine（ブローカ抽象化）
- 監視コンポーネント（システム健全性、注文ログ、リスク監視、Kill Switch）
- DuckDB / SQLite を用いたデータ格納・分析基盤
- 研究用モジュール（ファクター計算、特徴量探索）
- AI（OpenAI）連携によるニュースのセンチメント評価・レジーム判定
- 各種 CLI ユーティリティ（.env ウィザード、設定検証、レポート生成）

設計方針の一部：
- 本番とペーパー（paper_trading）を DB レベルで分離
- ルックアヘッドバイアス防止（target_date ベースでの処理）
- フェイルセーフ（API 失敗時のフォールバックや例外ハンドリング）
- ログは統一的に stdout と日次ローテートファイルに出力

---

## 機能一覧

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- Execution Engine 起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB に記録
- Monitoring 起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
- Paper Trading レポート生成: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築ユーティリティ（選定・重み付け・サイズ計算・セクター制限）
- ファクター計算（momentum / volatility / value）
- 研究用ユーティリティ（forward returns, IC, 統計サマリ）
- AI モジュール
  - kabusys.ai.news_nlp: ニュース記事を LLM でセンチメント評価して ai_scores に書き込み
  - kabusys.ai.regime_detector: マクロ + ETF MA200 による市場レジーム判定
- 監視（MonitoringDB）：
  - system_status, trade_logs, positions, risk_logs, dashboard テーブル管理
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（データ/ファイルによる ExecutionEngine 停止）
  - MonitoringEngine（複数 Monitor をまとめてポーリング）

---

## セットアップ手順

1. Python 仮想環境を用意する（推奨: venv / pyenv）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール  
   （プロジェクトに requirements.txt がない場合は主要依存をインストール）
   - pip install duckdb psutil openai pyyaml

   補足:
   - DuckDB: データ分析用
   - psutil: プロセス優先度・CPU 使用率などの取得
   - openai: AI 関連機能（OPENAI_API_KEY が必要）
   - PyYAML: 設定検証（config/*.yaml）のパースに使用（無くても動作するが、検証はスキップ）

3. .env を作成する  
   対話的ウィザードを使うのが簡単です:
   - python -m kabusys.config_setup

   主要な環境変数（必須・重要）:
   - JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
   - KABU_API_PASSWORD — kabuステーション API（必須）
   - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
   - OPENAI_API_KEY — OpenAI 利用時に必要（AI 機能）
   - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 用）
   - PAPER_FILL_MODE — paper_trading の約定挙動（instant / partial / never / reject）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
   - LOG_DIR — ログファイルの保存ディレクトリ（デフォルト: logs/）

4. 設定を検証する（起動前推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合: python -m kabusys.validate_config --strict

5. データディレクトリを用意（必要に応じて）
   - data/ ディレクトリは自動作成される場合がありますが、権限などを確認してください。
   - logs/ ディレクトリも作成されます（setup_logging が自動で作成を試みます）。

---

## 使い方

基本的な起動方法（開発環境を想定）:

- Execution Engine を起動（実行/ペーパーは KABUSYS_ENV に依存）
  - KABUSYS_ENV=development (発注なし)
  - KABUSYS_ENV=paper_trading (MockBrokerClient を使用、PAPER_TRADING_SQLITE_PATH に記録)
  - KABUSYS_ENV=live (本番ブローカーを使用)
  - 実行:
    - python -m kabusys.run_execution

  実行時の挙動:
  - プロセス優先度を "high" に設定しようとします（psutil による）。権限がない場合は警告になります。
  - ペーパートレード時は paper_trading 用の SQLite にアクセスします（本番 DB とは分離）。

- Monitoring を起動（システム健全性 / リスク / Kill Switch 等）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使って監視情報を記録します（run_monitoring の仕様）。

- Kill Switch / 停止フラグ
  - data/kill.flag を書き込むと ExecutionEngine に停止シグナルを送れます（KillSwitch により生成）。
  - data/stop_requested.flag（run_*.py 内で参照）を作成すると run scripts のループを抜けて終了します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動でクリアします（本番では 0 を推奨）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能
  - OPENAI_API_KEY を設定しておく必要があります（環境変数または引数で渡せる関数あり）。
  - ニューススコアリング: kabusys.ai.score_news を呼び出して ai_scores テーブルに書き込みます。
  - レジーム判定: kabusys.ai.regime_detector.score_regime を呼び出して market_regime テーブルに書き込みます。

ログ
- setup_logging により stdout と logs/<app_name>.log に日次ローテーションで出力されます（30 日保持）。
- ログレベルは環境変数 LOG_LEVEL または引数で制御可能。

注意点
- OpenAI API 等の外部キーは秘匿し、.env を Git にコミットしないこと。
- 実行ユーザの権限により psutil による優先度/affinity 設定が失敗する場合があります（警告でスキップされます）。
- DuckDB / SQLite のパスは .env で設定可能です。

---

## 主要な環境変数（まとめ）

必須
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 重要
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY — AI 機能を使う場合
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（paper_trading.db）
- PAPER_FILL_MODE — instant | partial | never | reject （デフォルト: instant）
- LOG_LEVEL — INFO（デフォルト）
- LOG_DIR — ログ出力先
- MONITOR_POLL_INTERVAL — 監視ループの秒間隔（run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1/0）

---

## サンプル .env（例）

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

※ .env.example をプロジェクトに含める想定ですが、.env は決して Git にコミットしないでください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/.env のロードと Settings 定義
  - config_setup.py — .env 作成ウィザード CLI
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化・CRUD ラッパー
    - monitoring_engine.py — Monitor 集約ポーリング
    - system_monitor.py — システム・データ鮮度監視
    - risk_monitor.py — ドローダウン/ポジション上限監視
    - trade_monitor.py — (注文監視、ログ解析)
    - kill_switch.py — フラグファイルによる停止シグナル生成
    - alert_manager.py — (アラート送信)
  - execution/    — 発注・オーダー管理・リスク管理など（Engine, BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/         — データ処理パイプライン（DuckDB 用クエリ等）
  - ...（その他モジュール）

実際のファイル一覧は src/kabusys 以下を参照してください。

---

## 開発メモ / 運用ヒント

- DB マイグレーションやスキーマ変更は monitoring_db.init_monitoring_db が冪等に行います（必要カラム追加処理あり）。
- Monitoring は監視専用 DB（SQLITE_PATH）を使用します。run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照する旨に注意してください（コード上の仕様）。
- ペーパー環境は紙上での検証用に DB を完全分離しています（PAPER_TRADING_SQLITE_PATH）。
- AI 機能は外部 API に依存するため、API 失敗時にはデフォルト値やスキップでフェイルセーフにしていますが、キーの管理とレート制限に注意してください。
- ログは stdout とファイルの両方へ出ます。プロダクションではログローテーションと保存期間（30 日）が設定されています。

---

必要であれば、各コンポーネント（ExecutionEngine、OrderManager、TradeMonitor、AlertManager 等）の詳細な API ドキュメントやシーケンス図、サンプル設定ファイル（config/*.yaml）のテンプレートも作成できます。どの部分を深堀りしますか？