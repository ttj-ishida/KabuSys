# KabuSys

日本株自動売買システムのコアライブラリ群（README）。  
本ドキュメントはリポジトリ内の主要スクリプト／モジュールに基づき、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。  
主な目的は次のとおりです。

- ファクター計算・リサーチ（DuckDB を用いた時系列分析）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ExecutionEngine（発注管理・ブローカークライアントを介した発注/約定ハンドリング）
- Monitoring（システム状態・取引状況・リスクを継続監視、Kill Switch による発注停止）
- AI 補助（ニュースセンチメント、レジーム判定：OpenAI API 利用）
- 開発支援ツール（env ウィザード、設定検証、ペーパートレード検証レポート）

設計上の特徴：
- DuckDB を分析データ用、SQLite を監視・発注履歴用に使用（環境に応じて paper_trading 用 DB は分離）
- LLM（OpenAI）呼び出しは堅牢性を意識したリトライ・バリデーションを実装
- ログ設定・プロセス優先度・CPU affinity 設定など運用向けユーティリティを提供

---

## 主な機能一覧

- 環境管理
  - .env 自動読み込み（プロジェクトルートの .env/.env.local）
  - 対話式 env ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）

- Execution（発注）
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
  - Paper trading モード（KABUSYS_ENV=paper_trading）で MockBroker を使用し、paper DB に記録
  - リスク管理（RiskManager／Reconciler／OrderManager 等の統合）

- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/Disk、データ鮮度、Execution プロセス監視
  - TradeMonitor：注文ログの異常検出（滞留注文・価格異常など）
  - RiskMonitor：ドローダウン・ポジション上限監視 → kill.flag 書き込み可能
  - MonitoringEngine：各モニタのポーリングとアラート連携
  - kill_switch：条件を満たすと `data/kill.flag` を書き込み、Execution 停止シグナルを送出

- 研究 / 分析
  - factor_research：モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB）
  - feature_exploration：将来リターン、IC、統計サマリ等

- AI
  - news_nlp：ニュース記事を集約して OpenAI（gpt-4o-mini）で銘柄ごとにセンチメント評価
  - regime_detector：ETF MA とマクロニュースから市場レジーム判定

- ツール
  - paper_verification_report：ペーパートレード DB から検証レポートを生成

- ユーティリティ
  - logging_setup：統一ログ設定（コンソール + 日次ローテートファイル）
  - process_priority：プロセス優先度／CPU affinity 設定ユーティリティ

---

## 前提 / 必要条件

- Python 3.9+（ソースは型注釈や pathlib 等を使用）
- 必要な Python パッケージ（代表例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定検証で YAML のパースを行う場合に推奨）
- SQLite（Python 標準ライブラリ sqlite3 で使用）
- kabuステーション / J-Quants 等外部 API の利用には各種認証情報が必要

（依存関係はプロジェクト配布物に requirements.txt があればそちらを参照してください）

---

## 環境変数（代表的なもの）

必須（運用時）：
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意/設定項目（デフォルト値は括弧内）：
- KABUSYS_ENV (development | paper_trading | live) — (development)
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db) — paper_trading モード用 DB
- LOG_LEVEL (INFO)
- OPENAI_API_KEY — AI 機能利用時に必要
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で使用、デフォルト 60）

ログディレクトリ:
- LOG_DIR（未指定時は logs/）

その他: LINE 通知用トークンや PID/flag のパスは Settings クラスで参照可能（デフォルト data 配下）

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. .env ファイル作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - あるいは .env.example を参照して .env を手動作成

5. 設定検証（任意／推奨）
   - python -m kabusys.validate_config
   - 重要な警告を FAIL 扱いにする場合は `--strict` を付ける

6. 必要ディレクトリ作成（自動で作られる場合もあるが事前に作成しておくと安全）
   - mkdir -p data logs

---

## 使い方（主要スクリプト & CLI）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB に書き込む（本番 DB と分離）
    - 起動時に `data/stop_requested.flag` があれば起動せず終了
    - 実行中に同フラグが作成されるとエンジン停止を試みる
    - 実行中は `data/execution.pid` に PID を書き込む（設定で変更可能）

- 監視ループ（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60）
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用（監視 DB を本番 DB と共用）
    - 監視ループは stop flag（data/stop_requested.flag）検出で終了
    - SystemMonitor / TradeMonitor / RiskMonitor を使って DB へログ書込み、Kill Switch の評価や Alert 通知を行う（AlertManager が設定されている場合）

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`

- AI 機能（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数か OPENAI_API_KEY 環境変数で指定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 実運用時の注意点 / 運用フロー

- 本番（KABUSYS_ENV=live）では kill_flag や KILL_FLAG_CLEAR_ON_START の設定に注意してください。設定ミスで自動的に Kill Switch をクリアすると危険です。
- monitoring は稼働監視・データ鮮度監視を行い、条件が揃うと `data/kill.flag` を作成して ExecutionEngine に停止シグナルを送ります（起動時に Execution 側がこのフラグの有無を確認）。
- ログはデフォルトで logs/ 以下に日次ローテートで保存されます。ログディレクトリの作成権限がないとファイル出力は無効化され、コンソールのみ出力になります。
- OpenAI 呼び出しはレート制限や一時エラーを考慮したリトライ実装がありますが、API キーやコストに注意してください。

---

## ディレクトリ構成（主要ファイル説明）

以下はソースルート `src/kabusys` を基にした概略です（抜粋）。

- kabusys/
  - __init__.py
    - パッケージ定義、バージョン情報
  - config.py
    - 環境変数読み込み・Settings クラス。自動 .env ロード機能を持つ
  - config_setup.py
    - .env 対話式ウィザード（CLI）
  - validate_config.py
    - 設定検証 CLI（必須環境変数や config/*.yaml の存在チェックなど）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（本番/ペーパー切替、PID/stop フラグ管理）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（Stream + TimedRotatingFile）
    - process_priority.py — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ永続化層（テーブル作成・CRUD ユーティリティ）
    - system_monitor.py — CPU/メモリ/Disk、データ鮮度、プロセス監視
    - trade_monitor.py — 注文ログ監視（滞留注文・約定異常等） ※（ソース中に存在）
    - risk_monitor.py — ドローダウン・ポジション上限制御
    - kill_switch.py — Kill Switch 実装（flag ファイル書き込み）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信管理。LINE 通知等と連携する想定）
  - execution/
    - execution_engine.py — ExecutionEngine 実装（注文ライフサイクル管理）
    - broker_factory.py — ブローカークライアント生成（本番 / モック切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注フロー関連
  - portfolio/
    - portfolio_builder.py — 候補選定、重み付け
    - position_sizing.py — 株数計算、aggregate cap 等
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ
  - ai/
    - news_nlp.py — ニュース集約 + OpenAI 呼び出しで銘柄別スコア生成
    - regime_detector.py — マクロ + ETF MA によるレジーム判定
  - data/ (ランタイムで作成される想定)
    - monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid など
  - logs/ (ログ出力先、デフォルト)

（注）この README はコードベースの要約です。詳細な API 使用法は individual モジュールの docstring / ソースを参照してください。

---

もし README に追記したい具体的な情報（例: requirements.txt の内容、CI 設定、デプロイ手順、Alert の実装例など）があれば教えてください。必要に応じてサンプル .env テンプレートや運用フローチャートも作成します。