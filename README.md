# KabuSys

日本株向けの自動売買 / 研究プラットフォーム（ミニマル実装）
バッチ実行・監視・ペーパートレード分離・AI を用いたニュース評価などのコンポーネントを備えています。

Version: 0.1.0

---

## 概要

KabuSys は日本株の自動売買・リサーチを目的とした Python ベースのシステムです。主要な機能は以下の通りです。

- ExecutionEngine：発注、リスク管理、オーダー管理の実行コンポーネント
- Monitoring：システム稼働状況、注文ログ、リスク指標のポーリング監視とアラート/Kill Switch
- Research：DuckDB を用いたファクター計算・特徴量解析
- Portfolio：候補選定、重み算出、ポジションサイズ計算、セクター制約
- AI：OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価・レジーム判定
- Tools：ペーパートレード検証レポート生成などの補助スクリプト
- 設定管理：.env の対話式ウィザードと起動前検証 CLI

設計上のポイント：
- Paper Trading（`KABUSYS_ENV=paper_trading`）は本番 DB と完全に分離（data/paper_trading.db）
- DB は DuckDB（分析用）と SQLite（監視 / 発注ログ用）を併用
- ロギングは統一的にセットアップされ、日次ローテーション（30日保持）
- AI 機能は OpenAI API キーが必要（環境変数 `OPENAI_API_KEY`）

---

## 主な機能一覧

- system_monitor: CPU / メモリ / ディスク / プロセス監視、データ鮮度チェック
- trade_monitor: 発注ログの整合性・滞留注文や異常約定検出（trade_logs）
- risk_monitor: ドローダウン監視・ポジション上限監視・ダッシュボード更新
- kill_switch: 条件に応じて `data/kill.flag` を書き込み ExecutionEngine 停止
- ExecutionEngine: ブローカー抽象化、リスク管理、オーダーの送信/照合/再突合
- Portfolio construction: 候補選定、等重・スコア重み、リスクベースの株数算出
- Research: モメンタム / ボラティリティ / バリューのファクター計算、IC、統計要約
- AI: ニュースをまとめて LLM に投げるセンチメント集約（ai_scores）・レジーム判定（market_regime）
- ユーティリティ: .env ウィザード、設定検証、Paper Trading レポート生成

---

## 必要条件（概略）

- Python 3.10+
- 必要なパッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML を解析する場合）
- SQLite（組み込み、追加インストール不要）
- ネットワーク接続（本番ブローカー/API、OpenAI を使う場合）

（実際の requirements.txt はリポジトリに合わせて用意してください）

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン / 展開
   - 例: git clone <repo>

2. 仮想環境の作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. 環境変数（.env）を作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を作成
     - 重要な変数（例）:
       - JQUANTS_REFRESH_TOKEN（必須）
       - KABU_API_PASSWORD（必須）
       - KABUSYS_ENV（development / paper_trading / live、デフォルト `development`）
       - OPENAI_API_KEY（AI 機能を使う場合）
       - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
       - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
       - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
       - LOG_LEVEL（デフォルト: INFO）

5. 設定検証
   - python -m kabusys.validate_config
   - 実行結果でエラー/警告を確認し、必要に応じて .env を修正
   - `--strict` を付けると警告も失敗扱い（exit 1）

---

## 使い方（起動 / 各種コマンド）

- ExecutionEngine（実行エンジン）を起動
  - python -m kabusys.run_execution
  - 注意:
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使い paper_trading DB（data/paper_trading.db）に記録
    - 起動時に `data/stop_requested.flag` があれば起動せず終了
    - 実行中は `data/execution.pid` が作成される

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - 監視は本番 sqlite_path を環境にかかわらず使用（監視テーブルを永続化）

- .env の作成（ウィザード）
  - python -m kabusys.config_setup

- 設定の事前検証（CLI）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --db <path> --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`

- AI（ニュース評価 / レジーム判定）
  - OpenAI API キー（`OPENAI_API_KEY`）が必要
  - ニュース評価関数: kabusys.ai.score_news（内部で DuckDB 接続と日付を渡して使用）
  - レジーム判定関数: kabusys.ai.regime_detector.score_regime

---

## 主要な環境変数（抜粋）

- 必須 / 重要:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 認証（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
  - KABUSYS_ENV — 実行環境（development / paper_trading / live）
  - OPENAI_API_KEY — OpenAI を使う場合（AI 機能）

- データ / ログ:
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパー用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - LOG_DIR — ログディレクトリ（デフォルト: logs/）

- モニタリング:
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
  - PID_FILE_PATH — ExecutionEngine の pid ファイルパス（デフォルト: data/execution.pid）

- Paper Trading:
  - PAPER_FILL_MODE — MockBrokerClient の約定モード（instant|partial|never|reject）

注意: 設定ロードは自動で `.env` / `.env.local` を読み込みます（環境変数優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## ファイルフラグ / PID / Kill Switch の説明

- data/stop_requested.flag
  - run_execution / run_monitoring のシャットダウン操作（外部よりフラグを書けばループは停止）

- data/kill.flag
  - KillSwitch によって書き込まれるファイル。ExecutionEngine の即時停止を意図する（管理者が検出・処理）

- data/execution.pid
  - ExecutionEngine が実行中の PID を保存するファイル

---

## ログ・DB の取り扱い

- ログ:
  - デフォルトログディレクトリ: logs/
  - 日次ローテーション（TimedRotatingFileHandler）、30日分保持
  - コンソール出力は stdout に書かれます（cron 等で収集しやすい）

- DB:
  - DuckDB: 分析用（prices_daily, raw_financials, など）
  - SQLite: 監視 / 発注ログ（monitoring.db や paper_trading.db）
  - monitoring_db.init は必要なテーブルを冪等的に作成し、簡単なマイグレーションも行います（カラム追加等）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — .env 読み込み・Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - execution/ (発注関連)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, ...
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, alert_manager.py, monitoring_engine.py
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py, __init__.py
  - research/
    - factor_research.py, feature_exploration.py, __init__.py
  - ai/
    - news_nlp.py — ニュースを LLM で評価して ai_scores に保存
    - regime_detector.py — マーケットレジーム判定（MA200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレードの性能検証レポート生成

（上記は主要ファイルの抜粋です。実際の詳細はソースツリーを参照してください）

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では設定と .env の値を慎重に管理してください。`validate_config` は live 用の追加警告を出します。
- Kill Switch（kill.flag）は本番での非常停止用に重要です。`KILL_FLAG_CLEAR_ON_START=1` の設定は本番では危険です（自動クリアにより Kill Switch が無効化される可能性）。
- process priority の設定は psutil を用いて行います。権限不足で設定できない場合は警告ログが出ますが処理自体は継続します。
- Paper Trading は本番 DB と分離されています。検証やバックテストでは paper_trading 環境を活用してください。
- AI API（OpenAI）呼び出しはレート制限や一時エラーに対してリトライやフォールバック処理が入っていますが、APIキーやコストに注意してください。

---

## 開発・テスト

- 各モジュールは純粋関数 / 明確なインターフェースで実装されており、ユニットテストを作成しやすい構造です（DuckDB 接続や OpenAI 呼び出しは差し替え可能）。
- AI 関連の外部呼び出しはテスト時にモックすることを推奨します（ソース内に patch 可能なラップ関数あり）。

---

以上がこのコードベースの概要と初期セットアップ / 使用方法です。個別の詳細（ExecutionEngine のパラメータ、戦略ロジック、ブローカ実装など）はソース内の docstring / コメントを参照してください。