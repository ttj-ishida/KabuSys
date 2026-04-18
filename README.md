# KabuSys

日本株向け自動売買システムのサブセット実装（ライブラリ + 起動スクリプト群）。  
このREADMEはリポジトリ内の主要モジュールをもとに作成した開発者向けドキュメントです。

概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関する以下の機能群を提供します（実装はリサーチ、ポートフォリオ構築、発注管理、監視、AI ベースのニュース分析などに分離されています）。

主な設計方針：
- DuckDB / SQLite を利用したオンプレミス型の時系列・ログ保存
- 実行環境（development / paper_trading / live）ごとに挙動を切り替え
- OpenAI（gpt-4o-mini）によるニュースセンチメント評価やマクロ判定（API キー必須）
- モジュールは純粋関数ベースでテストしやすく実装
- Kill Switch（フラグファイル）で外部から ExecutionEngine の停止を指示可能

バージョン: 0.1.0 (src/kabusys/__init__.py)

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートを基準に .env / .env.local を読み込む）
  - 対話式の .env 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行コンポーネント
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録
    - プロセス優先度を高く設定（set_process_priority）
    - 停止フラグ / PID 管理（data/stop_requested.flag, data/execution.pid）
  - Monitoring ポーリングスクリプト（python -m kabusys.run_monitoring）
    - SystemMonitor / TradeMonitor / RiskMonitor を定期実行
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）
    - 監視ログは SQLite（settings.sqlite_path）へ保存（監視は常に本番 sqlite_path を使用）

- 監視（Monitoring）
  - system_status, trade_logs, positions, risk_logs, dashboard 等の永続化（monitoring_db）
  - RiskMonitor: ドローダウン / ポジション上限監視とアラート記録
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine に停止指示

- ポートフォリオ構築（純粋関数）
  - 候補選出、重み計算（等金額 / スコア加重）
  - セクター上限適用（apply_sector_cap）
  - ポジションサイズ計算（risk_based / equal / score）

- リサーチ / ファクター計算（DuckDB）
  - momentum, volatility, value 等のファクター計算（prices_daily / raw_financials を参照）
  - IC 計算、将来リターン、統計サマリ、rank 等のユーティリティ

- AI（OpenAI）
  - ニュースを集約してセンチメントを算出し ai_scores に保存（kabusys.ai.news_nlp）
  - マクロセンチメントと ETF MA を合成して市場レジームを判定（kabusys.ai.regime_detector）
  - OpenAI API 呼び出しはバックオフ/リトライ、レスポンス検証を実装

- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
    - 稼働率、注文成功率、レイテンシ、リスク却下などを集計して PASS/FAIL を判定

---

## セットアップ手順

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール  
   下記は主要依存関係の例（プロジェクトに requirements.txt があればそれを使用してください）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で任意）
   - その他: sqlite3 は標準ライブラリ

   例:
   - pip install duckdb psutil openai PyYAML

3. プロジェクトルートに .env を用意
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動作成: リポジトリに .env.example があれば参考にしてください。

   必須環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   AI 機能を使う場合:
   - OPENAI_API_KEY を設定

   その他よく使う環境変数（デフォルトを必要に応じて上書き可）:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
   - LOG_LEVEL — "INFO" 等
   - LOG_DIR — ログ保存先（デフォルト: logs/）
   - KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリア（0/1）

   自動ロード:
   - 既定でプロジェクトルートの .env が自動ロードされます（.env.local は上書き）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリの作成（必要に応じて）
   - mkdir -p data logs

---

## 使い方

主要な CLI / モジュールの実行例。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告をエラー扱いにする: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し MockBrokerClient を利用
    - 停止フラグ（data/stop_requested.flag）や kill.flag を監視
    - data/execution.pid に PID を保存
    - プロセス優先度を high に設定しようとします（権限により失敗する可能性あり）

- Monitoring を起動（定期監視）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）を指定（デフォルト 60）。1 未満や 0 は無視されて 60 秒が使われます。
  - 注意:
    - 監視コンポーネントは KABUSYS_ENV に関係なく production の sqlite_path（settings.sqlite_path）を使用します（監視ログは本番 DB に記録）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH が優先されます。

