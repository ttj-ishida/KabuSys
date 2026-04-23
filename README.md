# KabuSys

日本株自動売買システムの軽量モジュール群（ライブラリ＋実行スクリプト群）

このリポジトリは、取引実行・監視・ポートフォリオ構築・リサーチ・AI を含む
自動売買システムのコア部分を収めています。実行スクリプトや対話式設定ウィザードを備え、
開発 / ペーパートレード / 本番（live）を切り替えて使えます。

バージョン: 0.1.0

---

## 概要

主な目的は次の通りです。

- ExecutionEngine（発注エンジン）とその周辺（OrderManager、RiskManager、Reconciler 等）の実装（起動スクリプト: run_execution.py）
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor）をポーリングする監視プロセス（起動スクリプト: run_monitoring.py）
- ポートフォリオ構築（候補選定、重み計算、株数決定、セクター制約等）の純関数群
- リサーチ用ファクター計算・特徴量解析（DuckDB を用いる）
- ニュースを LLM でスコアリングする AI モジュール（OpenAI）
- 各種ユーティリティ（ロギング設定、プロセス優先度、設定ウィザード、設定検証）
- ペーパートレード検証レポート生成ツール

設計方針の一部:
- DuckDB / SQLite をデータストアに利用（分析用は DuckDB、監視・発注ログは SQLite）
- 本番 DB とペーパートレード DB を明確に分離（KABUSYS_ENV に依存）
- LLM 呼び出しはフェイルセーフで設計（失敗してもシステム全体は継続）

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動（KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用）
  - Paper Trading 用 DB（data/paper_trading.db）へ記録し、本番 DB と分離
  - プロセス優先度の自動設定、PID ファイル管理、停止フラグ検出

- run_monitoring.py
  - SystemMonitor（CPU/メモリ/ディスク/プロセス生存）を定期ポーリングして記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - monitoring は常に本番 sqlite_path を使用して監視ログを蓄積

- monitoring.*
  - system_status, trade_logs, positions, risk_logs, dashboard 等を管理する MonitoringDB（SQLite）
  - RiskMonitor、KillSwitch、MonitoringEngine、AlertManager（通知は AlertManager 実装次第）

- portfolio.*
  - 銘柄選定（select_candidates）、重み計算（等重・スコア加重）
  - セクター上限適用、レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ決定（risk_based / equal / score、単元丸め、aggregate cap）

- research.*
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- ai.*
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのスコアを ai_scores に書き込む
  - regime_detector: ETF MA 乖離 + マクロセンチメントで日次レジーム判定を作成

- tools.paper_verification_report
  - ペーパートレード DB を解析して検証レポート（稼働率、注文成功率、レイテンシ等）を出力

- 設定関連
  - config_setup.py: 対話式で .env を生成／更新するウィザード
  - validate_config.py: 起動前の設定検証 CLI

---

## 前提・依存（概略）

必要な Python ライブラリ（主要）:
- duckdb
- psutil
- openai（AI 機能を使う場合）
- sqlite3（標準）
- ロギング・ファイルハンドラは標準 logging を使用

※ 実環境では requirements.txt / pyproject.toml に依存関係を明示してインストールしてください。

---

## セットアップ手順

1. リポジトリを取得し、仮想環境を作成して有効化する
   - 例:
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows

2. 依存関係をインストール
   - 例（pip）:
     pip install duckdb psutil openai

   - 実際はプロジェクトの requirements.txt / pyproject.toml に従ってください。

3. 環境変数を設定
   - 対話式ウィザードで .env を生成することを推奨:
     python -m kabusys.config_setup

   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）

   - 主要なオプション（デフォルトを含む）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - LOG_DIR: logs/
     - OPENAI_API_KEY: （AI 機能を使うなら必須）

   - 自動ロード:
     - プロジェクトルートの .env / .env.local は自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

4. データディレクトリ作成（必要に応じて）
   - data/ と logs/ は起動時に自動作成されることが多いですが、権限等で問題がある場合手動で作成してください。

---

## 使い方（主要コマンド）

