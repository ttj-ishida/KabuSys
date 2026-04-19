# KabuSys

日本株向けの自動売買システム（プロトタイプ）。  
このリポジトリは、データ処理・ファクター計算・ポートフォリオ構築・発注エンジン・監視・AI（ニュース NLP / レジーム判定）などのコンポーネントをまとめたモジュール群を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。設計方針の要点は以下の通りです。

- データ蓄積・分析は DuckDB / SQLite を使用（DuckDB は分析、SQLite は監視・発注ログ）。
- 発注ロジックは実行環境に依存せず、paper_trading（モック）と live（実口座）を切り替え可能。
- 監視（Monitoring）コンポーネントでプロセス・データ鮮度・取引異常等をチェックし、必要に応じて停止フラグを立てる（Kill Switch）。
- ニュースのセンチメント解析や市場レジーム判定は OpenAI（gpt-4o-mini 等）を利用する設計（APIキー必須）。
- ログ出力やプロセス優先度設定などのユーティリティを標準化。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み / config 管理（`kabusys.config`）
  - 対話式設定ウィザード（`python -m kabusys.config_setup`）
  - 設定検証 CLI（`python -m kabusys.validate_config`）

- 実行エンジン
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
  - Paper trading と Live を切替可能（`KABUSYS_ENV`）

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 単独起動スクリプト（`run_monitoring.py`）
  - SQLite に監視ログ・トレードログを永続化（`monitoring_db.py`）
  - Kill Switch（`data/kill.flag`）による強制停止機構

- ポートフォリオ構築
  - 銘柄選定、重み計算、ポジションサイズ計算（等配分・スコア加重・リスクベース）
  - セクターキャップ・レジーム乗数適用

- 研究 / 分析
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算・IC（Information Coefficient）計算
  - DuckDB を使ったデータ処理を想定

- AI（OpenAI）
  - ニュース NLP による銘柄センチメント（`kabusys.ai.news_nlp.score_news`）
  - マクロ記事 + ETF MA による市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）

- ツール
  - ペーパートレード検証レポート生成（`kabusys.tools.paper_verification_report`）

- ユーティリティ
  - ロギングセットアップ（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

前提: Python 3.9+ を想定（duckdb / psutil / openai 等が必要）。

1. リポジトリをクローン
   - git clone <repository-url>
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. インストール（pip）
   - pip install -e .   # パッケージとしてインストールできる場合
   - 必要なパッケージ（主なもの）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証時に推奨）
   - 例: pip install duckdb psutil openai pyyaml
4. ディレクトリ作成（必要に応じて）
   - mkdir -p data logs
5. .env を作成
   - 対話式で作成: python -m kabusys.config_setup
   - もしくは手動で data/default を基準に .env を作成
   - 最小必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_kabu_password
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=sk-...  (AI を使う場合)
   - 参考: config_setup が生成する .env フォーマットに従ってください。

注意:
- `run_execution` は `KABUSYS_ENV=paper_trading` の場合、専用の paper trading DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離します。
- `run_monitoring` は監視 DB に常に本番の sqlite_path（Settings.sqlite_path）を使用します（環境に関係なく）。

---

## 使い方（主要コマンド・実行例）

基本的に各起動スクリプトはモジュールとして実行します。

- 設定ウィザード（.env の生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作:
    - プロセス優先度を high に設定
    - DB に接続（paper_trading の場合は paper_trading DB を使用）
    - ブローカークライアントを生成（実 / モックを切り替え）
    - ExecutionEngine をスレッドで実行
    - 停止は data/stop_requested.flag を作成することで検知

- 監視プロセス起動（Monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 動作:
    - process priority を high に設定
    - SystemMonitor.check_once() を定期実行し、monitoring DB にログを残す
    - data/stop_requested.flag を検知するとループを終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 引数 --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI 関連（プログラム呼び出し例）
  - ニュース NLP スコア生成（DB 接続済みの duckdb_conn を渡す）
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を指定しない場合は OPENAI_API_KEY を参照
  - レジーム判定
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

ログ:
- デフォルトで stdout とファイル（logs/<app_name>.log）に出力されます。ログディレクトリは LOG_DIR 環境変数で上書き可能。

停止・Kill Switch:
- Kill Switch は monitoring 側で条件を満たすと data/kill.flag に理由を書き込みます。ExecutionEngine は起動時にそのフラグを検査します。
- Kill Flag を自動クリアする挙動は KILL_FLAG_CLEAR_ON_START 環境変数で制御（0=クリアしない（推奨）, 1=自動クリア）。

注意事項:
- OpenAI を使う機能は API キー（OPENAI_API_KEY）を必須とします。API 呼び出しでの失敗はリトライやフォールバックを行い、致命的失敗は起こさない設計ですが、API キー未設定時は例外になります。

---

## ディレクトリ構成

主要なファイル / モジュールツリー（src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（自動 .env ロード含む）
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py       — 市場レジーム判定（ETF + マクロ NLP）
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB 層（テーブル作成・CRUD）
    - monitoring_engine.py    — 各 Monitor の統合（ポーリング）
    - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py        — （省略列）取引監視ロジック
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — Kill Switch 実装（flag ファイル）
    - alert_manager.py        — （省略列）通知管理（LINE 等）
  - execution/
    - (発注エンジン関連モジュール: EngineConfig, ExecutionEngine, OrderManager, Reconciler, RiskManager, BrokerFactory, OrderRepository 等)
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・上限・丸め処理
    - risk_adjustment.py      — セクター上限・レジーム乗数等
    - __init__.py
  - research/
    - factor_research.py      — momentum / volatility / value 計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
    - __init__.py
  - utils/
    - logging_setup.py        — 統一ロギング設定（stdout + 日次ファイル）
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - __init__.py
  - data/                      — 実行時に使用するファイル群（例: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid 等）※リポジトリ外で作成

補足:
- 実際の発注やブローカークライアント実装、TradeMonitor/AlertManager の詳細は該当モジュール内にある想定の実装に従います（本 README は主要ワークフローと使い方をまとめたものです）。

---

## よくある質問 / トラブルシュート

- DB ファイルや logs ディレクトリへの書き込み権限がない:
  - 実行ユーザに書き込み権限を付与してください（data/ と logs/ を作成）。
- OpenAI 関連で KeyError / 認証エラーが出る:
  - OPENAI_API_KEY を正しく設定しているか確認してください。ローカルでは .env に設定するか環境変数で渡します。
- run_execution を起動したがすぐ終了する:
  - data/stop_requested.flag が存在していないか確認してください（存在すると起動をスキップします）。
- 設定検証でエラーが出る:
  - `.env.example` を参考に .env を作成し、`python -m kabusys.validate_config` で確認してください。`--strict` を付けると警告もエラーとして扱います。

---

必要であれば、README に追加する内容（詳細な設定項目説明、config/*.yaml のフォーマット、API レスポンス仕様、Unit Test 実行方法、CI 設定など）を指定してください。