- AI / リサーチ関数（プログラムから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - リサーチ関数（例）: kabusys.research.calc_momentum(duckdb_conn, date)
  - OpenAI を使う関数は OPENAI_API_KEY が必要。api_key 引数でも指定可能。

ログ:
- logging は kabusys.utils.logging_setup.setup_logging を通して統一的に設定されます。
- デフォルトログディレクトリ: logs/。ログファイル名は <app_name>.log（例: logs/execution.log）。

停止・Kill Switch:
- 外部から ExecutionEngine 停止を指示するには data/kill.flag に理由を書き込むか、Monitoring が条件を満たして自動で書き込みます。
- stop_requested.flag（run_* スクリプトが参照）を作成すると該当スクリプトはループを終了して安全停止します。

注意事項:
- 実行時に高権限での優先度変更や CPU affinity 設定が行われるため、権限不足により警告が出ることがあります（挙動はスキップされます）。
- AI 呼び出しは外部 API を使うためコストとレート制限があります。レスポンス検証とリトライが実装されていますが、API キーの取り扱いは慎重に行ってください。

---

## ディレクトリ構成（主要ファイル）

リポジトリの src/kabusys 以下の主要モジュール / パッケージ:

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数 / デフォルト値の定義、自動 .env ロード
  - config_setup.py
    - 対話式 .env ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py         — ニュースの LLM センチメント評価と ai_scores への書き込み
    - regime_detector.py  — ETF MA とマクロニュースを合成して市場レジーム判定
  - monitoring/
    - monitoring_db.py    — SQLite テーブル定義・永続化層
    - system_monitor.py   — CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - risk_monitor.py     — ドローダウン / ポジション上限監視
    - kill_switch.py      — kill.flag 書き込みユーティリティ
    - monitoring_engine.py— 各 Monitor を束ねる実行ループ
    - (trade_monitor.py, alert_manager.py 等が想定される)
  - execution/
    - execution_engine.py
    - broker_factory.py
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
  - data/
    - pipeline.py, stats.py (prices データ取得・統計系ユーティリティ想定)
  - tools/
    - paper_verification_report.py  — Paper Trading の検証レポート生成スクリプト
  - utils/
    - logging_setup.py     — ログ設定ユーティリティ
    - process_priority.py  — プロセス優先度・CPU affinity 設定
  - その他: logs/, data/（実行時に使用される）

監視 DB（SQLite）スキーマ（monitoring_db.init_monitoring_db に定義）:
- system_status (cpu_percent, memory_percent, disk_percent, process_ok, recorded_at)
- trade_logs (発注イベントログ、latency_ms カラムあり)
- positions (保有)
- risk_logs
- dashboard (集計、peak_value カラムあり)

---

## 補足情報・運用メモ

- 環境自動ロード:
  - プロジェクトルートは .git または pyproject.toml により検出されます。
  - 自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- .env の取り扱い:
  - .env は機密情報を含むため絶対に Git にコミットしないでください。
  - config_setup.py で生成された .env ファイル内にも同旨の注意書きがあります。

- paper_trading モード:
  - KABUSYS_ENV=paper_trading に設定すると発注はモッククライアントを用いて paper_trading 用の SQLite に記録され、本番 DB と分離されます。

- ログ:
  - setup_logging は stdout へ出力しつつファイルへ日次ローテーションで保存します（デフォルト 30 日分保持）。

- テスト / 開発:
  - 多くのモジュールは依存性注入（DuckDB/SQLite 接続・Broker クライアントなど）で設計されており、ユニットテストがしやすい構造です。
  - AI 呼び出し部分は _call_openai_api 等の関数をモックすることでエンドツーエンドの API 呼び出しを回避できます。

---

必要に応じてこの README をベースに運用手順（デプロイ・監視・ロールバック手順）、CI 設定、requirements.txt を追加してください。質問や追加で記載したい内容があれば教えてください。