# KabuSys

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。戦略のバックテスト／リサーチ、ポートフォリオ構築、発注エンジン（本番 / ペーパートレード分離）、監視・アラート、LLM を利用したニュース分析などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

主な設計方針・特徴：

- モジュール化されたコンポーネント（execution, monitoring, portfolio, research, ai, tools 等）。
- ペーパートレードと本番（live）を明確に分離（専用 SQLite DB 等）。
- DuckDB を分析用 DB、SQLite を監視／発注ログ用 DB に利用。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価およびレジーム判定をサポート（API キー必要）。
- 監視用コンポーネントは Kill Switch（flag ファイル）で ExecutionEngine を停止可能。
- ログはコンソールおよび日次ローテーションファイルに出力（`logs/`、デフォルト）。

---

## 主な機能一覧

- ExecutionEngine（実際の発注処理／ペーパートレード対応）
- Monitoring（SystemMonitor, TradeMonitor, RiskMonitor 等）
- Kill Switch（ドローダウンやポジション上限で発動する停止機構）
- Portfolio Construction（候補選定、重み計算、ポジションサイズ計算、セクター制限等）
- Research（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI モジュール
  - news_nlp: ニュースを LLM でスコアリングし ai_scores テーブルへ保存
  - regime_detector: マクロ + ETF MA を組み合わせて市場レジーム判定
- サポートツール
  - 設定ウィザード（.env の対話式生成）
  - 設定検証 CLI（.env / config/*.yaml の事前チェック）
  - Paper Trading 検証レポート出力ツール

---

## 必要要件（例）

- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使用する場合)
- PyYAML（config/*.yaml の検証を行う場合に推奨）

依存パッケージはプロジェクト配布に requirements.txt がある想定でインストールしてください（プロジェクトに未付属の場合は上記パッケージを個別に導入）。

---

## セットアップ手順

1. リポジトリをクローン、またはプロジェクト配布を取得。

2. 仮想環境を作成して有効化（例）:
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール:
   - pip install duckdb psutil openai
   - PyYAML が必要なら pip install pyyaml

4. 環境変数設定:
   - プロジェクトルートに `.env` を作成するか、以下のコマンドで対話式ウィザードを実行します:
     - python -m kabusys.config_setup
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — 必須
     - KABU_API_PASSWORD — 必須
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading の場合）
     - OPENAI_API_KEY — AI 機能利用時に必要
     - LOG_LEVEL, LOG_DIR 等

   - 自動 .env 読み込みの挙動:
     - OS 環境変数 > .env.local > .env の優先順位でロードされます。
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. （任意）設定検証:
   - python -m kabusys.validate_config
   - `--strict` を付けると警告も失敗扱いになります。

6. データディレクトリ作成（例）:
   - mkdir -p data logs

---

## 実行方法（代表的なコマンド）

- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在するとエンジンは起動しません。
    - エンジンは PID ファイル（デフォルト: data/execution.pid）を管理します。
    - 停止させるには data/stop_requested.flag を作成するか、ExecutionEngine 側の停止 API を利用します。

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - 補足:
    - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、1 以上）。
    - 監視は本番 sqlite_path を環境にかかわらず使用します（監視ログは共有 DB）。
    - 監視ループを停止するにはプロセスに SIGINT（Ctrl+C）またはプロジェクトルート/data/stop_requested.flag を作成。

- 設定ウィザード（.env 作成）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート出力:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能（デフォルト: data/paper_trading.db）

- AI 関連（コード内 API）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を使用。

---

## 主要設定とフラグ

- KABUSYS_ENV:
  - development / paper_trading / live のいずれか。
  - paper_trading: 発注はモック、専用 DB を使用。
  - live: 実際の発注を行うため注意が必要。

- MONITOR_POLL_INTERVAL:
  - 監視ポーリング間隔（秒）。run_monitoring が参照。1 以上の整数。

- Kill Switch / stop flag:
  - Kill Switch は条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止指示を送る仕組み（監視側で評価される）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動消去する（本番では 0 推奨）。

- Stop requested:
  - run_execution / run_monitoring は `data/stop_requested.flag` を監視して外部停止シグナルを受け取る。

- Logging:
  - デフォルト出力先: stdout + 日次ローテーションファイル（logs/<app_name>.log）。
  - 環境変数 LOG_LEVEL, LOG_DIR で制御。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite のスキーマ初期化・永続化ラッパー
    - system_monitor.py — システム状態 / データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 Monitor を組み合わせた実行ループ
    - (その他: trade_monitor, alert_manager 等が参照される)
  - execution/ (発注関連コンポーネント - BrokerFactory, Engine, OrderManager など)
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメント取得と ai_scores 書き込み
    - regime_detector.py — マクロ + MA を用いた市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - data/ （ランタイム生成）
    - monitoring.db (デフォルト SQLite)
    - paper_trading.db (ペーパートレード用 DB)
    - execution.pid, kill.flag, stop_requested.flag などの制御ファイル

---

## 注意事項 / 運用上のヒント

- 本番モード（KABUSYS_ENV=live）での起動前に `python -m kabusys.validate_config` で設定確認を強く推奨します。
- .env は機密情報（API トークン等）を含むため絶対に Git にコミットしないでください。
- OpenAI を利用する機能は外部 API へのリクエストが発生します。API 利用料とレート制限に注意してください。
- 監視・Execution 両方が同じ SQLite を参照する場合、同時アクセスによるロックに注意（設計上は別ファイルに分けることを推奨）。
- ローカル開発では KABUSYS_ENV=development を使用すると発注を抑止するなど安全措置が入る想定です（コード内で制御）。

---

## 開発・テスト

- 各モジュールは純粋関数（portfolio, research 等）と副作用を持つコンポーネント（db 書込み、API call）に分かれており、ユニットテストが書きやすい構造です。AI コールや外部依存はモック化してテストしてください。
- config の自動ロードはプロジェクトルートの特定（.git または pyproject.toml）に依存します。配布後は環境に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することを検討してください。

---

README は以上です。必要であれば以下を提供します：
- 例 .env.example（サンプルのキー/値）
- systemd / supervisor 用の起動スクリプト例
- 開発時のユニットテスト例や CI 設定案

どれを追加しましょうか？