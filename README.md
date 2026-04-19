# KabuSys

日本株向けの自動売買システム（プロジェクト骨格）。  
このリポジトリは以下の主要機能を含み、実運用・ペーパートレード・研究用途の各コンポーネントを備えます。

- 実行エンジン（ExecutionEngine）
- 監視 / Kill Switch（Monitoring）
- ポートフォリオ構築（候補選定・配分・サイズ決定）
- リサーチ（ファクター計算・特徴探索）
- ニュースを用いる AI スコアリング（OpenAI）
- ユーティリティ（ログ設定・プロセス優先度設定 等）
- 運用ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

以下はソースコード（src/kabusys 以下）から作成した README です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。設計方針は以下の通りです。

- 実取引（live）とペーパートレード（paper_trading）を分離して運用可能
- DuckDB / SQLite を用いたデータ蓄積・分析
- モジュールは可能な限り純粋関数（副作用を持たない）として設計
- OpenAI を用いたニュースセンチメント評価やレジーム判定をサポート
- 監視コンポーネントで稼働状況を監視し、所定の条件で Kill Switch を発動可能

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動するエントリポイント
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、`data/paper_trading.db` に記録（本番 DB と分離）
  - PID ファイル / stop フラグで安全停止制御
- run_monitoring.py
  - SystemMonitor のポーリングループを起動
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔上書き可能（デフォルト 60 秒）
  - 監視用 DB は環境に関係なく本番の sqlite_path を使用する設計
- config_setup.py
  - 対話式ウィザードで `.env` を作成 / 更新
- validate_config.py
  - .env と config/*.yaml の設定を起動前に検証
- tools/paper_verification_report.py
  - Paper Trading のログ（SQLite）から検証レポートを生成
- portfolio/*
  - 候補選定、重み計算、ポジションサイズ決定、セクター制限などの純粋関数を提供
- research/*
  - DuckDB を用いたファクター算出、将来リターン・IC 計算など
- ai/*
  - news_nlp: OpenAI を用いたニュースのセンチメントスコア付与
  - regime_detector: MA200 とマクロニュースを合成して日次レジーム判定
- monitoring/*
  - MonitoringDB（SQLite永続化）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager 等
- utils/*
  - ロギング設定、プロセス優先度 / CPU affinity 設定など共通ユーティリティ

---

## 事前準備 / 依存関係（例）

コード中で使用されているライブラリ例（バージョンはプロジェクトポリシーに合わせて指定してください）:

- Python 3.9+
- duckdb
- psutil
- openai (OpenAI Python SDK)
- PyYAML（config 検証を行う場合は必須ではあるが推奨）
- sqlite3（標準ライブラリ）

実際には requirements.txt を用意している場合はそちらを利用してください。ない場合は最低限次のようにインストールします:

python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml

注: OpenAI を使う機能を利用するには環境変数 `OPENAI_API_KEY` が必要です。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は上記の必須パッケージを個別にインストール）

4. .env の作成
   - 対話式で作成: python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - その他: DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, OPENAI_API_KEY（AI 機能用）など
   - .env 自動読み込み:
     - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動でロードされます（テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

---

## 使い方（主要コマンド）

- 実行エンジン起動（バックグラウンド管理は別途必要）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 sqlite（PAPER_TRADING_SQLITE_PATH または `data/paper_trading.db`）を使用
    - PID ファイル: data/execution.pid（Settings.pid_file_path）
    - 停止: `data/stop_requested.flag` が検出されると安全に停止する

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒数で指定（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存しない）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 確認項目: 稼働率、注文成功率、送信率、P95 レイテンシ等

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時）
- PAPER_FILL_MODE — paper_trading 時のフィルモード（instant/partial/never/reject）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で使用）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

詳しくは `kabusys.config.Settings` のプロパティを参照してください。

---

## 運用上の概念（重要）

- Paper Trading と Live の分離
  - `KABUSYS_ENV=paper_trading` を指定すると Execution は MockBrokerClient を使用し、ペーパートレード専用 DB に記録します。本番 DB と分離するため必ず環境変数を正しく設定してください。

- Kill Switch / stop フラグ
  - `kabusys.monitoring.kill_switch` が条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。
  - `data/stop_requested.flag` が存在すると `run_execution` / `run_monitoring` はループを抜けて終了します（外部から安全停止するための仕組み）。

- ログ
  - `kabusys.utils.logging_setup.setup_logging` により stdout と日次ローテートのファイルログ（logs/<app_name>.log）に出力されます。ログディレクトリが作れない環境ではコンソールのみで継続します。

- データ鮮度 / 監視
  - SystemMonitor はプロセスの健全性、CPU/メモリ/Disk、DuckDB 内のデータ鮮度などをチェックします。監視は `monitoring` テーブル群（SQLite）に永続化されます。

---

## ディレクトリ構成（src/kabusys の主なファイル）

- __init__.py — パッケージ情報
- config.py — 環境変数 / Settings 管理（.env 自動ロード機能含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ（主要ファイル）:

- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリング
  - regime_detector.py — レジーム判定（MA200 + マクロニュース）
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 発注ログの異常検出（存在）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — Kill Switch 実装
  - monitoring_engine.py — 各モニターの統合
  - alert_manager.py — アラート送信（存在）
- execution/
  - execution_engine.py — ExecutionEngine（実行ロジック）
  - broker_factory.py — Broker クライアントの生成（Mock / Live）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実注関連
- portfolio/
  - portfolio_builder.py — 候補選定・重み算出
  - position_sizing.py — 発注株数計算（ロット丸め等）
  - risk_adjustment.py — セクター上限、レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン / IC 計算 等
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度・CPU affinity 設定

（上記以外にも細かいモジュールが含まれます。実際のファイル一覧はソースツリーを参照してください。）

---

## 開発・運用上の注意

- .env は機密情報を含むため Git にコミットしないでください（config_setup.py の生成メッセージにも注意喚起あり）。
- 本番環境（KABUSYS_ENV=live）では kill_flag やログ設定を慎重に扱ってください。validate_config の live チェックは本番向けの注意点を警告します。
- OpenAI API を利用する機能は API キーと利用料が発生します。キー漏洩に注意してください。また、LLM 呼び出しは外部に依存するため失敗時はフェイルセーフ（スコア 0 など）で継続する設計になっていますが、運用ルールを定めてください。
- DuckDB / SQLite のパス、ログディレクトリ、データディレクトリ（`data/`）の権限やバックアップ方針を整えてください。

---

## 参考コマンドまとめ

- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README は以上です。追加で以下の点について追記が必要であれば教えてください。

- requirements.txt の具体的なバージョン提案
- 各モジュール（ExecutionEngine 等）の詳しい設計図やシーケンス図
- 運用手順（デプロイ / システム監視 / ロールバックフロー）