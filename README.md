# KabuSys

日本株向け自動売買システムのコンポーネント群（ライブラリ兼実行スクリプト群）。

このリポジトリは、発注エンジン・監視・ポートフォリオ構築・リサーチ・AI（ニュースNLP / レジーム判定）などの主要機能をモジュール化して提供します。

---

## プロジェクト概要

- 発注（ExecutionEngine）とそれを監視する Monitoring 系のコンポーネントを中心に、ポートフォリオ構築・リスク調整・ポジションサイズ計算などの純粋関数、DuckDB / SQLite を用いたデータアクセス層、OpenAI を用いたニュースセンチメント分析・レジーム判定などを含みます。
- 設定は .env ファイル（または環境変数）で管理。`.env` を自動ロードする機能を備え、対話式ウィザードで初期作成が可能です。
- Paper Trading（ペーパートレード）用に本番 DB と分離した専用 SQLite を利用する仕組みがあります。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV によるペーパートレード切替あり）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更）
- 設定管理 / 検証
  - config.py: 環境変数 / .env の読み込みと Settings クラス
  - config_setup.py: 対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config.py: 起動前チェック（必須環境変数や config/*.yaml の簡易検証）
- 監視
  - monitoring/monitoring_db.py: SQLite 監視テーブルの初期化・永続化 API
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py 等
  - run_monitoring による定期ポーリング（stop フラグによる安全停止）
- 発注 / 実行関連（execution/*）
  - Broker ファクトリ、ExecutionEngine、OrderManager、RiskManager、Reconciler、OrderRepository など（主要ロジックは execution 配下）
- ポートフォリオ構築（portfolio/*）
  - 候補選定、重み計算、セクター制限、レジーム乗数、ポジションサイズ算出（純粋関数群）
- リサーチ（research/*）
  - ファクター計算（Momentum / Volatility / Value 等）、将来リターン、IC 計算、統計サマリなど（DuckDB を利用）
- AI（ai/*）
  - news_nlp.py: raw_news を OpenAI に投げて銘柄ごとのセンチメントを ai_scores テーブルへ書込
  - regime_detector.py: ETF MA とマクロニュース（LLM）を組み合わせて market_regime を算出・保存
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定（psutil ベース）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone … && cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config の YAML 検証を有効にしたい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （本リポジトリに requirements.txt がない場合は上記を個別にインストールしてください）

4. .env を作成
   - 対話式に作る:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して .env を手動作成
   - .env は絶対に Git にコミットしないこと

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）になります

注意:
- 自動ロード: config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探して `.env` / `.env.local` を自動で読み込みます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（主要）

必須（validate_config でチェックされる）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（代表）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY: OpenAI 呼び出しに必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパー取引時の約定モード（instant|partial|never|reject）

---

## 使い方（よく使うコマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 / ペーパーは KABUSYS_ENV で切替）
  - python -m kabusys.run_execution

  動作メモ:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - data/execution.pid に PID を書きます（設定で変更可）。

- Monitoring（SystemMonitor）起動
  - python -m kabusys.run_monitoring

  動作メモ:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更（秒、デフォルト 60）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを書きます。
  - 停止は data/stop_requested.flag を作成することで行えます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH を使うことも可能

- AI モジュール（プログラムから直接呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## ロギング

- ログ設定は kabusys.utils.logging_setup.setup_logging を通して行います（起動スクリプトで自動的に呼ばれます）。
- 出力先:
  - コンソール（stdout）
  - ファイル: logs/<app_name>.log（日次ローテート、30日保持）
- 環境変数:
  - LOG_LEVEL（出力レベル）
  - LOG_DIR（ログ保存ディレクトリ）

---

## 停止 / Kill Switch

- kill_switch（data/kill.flag）:
  - RiskMonitor 等が条件を満たすと data/kill.flag を作成し、ExecutionEngine に対する停止シグナルを出します。
  - KillSwitch.clear() によってフラグを削除できます。
- stop フラグ（stop_requested.flag）:
  - run_execution / run_monitoring は data/stop_requested.flag を検知して安全に停止します。

---

## よくあるトラブルシューティング

- OpenAI 未設定
  - news_nlp や regime_detector を使うには OPENAI_API_KEY が必要です。未設定だと ValueError が発生します。
- psutil によるプロセス優先度設定で AccessDenied
  - set_process_priority は権限がないと警告を出してスキップします（フェイルセーフ）。
- validate_config で YAML パースチェックがスキップされる
  - PyYAML がインストールされていないと YAML の内容検証はスキップされます（警告が出ます）。
- ログディレクトリ作成失敗
  - 権限等で logs ディレクトリが作れない場合、コンソールログのみで継続します。LOG_DIR を書き込み可能なパスに変更してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数/.env のロードと Settings
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前の設定検証
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ / ファイル（主要）
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — 市場レジーム判定（ETF MA + LLM マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite テーブル作成・永続化 API
  - system_monitor.py — システム状態 / データ鮮度監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - trade_monitor.py — 発注ログ監視（滞留注文等）  ※ファイル内実装あり
  - monitoring_engine.py — 監視コンポーネントを束ねる
  - kill_switch.py — kill.flag の管理
  - alert_manager.py — 通知管理（LINE等）
- portfolio/
  - portfolio_builder.py — 候補選定・重み
  - risk_adjustment.py — セクター上限・レジーム乗数
  - position_sizing.py — 株数計算・上限・単元丸め
- research/
  - factor_research.py — Momentum/Value/Volatility 等ファクター計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- utils/
  - logging_setup.py — 一元的なログ設定
  - process_priority.py — プロセス優先度 / CPU affinity
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート

データ / 実行時ファイル（プロジェクトルート）
- data/
  - monitoring.db（デフォルト SQLite）
  - paper_trading.db（ペーパートレード用、KABUSYS_ENV=paper_trading の場合使用）
  - kabusys.duckdb（デフォルト DuckDB）
  - kill.flag / stop_requested.flag / execution.pid などの制御ファイル

---

## 開発上の注意点 / 設計方針（抜粋）

- 多くの分析・ポートフォリオ計算関数は副作用を持たない純粋関数として設計されています（テスト容易性）。
- OpenAI 呼び出し周りはエラーに対してフェイルセーフ（失敗時はデフォルト値で継続）を優先し、部分失敗時に既存データを破壊しないよう配慮しています（例: ai_scores の置換は対象コードのみ DELETE→INSERT）。
- 監視ログは SQLite（monitoring.db）へ蓄積。monitoring_db.init_monitoring_db は冪等化・簡易マイグレーションを行います。
- 実行スクリプトは外部からの停止指示（flag ファイル）を監視して安全に終了します。

---

必要に応じて README の補足（運用手順、systemd ユニット例、Dockerfile、requirements.txt など）を追記できます。希望があれば提供してください。