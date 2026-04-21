# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買 / 研究 / 監視に関するユーティリティ群をまとめたコードベースです。  
README ではプロジェクト概要、主な機能、セットアップ手順、使い方、およびディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 日次・リアルタイムの監視（System / Trade / Risk の監視、Kill Switch）
- Execution エンジン（実際の発注 / ペーパートレード切替）
- ポートフォリオ構築（銘柄選定、重み・株数計算、セクター・レジーム制御）
- 研究用ファクター計算 / 特徴量探索（DuckDB を利用した独立集計）
- ニュースの NLP によるセンチメント評価（OpenAI API 経由）
- 運用補助ツール（環境設定ウィザード、設定検証、Paper Trading レポート生成）
- 共通ユーティリティ（ログ設定、プロセス優先度制御など）

設計方針の要点：
- DB（SQLite / DuckDB）とローカルファイルを中心にデータ永続化
- 本番 / ペーパートレードを環境変数で明確に切替
- 可能な限りフェイルセーフ（API失敗時のフォールバック、部分的な安全な書込み）
- ルックアヘッドバイアス対策（研究・AI モジュールは日付参照に注意）

---

## 主な機能一覧

- run_monitoring.py
  - SystemMonitor を定期ポーリングして system_status / dashboard / risk_logs 等を更新
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）
  - 監視サイクル内で kill.flag の書き込みを行い ExecutionEngine を停止させる（Kill Switch）

- run_execution.py
  - ExecutionEngine を起動して当日のセッションを実行
  - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db）へ記録
  - 停止フラグ（data/stop_requested.flag）で安全に停止

- config_setup.py
  - .env を対話式に作成 / 更新するウィザード