- 設定ウィザード（.env 生成）
  python -m kabusys.config_setup

- 設定検証（.env と config/*.yaml の基本チェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も失敗扱い

- ExecutionEngine 起動（取引エンジン）
  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中に data/stop_requested.flag が作成されるとエンジンが停止します。
  - PID ファイル: data/execution.pid

- Monitoring 起動（監視プロセス）
  python -m kabusys.run_monitoring

  挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60）。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を参照して監視ログを記録。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を優先的に使う。

- AI 関連（プログラム API）
  - ニューススコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  ※ これらはライブラリ関数として呼び出す想定です。CLI は提供されていない（今後追加可）。

---

## ログとファイル

- ログ:
  - デフォルト出力先: stdout および logs/<app_name>.log（日次ローテート、30日保持）
  - app_name 例: execution, monitoring
  - LOG_DIR 環境変数で変更可能

- データベース:
  - DuckDB: data/kabusys.duckdb（分析用）
  - SQLite (監視): data/monitoring.db
  - SQLite (paper trading): data/paper_trading.db（KABUSYS_ENV=paper_trading 時）

- フラグ / PID:
  - 停止要求フラグ: data/stop_requested.flag（run_execution/run_monitoring が監視）
  - Kill Switch: data/kill.flag（KillSwitch が書き込み、ExecutionEngine に停止シグナルを送る）
  - PID: data/execution.pid

---

## 注意点 / オペレーション上のヒント

- 環境切り替え:
  - KABUSYS_ENV によって動作が変わります。特に `paper_trading` は本番 DB と分離されるため、試験に便利です。`live` は本番モードなので設定ミスに注意してください。

- 自動読み込み:
  - プロジェクトルートの .env / .env.local は自動で読み込まれます。OS 環境変数は上書きされません。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。

- OpenAI（AI 機能）:
  - OPENAI_API_KEY が必要。API 呼び出しはリトライとフェイルセーフ設計になっていますが、API 料金に注意してください。
  - news_nlp と regime_detector は JSON mode を使い厳密な JSON 出力を期待しています。API レスポンス検証とクリッピング処理があります。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は起動時にテーブル作成と簡単なカラム追加（マイグレーション）を行います。運用開始後に手動でのスキーマ変更を行う場合は注意してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定アクセス
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity

- monitoring/
  - monitoring_db.py       — SQLite 永続化層
  - system_monitor.py      — システム / データ鮮度監視
  - trade_monitor.py       — （取引監視: 滞留注文等）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag 管理
  - monitoring_engine.py   — 複数モニタの統合ポーリング
  - alert_manager.py       — 通知管理（実装により外部通知）

- execution/
  - broker_factory.py      — ブローカークライアント生成
  - execution_engine.py    — 実行エンジン本体
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

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

- tools/
  - paper_verification_report.py

（上記は主要ファイルの抜粋です。実際のリポジトリにはさらに細かなモジュールやサポートコードが含まれます。）

---

## テスト実行・開発時のヒント

- ローカルでのペーパートレード検証は KABUSYS_ENV=paper_trading を指定して run_execution を起動すると良いです。
- まずは python -m kabusys.validate_config で設定チェックを行ってください。
- ロギングは setup_logging() で統一されているため、起動スクリプトから必ず呼び出してください（run_* スクリプトは実行時に呼んでいます）。
- DuckDB を直接操作してデータを確認したい場合は duckdb の CLI／Python API を使って data/kabusys.duckdb を参照してください。

---

## ライセンス・貢献

本 README はコードベースの概要・使い方を示すもので、実運用にあたってはさらに詳細な運用ドキュメント（稼働手順、監視アラート設計、バックアップ方針、セキュリティ・シークレット管理）を整備してください。

貢献は PR・Issue を歓迎します。重要な変更（特に取引ロジック・リスク管理）についてはコードレビューを厳密に行ってください。

---

何か特定のセクション（例えば ExecutionEngine の API、監視アラートの実装方法、AI モジュールのテスト方法など）を詳しく追記したい場合は教えてください。追加で具体的なコマンド例やテンプレートを用意します。