# KabuSys — README (日本語)

本ドキュメントはリポジトリ内のコードベースに基づく README です。日本株自動売買システム「KabuSys」の内部ツール群（ExecutionEngine / Monitoring / Research / Portfolio / AI / Tools）を簡潔にまとめ、セットアップと使い方の手順を示します。

---

## プロジェクト概要

KabuSys は日本株の自動売買・検証を支援するモジュール群です。主な機能は以下の通りです：

- ExecutionEngine: 発注ロジック・注文管理・リスク管理を担う実行エンジン（paper/live 切替可）。
- Monitoring: システム状態、注文／約定、リスク（ドローダウン・ポジション上限）を監視し、必要時に Kill Switch を発動。
- Portfolio construction: 候補選定、配分計算、ポジションサイズ計算やセクター制限。
- Research: ファクター計算（モメンタム、バリュー、ボラティリティ）・特徴量解析（IC など）。
- AI ツール: ニュースの NLP スコアリング（OpenAI）や市場レジーム判定。
- Tools: ペーパートレード集計・検証レポート生成などの補助ツール。
- 設定ユーティリティ: .env の対話式生成、設定検証 CLI。

主要な永続化は DuckDB（分析） と SQLite（監視・注文ログ）を使用します。

---

## 機能一覧（抜粋）

- Execution
  - paper_trading モード時は MockBrokerClient を使用し、paper_trading 用 SQLite に記録（本番 DB と分離）。
  - リスク管理（最大ポジション比率、利用率、ドローダウンなど）。
  - 発注履歴の永続化（SQLite の trade_logs 等）。
- Monitoring
  - CPU / メモリ / ディスク監視、プロセス生存チェック、データ鮮度チェック。
  - リスク監視（ドローダウン、ポジション数超過） → 必要時に kill.flag を作成。
  - アラート／ログ出力（LINE 等への通知は設定に依存）。
- Portfolio
  - 候補選定（スコア順）、等金額/スコア加重配分、リスクベース発注量計算。
  - セクター上限適用、レジームに応じた乗数計算。
- Research
  - DuckDB 上でのファクター計算（mom、value、volatility）や forward returns / IC 計算。
- AI
  - OpenAI を用いたニュースセンチメント評価（ai_scores テーブルへ書き込み）。
  - マクロニュース＋ETF ma200 による市場レジーム判定（market_regime テーブルへ書込）。
- Utilities
  - 対話式 .env 作成ツール（kabusys.config_setup）。
  - 設定検証 CLI（kabusys.validate_config）。
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）。

---

## セットアップ手順（開発 / 実行前）

以下は一般的な手順です。実際はプロジェクトの requirements.txt やデプロイ手順に合わせて調整してください。

1. Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は最低でも psutil, duckdb, openai, sqlite3 が必要）

3. データディレクトリの準備（デフォルト）
   - data/（SQLite, pid, flag ファイル用）
   - logs/（ログファイル用）
   これらは多くのユーティリティで自動作成されますが、権限に注意してください。

4. 環境変数 / .env の準備
   - 推奨: 対話式ウィザードで .env を作成
     - python -m kabusys.config_setup
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API パスワード）
   - 主要なオプション（デフォルトを記載）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時）
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI を使う機能を動かす場合に必要
   - 自動ロード挙動
     - プロジェクトルート（.git または pyproject.toml を検出）から .env/.env.local を自動読み込みします。
     - 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗にしたいときは --strict を指定

---

## 使い方（主要コマンド）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番とは分離）。
    - 起動時に data/stop_requested.flag が存在すると起動を中止。
    - エンジンは別スレッドで run_session を実行し、stop_requested.flag を監視して停止可能。
    - プロセス優先度を high に設定するユーティリティを呼びます。

- 監視プロセス（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - SQLite（monitoring DB）に接続して監視テーブルを初期化。
    - SystemMonitor.check_once() をポーリング。デフォルト間隔は 60 秒。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（例: MONITOR_POLL_INTERVAL=30）。
    - 停止は data/stop_requested.flag の作成で行います。

- .env 対話式作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI スコアリング / レジーム判定（プログラム内 API）
  - ニューススコア: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を指定。

---

## 停止・Kill スイッチの仕組み

- stop_requested.flag
  - run_execution / run_monitoring が監視するファイル（data/stop_requested.flag）。
  - 存在すると監視ループや ExecutionEngine を安全に終了します（明示的停止用）。
- kill.flag（KillSwitch）
  - monitoring 内の条件（例: ドローダウン閾値超過、ポジション上限超過）で書き込まれるフラグ。
  - ExecutionEngine は起動時にこの flag を検出すると起動を中止し、実行中は kill.flag の存在で停止される仕様。
- PID ファイル
  - 実行時に data/execution.pid などを使用してプロセス PID を管理する実装があるため、運用時はこれらのファイルに注意。

---

## ログ出力

- logging_setup モジュールで統一的に設定されます。
  - コンソール stdout と logs/<app_name>.log（日次ローテーション、30日保持）に出力。
  - デフォルトログディレクトリ: logs/
  - LOG_LEVEL 環境変数でログレベルを制御可能。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意／推奨:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- OPENAI_API_KEY — AI 機能使用時に必要
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）、デフォルト 60
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（1で有効。liveでは危険）

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ初期化
  - config.py — 環境変数 / 設定管理（自動 .env 読み込み・Settings クラス）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — forward returns, IC, 統計サマリー
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB の初期化と読み書き API（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — (trade 関連の監視ロジック)
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - monitoring_engine.py — Monitor をまとめて運用する実行エンジン
    - kill_switch.py — kill.flag の生成・管理
    - alert_manager.py —（通知用ラッパー、LINE など）※抜粋コードにより実装がある想定
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - execution/（発注ロジック、OrderManager 等が含まれる想定）
  - data/（データパイプラインや DuckDB 接続用モジュールが含まれる想定）

（注）抜粋コードには trade_monitor.py の全文が含まれていない箇所がありますが、概念的なコンポーネントは上記の通りです。

---

## 運用上の注意・ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0 を推奨します。
- paper_trading モードは本番 DB と分離されます。Paper 用 DB と本番 DB のパス設定を必ず確認してください。
- OpenAI API を利用する機能は API 呼び出しに失敗するケースにフェイルセーフ設計（フォールバック）がありますが、API キーの保護とレート管理は運用で注意してください。
- ログディレクトリやデータディレクトリの書き込み権限を事前に確認してください。
- validate_config を利用して起動前の設定検証を行うことを推奨します。
- モジュールの多くは DB 接続（DuckDB, SQLite）を外部から渡す設計のため、テスト時はモック接続を渡して単体テストを行うと良いです。

---

## 参考コマンドまとめ

- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate
- 依存インストール
  - pip install -r requirements.txt
- .env 作成
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要に応じて README に追記します（例: 実際の requirements.txt、デプロイスクリプト、docker-compose、各コンポーネントの細かな設定例など）。追加情報や特定項目の詳細（例: ExecutionEngine の内部 API、OrderManager の振る舞い、trade_monitor の仕様）をご希望であれば教えてください。