- validate_config.py
  - .env と config/*.yaml の基本チェックを実行する CLI（--strict モードあり）

- tools/paper_verification_report.py
  - ペーパートレード DB を集計し稼働率・注文成功率・レイテンシなどをレポート形式で出力

- portfolio モジュール
  - 銘柄選定、等重/スコア重み、株数決定（単元丸め・集約キャップ）、セクター制約、レジーム乗数

- research モジュール
  - ファクター（Momentum / Volatility / Value）の計算、将来リターン、IC 計算、統計サマリ

- ai モジュール
  - news_nlp.py: OpenAI を使った記事の銘柄別センチメント算出（ai_scores への書込み）
  - regime_detector.py: ETF MA 乖離とマクロニュースを合成して市場レジーム判定

- utils
  - logging_setup: 統一的なログ初期化（コンソール + 日次ローテーション）
  - process_priority: OS に依存せずプロセス優先度 / CPU affinity を設定
  - など

- monitoring
  - monitoring_db: SQLite スキーマの初期化・永続化 API
  - system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_engine, alert_manager（ログ・通知管理）など

---

## セットアップ手順

前提:
- Python 3.9+（コードは型ヒント等を利用しているため新しめの Python を推奨）
- OS: Linux / macOS / Windows（いくつかの機能はプラットフォーム差分あり）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または Windows では .venv\Scripts\activate

2. 依存パッケージをインストール
   - 必要パッケージの例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイル検証に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt があればそれを利用してください）

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example をコピーして編集（存在する場合）

   主要な環境変数（一部）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
   - DUCKDB_PATH — デフォルト data/kabusys.duckdb
   - SQLITE_PATH — デフォルト data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
   - LOG_LEVEL — デフォルト INFO
   - OPENAI_API_KEY — ai モジュールを利用する場合必須
   - MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）

   注意: .env は絶対にリポジトリにコミットしないでください（シークレットを含みます）。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

5. データディレクトリの作成（必要に応じて）
   - デフォルトでは `data/`、ログは `logs/` に出力されます。起動時に自動作成される場合もありますが、権限に注意してください。

---

## 使い方

以下は典型的な起動・操作方法です。プロセスマネージャ（systemd / supervisord / Docker / k8s 等）で起動することを想定しています。

- 監視プロセスを起動（バックグラウンド or コンテナ内で）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を変更する例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 備考: Monitoring は本番（settings.sqlite_path）を常に参照します（環境にかかわらず）。

- Execution エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定してペーパートレードモードにする:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - ペーパートレード時は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録され、本番 SQLite と分離されます。
  - run_execution は起動時にプロセス優先度を high に設定し、エンジンはデーモンスレッドで run_session を実行します。
  - 停止フラグ: `data/stop_requested.flag` があれば起動を行わない / 実行中は停止します。

- Kill Switch（Monitoring から Execution へ停止指示）
  - Monitoring 側のリスク判定により `data/kill.flag` を書き込むと ExecutionEngine は停止を検出して停止します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動でクリアしますが、本番では推奨されません。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB ファイルを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI（ニュース・レジーム）
  - ai.score_news / regime_detector.score_regime は DuckDB 接続と target_date, OPENAI_API_KEY を与えて呼び出します。
  - 例（スクリプト経由）:
    - OPENAI_API_KEY=xxx python -c "from kabusys.ai.news_nlp import score_news; import duckdb, datetime; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date(2026,4,20)))"
  - 実運用ではモジュール関数を呼んで ai_scores / market_regime テーブルへ書き込みます。
  - API 呼び出しはリトライ・バックオフを備えていますが、API キーの設定を忘れないでください。

- ログ
  - デフォルトで `logs/<app_name>.log` に日次ローテーションで保存されます（30 日保持）。
  - setup_logging を各スクリプトで呼び出して統一的にログを構成します。

---

## ファイル / ディレクトリ構成（主要部のみ）

（リポジトリの root 配下に `src/kabusys` がある想定）

- src/kabusys/
  - __init__.py
  - run_monitoring.py           — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - config.py                   — 環境変数・設定管理（Settings クラス）
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py                — ニュース NLP → ai_scores 書込み
    - regime_detector.py         — 市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py           — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py
    - trade_monitor.py           — (発注ログ監視等)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py           — 通知（LINE 等）を統括（実装に応じて）
  - utils/
    - logging_setup.py           — 共通ログ初期化
    - process_priority.py        — プロセス優先度 / CPU affinity
    - __init__.py
  - execution/                   — 発注周りの実装（BrokerFactory 等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/                  — 上述（重複しないよう注意）

- data/                          — デフォルトの DB / フラグファイル置き場（起動時に作成される）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - stop_requested.flag
  - kill.flag

- logs/                          — デフォルトログ出力先

---

## 運用上の注意 / ヒント

- .env の管理
  - シークレットは .env に保存しますが、決して Git にコミットしないでください。
  - config_setup.py で初期化し、validate_config.py でチェックしてから運用開始してください。

- 本番環境では KABUSYS_ENV=live とし、KILL_FLAG_CLEAR_ON_START は 0 にしてください。

- DB の分離
  - ペーパートレードでは paper_trading 用の SQLite を使って本番 DB と完全分離します。設定を誤って本番 DB を上書かないよう注意してください。

- プロセス優先度
  - 起動スクリプトは最初にプロセス優先度を "high" に設定します。権限や OS により無効化される場合があります（警告ログが出ます）。

- 停止フラグ
  - safe stop: `data/stop_requested.flag` を作成すると run_execution/run_monitoring は検出して終了します。
  - kill switch: Monitoring 側が危険判定した場合に `data/kill.flag` を書き込んで Execution を停止させます。

- OpenAI 利用
  - OPENAI_API_KEY は環境変数で与えるか関数引数として渡してください。API コスト・レート制限に注意して運用してください。

---

## よくあるコマンドまとめ

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

必要であれば各モジュールの API 使用例（関数呼び出しサンプル）や systemd ユニット / docker-compose の雛形も作成できます。どの情報を追加したいか教えてください。