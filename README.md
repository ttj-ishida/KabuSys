# KabuSys

日本株自動売買システムのライブラリ / 実行スクリプト群

このリポジトリは、信号生成・ポートフォリオ構築・発注エンジン・監視・AI ベースのニュース解析などを含む自動売買基盤の一部実装です。DuckDB / SQLite をデータ層として利用します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 動作要件 / 依存関係
- セットアップ手順
- 使い方（主要コマンド例）
- 実行時の環境変数（主なもの）
- 停止・Kill スイッチについて
- ディレクトリ構成（主要ファイル）
- 補足・注意事項

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームを構築するためのモジュール群です。  
主要な役割は次の通りです。

- 市場データ（DuckDB の prices_daily 等）を使ったファクター計算・リサーチ
- ポートフォリオ選定・配分・株数算出（等配分 / スコア加重 / リスクベース等）
- ExecutionEngine（発注エンジン） — 実際のブローカー呼び出しまたはペーパートレード
- 監視（MonitoringEngine） — システム/発注/リスク監視、アラート、Kill Switch
- AI モジュール — ニュースのセンチメント解析（OpenAI）や市場レジーム判定
- ツール類 — .env 設定ウィザード、構成検証、Paper Trading 検証レポート生成

---

## 機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、無効化可能）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行部
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
  - Monitoring 起動スクリプト（run_monitoring.py）
    - ポーリング間隔は MONITOR_POLL_INTERVAL でオーバーライド可能（デフォルト 60 秒）

- 監視（monitoring パッケージ）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存確認 / データ鮮度検査
  - TradeMonitor：発注ログの監視（滞留注文・約定異常など）※実装参照
  - RiskMonitor：ドローダウン・ポジション上限の監視とリスクログ記録
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringDB：SQLite による永続化（system_status, trade_logs, positions, risk_logs, dashboard）

- ポートフォリオ（portfolio パッケージ）
  - 候補選定（select_candidates）
  - 重み計算（等配分 / スコア加重）
  - セクターキャップ適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - 株数決定（calc_position_sizes） — lot サイズ丸め・集約キャップ処理あり

- リサーチ（research パッケージ）
  - ファクター計算：モメンタム / ボラティリティ / バリュー
  - 特徴量探索：将来リターン、IC（Spearman）、統計サマリー

- AI（ai パッケージ）
  - news_nlp: OpenAI を用いたニュースセンチメント（ai_scores 書き込み）
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースを組み合わせたレジーム判定
  - OpenAI 呼び出しは retry/バックオフ・レスポンス検証を実装

- ツール
  - Paper Trading 検証レポート（tools.paper_verification_report）：ペーパートレード DB を集計して PASS/FAIL 判定

---

## 動作要件 / 依存関係

推奨 Python バージョン: 3.10+

主要依存パッケージ（最低限）
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）

インストール例:
- pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt がない場合は上記を直接インストールしてください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo_url>
   - cd <repo>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - pip install duckdb psutil openai pyyaml

4. .env を作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成します。必須項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は必ず設定してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 本番前は --strict を付けて警告も失敗扱いにできます:
     - python -m kabusys.validate_config --strict

6. データディレクトリ / DB
   - デフォルトの DB パスは
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - 起動スクリプトは必要に応じて DB を初期化します（monitoring のテーブル作成等）。ディレクトリは自動で作成されます。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（通常）
  - python -m kabusys.run_execution
  - 起動前に data/stop_requested.flag が存在すると起動しません（安全措置）
  - ExecutionEngine は PID ファイル（デフォルト data/execution.pid）を扱います

- Monitoring を起動（常駐監視）
  - python -m kabusys.run_monitoring
  - デフォルトポーリング間隔: 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能
    - 例: export MONITOR_POLL_INTERVAL=30

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に生成・更新します

- 設定検証
  - python -m kabusys.validate_config [--strict]

---

## 実行時の主要な環境変数

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading: MockBroker を使い paper_trading.db に発注ログを保存（本番 DB と分離）
    - live: 実際に発注が行われます（取り扱い注意）

- DB / ログパス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - LOG_DIR (default: logs/)
  - LOG_LEVEL (default: INFO)

- OpenAI
  - OPENAI_API_KEY （AI 機能を使う場合）

- その他
  - MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
  - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START（本番での Kill Flag 自動クリア、0 推奨）

- 自動 .env 読み込みの挙動
  - 起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env → .env.local を自動ロードします
  - 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 停止・Kill スイッチ

- 優雅な停止
  - 実行中プロセスを止める方法としてプロジェクトルートの data/stop_requested.flag ファイルを作成すると run_execution / run_monitoring のループは検知して安全に停止します（両起動スクリプトで利用）。

- Kill Switch（Execution 停止用）
  - monitoring 側で条件に合致すると data/kill.flag を書き込みます。ExecutionEngine はこのファイルの存在を検知して自身を停止します。
  - KillSwitch はドローダウン・ポジション上限などをトリガーに作成されます。

- clear
  - KillSwitch.clear() を使うか手動で data/kill.flag を削除して再開します。
  - 環境変数 KILL_FLAG_CLEAR_ON_START=1 があると起動時に自動クリアしますが、本番では 0 を推奨します。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主なファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（OpenAI）
    - regime_detector.py           — 市場レジーム判定（OpenAI + MA）

  - monitoring/
    - monitoring_db.py             — SQLite スキーマ + 永続化 API
    - monitoring_engine.py         — 各 Monitor を束ねるループ
    - system_monitor.py            — システム / データ鮮度監視
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - kill_switch.py               — kill.flag 制御
    - (alert_manager, trade_monitor 等の実装あり)

  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数決定ロジック
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py           — モメンタム/ボラ/バリュー計算（DuckDB）
    - feature_exploration.py       — 将来リターン・IC・統計
    - __init__.py

  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

  - utils/
    - logging_setup.py             — 共通ログ設定
    - process_priority.py          — プロセス優先度 / CPU affinity
    - __init__.py

データ / 実行関連（プロジェクトルート）
- data/
  - kill.flag
  - stop_requested.flag
  - execution.pid
  - monitoring.db (デフォルト: data/monitoring.db)
  - paper_trading.db (paper_trading 用)

ログ
- logs/
  - execution.log, monitoring.log, ...（TimedRotatingFileHandler、日次ローテーション）

---

## 補足・注意事項

- Paper Trading と本番 DB は分離されています。KABUSYS_ENV=paper_trading 時は MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）が必須です。キーがない場合は関連機能は動作しません（例外を投げる箇所あり）。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通して統一されています。ログディレクトリを作成できない場合は標準出力のみで稼働します。
- OS によっては process priority / cpu affinity の設定が制限されるため失敗時は警告が出て処理を継続します（psutil を使用）。
- .env は絶対に Git にコミットしないでください。config_setup.py はその旨を明示しています。
- DuckDB の一部機能はバージョン差分に依存する可能性があるため、実行環境の duckdb バージョンに注意してください。
- テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境自動ロードを無効化できます。

---

README はここまでです。必要であれば以下を追加できます：
- 具体的な設定例（.env.example 風）
- 各モジュール（ExecutionEngine / TradeMonitor / AlertManager 等）の詳細設計ドキュメント
- 開発用のユニットテスト実行方法や CI 設定のサンプル

ご希望があれば追記します。