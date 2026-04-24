# KabuSys

日本株向けの自動売買・リサーチ基盤（ミニマム実装）。  
このリポジトリは、発注実行エンジン、監視（Monitoring）周りのユーティリティ、ポートフォリオ構築・ポジション算出、ファクター計算、LLM を使ったニュースセンチメント評価などのモジュール群を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次の目的を想定したコンポーネント群を提供します。

- 実際の発注実行（ExecutionEngine）とペーパートレードモードの切替
- 稼働監視・リスク監視・滞留注文検出・Kill Switch（停止フラグ）による自動停止
- ポートフォリオ構築（候補選定／重み算出／ポジションサイジング）
- ファクター計算（モメンタム／バリュー／ボラティリティ）や研究用の統計処理
- OpenAI を用いたニュースセンチメント・レジーム判定（AI モジュール）
- 各種 CLI（環境設定ウィザード、設定検証、ペーパートレード検証レポート生成）

設計方針として、DB（DuckDB / SQLite）や外部 API へのアクセスは明示的に分離し、ルックアヘッドバイアスに配慮した実装が行われています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動（本番 / paper_trading 切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で調整可）
- 設定関連
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — .env と config/*.yaml の検証 CLI
  - Settings クラス（kabusys.config）で環境変数を一元管理
- 監視（monitoring）
  - MonitoringEngine：各種 Monitor（System / Trade / Risk）を束ねる
  - SystemMonitor：プロセス・CPU/メモリ/ディスク・データ鮮度を監視
  - TradeMonitor / RiskMonitor：注文・ドローダウン・ポジション上限などの監視
  - KillSwitch：条件により data/kill.flag を作成して ExecutionEngine を停止
  - MonitoringDB：SQLite ベースの永続化層（schema の初期化とマイグレーション対応）
- 実行（execution）
  - ブローカーファクトリ（実ブローカ／MockBroker の切替）
  - OrderManager / OrderRepository / RiskManager / Reconciler / ExecutionEngine（発注ロジック）
  - paper_trading 時は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離
- ポートフォリオ（portfolio）
  - 候補選定（select_candidates）、等重/スコア重み算出
  - ポジションサイジング（lot の丸め、aggregate cap、risk_based 等）
  - セクター上限適用・レジーム乗数
- 研究（research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（ai）
  - news_nlp.score_news：OpenAI（gpt-4o-mini）でニュースをスコアリングし ai_scores に書き込み
  - regime_detector.score_regime：ETF の MA とマクロニュースを組み合わせて市場レジームを判定
- ツール
  - tools.paper_verification_report：ペーパートレード DB に対する検証レポート生成

---

## セットアップ手順（開発 / ローカル実行向け）

推奨: Python 3.10 以上。仮想環境を作成してから進めてください。

1. リポジトリをクローン／展開
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - 主要パッケージ（例）:
     - pip install duckdb psutil openai
     - PyYAML を使う場合: pip install pyyaml
   ※ requirements.txt がある場合はそれを利用してください（本リポジトリ例では省略）。
4. 初期設定ファイル（.env）を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を元に作成して .env をプロジェクトルートに置く
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）
6. データディレクトリ
   - デフォルトの DB / pid / flag ファイルは project_root/data に置かれます。権限を確認してください。
7. OpenAI を使う機能を実行する場合は環境変数 OPENAI_API_KEY を設定

重要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV = development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番通知用、任意）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリア、開発時のみ 1 を推奨）
- PAPER_FILL_MODE（paper_trading の MockBroker の fill 動作: instant | partial | never | reject）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト 60）

---

## 使い方

基本的な起動例を示します（プロジェクトルートで実行）。

- 環境ファイルの作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密チェック: python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - 本番／開発モード: KABUSYS_ENV に応じて挙動が変わります
  - python -m kabusys.run_execution
  - ペーパートレード（mock broker を使用）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 実行時の PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）
  - 停止: data/stop_requested.flag を作成すると起動中のプロセスが検知して終了

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更: MONITOR_POLL_INTERVAL を秒数で指定（例: 30）
    - export MONITOR_POLL_INTERVAL=30
  - 監視は常に本番 sqlite_path を使用（Settings 設計）

- Kill Switch
  - KillSwitch は監視結果に応じて data/kill.flag を書き込みます。ExecutionEngine は起動時・監視ループ等でこれを検知して停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアされますが、本番では 0 を推奨します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で上書き可）

- AI 機能（ニューススコアリング / レジーム判定）
  - プログラムから呼び出す例:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="sk-...")
  - 実行には OPENAI_API_KEY の設定が必要

ログ出力:
- デフォルトで logs/<app_name>.log に日次ローテーションで出力（logs ディレクトリを作成）
- setup_logging によりコンソール stdout とファイル両方に出力

注意:
- paper_trading モードは専用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録し、本番 DB と完全分離されます。
- DB スキーマの初期化やマイグレーションは monitoring_db.init_monitoring_db にて行われます（冪等）。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py — Settings クラス（環境変数読み込み・自動 .env ロード）
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ（主なもの）
- monitoring/
  - monitoring_db.py — SQLite schema 初期化 + MonitoringDB クラス
  - system_monitor.py — システム監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - trade_monitor.py — （滞留注文などの監視、ソース内に実装あり）
  - monitoring_engine.py — 各 Monitor を束ねる
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — 通知管理（実装参照）
- execution/
  - execution_engine.py — 実行エンジン本体
  - broker_factory.py — ブローカークライアント生成（Mock / 実装切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py
- portfolio/
  - portfolio_builder.py — 候補選定・重み算出
  - position_sizing.py — 株数計算・aggregate cap ロジック
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum, volatility, value）
  - feature_exploration.py — 将来リターン・IC 計算 等
- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI 呼び出し・バッチ処理）
  - regime_detector.py — レジーム判定（MA + マクロニュース + LLM）
- data/（実行時に使用）
  - monitoring.db（default SQLITE_PATH）
  - kabusys.duckdb（default DUCKDB_PATH）
  - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - execution.pid / stop_requested.flag / kill.flag など

ユーティリティ
- utils/logging_setup.py — 統一的なロギング設定
- utils/process_priority.py — プロセス優先度 / CPU affinity

ツール
- tools/paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

---

## 運用上の注意点

- 本番運用時は KABUSYS_ENV=live を設定し、LINE 通知／ログレベル等を慎重に確認してください（validate_config で注意喚起あり）。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番で危険なため推奨されません。
- OpenAI API の利用はキーの管理とコストに注意してください。API 呼び出しはリトライとフェイルセーフを備えていますが、失敗時は安全側のフォールバック（スコア 0 等）を行います。
- DuckDB / SQLite のファイルパスは Settings にてカスタマイズ可能です。バックアップ・監視を検討してください。
- process priority / cpu affinity は OS 権限により失敗することがあります（警告ログを出してスキップ）。

---

## 開発にあたって

- コードはモジュール単位で分かれており、関数は可能な限り副作用を避ける純粋関数設計が多く採用されています（ポートフォリオ・リサーチ等）。
- テスト用に依存注入や外部呼び出しをモックしやすい設計（OpenAI 呼び出し関数は差し替え可能）になっています。

---

必要であれば README を英語版や簡略版に編集したり、運用手順（systemd ユニット / supervisor / Docker イメージ化）を追加で記載できます。どの形式のドキュメントが欲しいか教えてください。