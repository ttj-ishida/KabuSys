# KabuSys

日本株向けの自動売買システムのコアライブラリ群（ライブラリ兼起動スクリプト群）です。  
このリポジトリには監視 / 発注エンジン、ポートフォリオ構築、ファクター研究、AI ベースのニューススコアリングなどの主要コンポーネントが含まれます。

## 概要
- モジュール構成は「監視 (monitoring)」「発注 (execution)」「ポートフォリオ (portfolio)」「リサーチ (research)」「AI (news/regime)」「ユーティリティ (utils)」などに分割されています。
- モジュール単位でプログラム的に利用できる関数群と、実行用エントリポイント（`python -m kabusys.<module>`）を備えています。
- 設定は環境変数 / `.env` により管理。対話式ウィザードと検証ツールを提供します。
- Paper Trading 用に本番 DB と分離された SQLite を使う仕組みがあります。
- OpenAI API を利用したニュース NLP / レジーム検知機能を含みます（APIキー必須）。

## 主な機能
- 実行（ExecutionEngine）起動スクリプト（`run_execution.py`）
  - `KABUSYS_ENV=paper_trading` では MockBroker と分離した paper DB を使用
  - プロセス優先度設定、PID 管理、停止フラグ監視
- 監視（SystemMonitor / MonitoringEngine）起動スクリプト（`run_monitoring.py`）
  - CPU/メモリ/Disk/プロセス稼働状況やデータ鮮度を定期ポーリングして永続化
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
  - 監視ログは SQLite（`data/monitoring.db`）へ保存（monitoring は環境にかかわらず本番 sqlite_path を使用）
- 監視 DB（`monitoring_db.py`）
  - `system_status`, `trade_logs`, `positions`, `risk_logs`, `dashboard` テーブルを作成・管理
- リスク監視（`risk_monitor.py`）
  - ドローダウン警告、ポジション数上限チェック、ダッシュボード更新、risk_logs への記録
- Kill Switch（`kill_switch.py`）
  - 条件に応じて `data/kill.flag` を書き込み、ExecutionEngine 停止をトリガー
- ポートフォリオ構築（`portfolio` パッケージ）
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数などの純関数
- リサーチ（`research` パッケージ）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を使用）
  - 将来リターン、IC 計算、統計サマリなど
- AI（`ai` パッケージ）
  - `news_nlp`：OpenAI を使ったニュースのセンチメント集約 → `ai_scores` へ書き込み
  - `regime_detector`：ETF MA とマクロニュース（LLM）を合成して日次レジーム判定
- ツール
  - `.env` 対話式ウィザード（`config_setup.py`）
  - 設定検証 CLI（`validate_config.py`）
  - Paper Trading 検証レポート生成スクリプト（`tools/paper_verification_report.py`）
- ロギング整備ユーティリティ（`utils/logging_setup.py`）
  - stdout と日次ローテーションファイル出力（デフォルト `logs/`）を統一的に設定
- プロセス優先度 / CPU affinity 設定ユーティリティ（`utils/process_priority.py`）

## 必要要件
- Python 3.10+
- 推奨 / 必要パッケージ（代表）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（`validate_config` で config/*.yaml のパース検証を行う場合）
- これらは環境によって追加・削除されるため、プロジェクト内に requirements.txt があればそれを利用してください。
  例:
  pip install duckdb psutil openai PyYAML

## セットアップ手順
1. リポジトリをクローン / 配布パッケージを展開
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （オプション）pip install PyYAML
4. 初期 `.env` ファイル作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 対話で必要項目（J-Quants token / KABU API password / KABUSYS_ENV など）を入力
5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば指摘に従って `.env` や config/*.yaml を修正
6. データディレクトリの確認
   - デフォルトで以下のファイル/ディレクトリを使用します:
     - data/monitoring.db（SQLite 監視 DB）
     - data/paper_trading.db（Paper Trading 用 DB）
     - data/kabusys.duckdb（DuckDB）
     - data/execution.pid（Execution の PID）
     - data/kill.flag / data/stop_requested.flag（停止制御）
     - logs/（ログ出力）

## 使い方（主要コマンド）
- 実行エンジン（ExecutionEngine）を起動
  - 通常（`.env` の KABUSYS_ENV を使用）:
    - python -m kabusys.run_execution
  - Paper Trading（環境変数で上書きしても可）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 注意:
    - Paper Trading では `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）を使用して本番 DB とは分離します。
    - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
    - ExecutionEngine 側は `KILL_FLAG_CLEAR_ON_START` に応じて `data/kill.flag` を自動クリアする挙動があります（本番では 0 推奨）。
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で指定（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は `settings.sqlite_path`（通常 `data/monitoring.db`）にログを書きます。monitoring は常に sqlite_path を使用します（KABUSYS_ENV に依存しない）。
- 設定の検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI 機能（プログラム呼び出し例）
  - OpenAI API キーは環境変数 OPENAI_API_KEY で指定
  - 例: kabusys.ai.score_news(conn, target_date, api_key=None)  # api_key が None の場合環境変数を参照
- 停止手段
  - 永続的な停止（外部要因）: プロジェクトルートの data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して安全停止します。
  - Kill Switch（リスクによる停止）: 監視コンポーネントが条件を満たすと `data/kill.flag` を書き込み ExecutionEngine に停止指示を送る仕組みです。

## 環境変数（主要）
- 必須 / 重要
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB / ログ
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB、デフォルト: data/paper_trading.db）
  - LOG_DIR（ログファイル保存先、デフォルト: logs/）
  - LOG_LEVEL（"DEBUG"/"INFO"/...）
- 監視 / 制御
  - MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
  - PID_FILE_PATH（Execution 用 pid ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_CLEAR_ON_START（0/1、起動時に kill.flag を自動クリアするか）
  - PAPER_FILL_MODE（paper_trading の MockBroker の fill モード: instant|partial|never|reject）

## 実装上のポイント / 注意事項
- run_monitoring は MONITOR_POLL_INTERVAL を環境変数で上書き可能。0以下の値は無効でデフォルトにフォールバックします。
- run_monitoring のデータ永続化（SQLite）は常に `settings.sqlite_path` を使います（監視は本番 DB と同一ファイルを参照する設計）。
- run_execution は KABUSYS_ENV が `paper_trading` の場合、Paper 用 SQLite を使用して本番と完全分離します。
- ログは stdout とファイル（TimedRotatingFileHandler：日次、30日保持）に出力されます。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで動作します。
- OpenAI を使うモジュールは API キーを必要とし、エラー時は安全側フォールバック（スコア 0.0 等）して処理継続します（フェイルセーフ設計）。
- `.env` は機密情報を含むため、絶対にリポジトリにコミットしないでください（config_setup.py にもその旨が記載されています）。

## ディレクトリ構成（抜粋）
プロジェクトルートに `src/kabusys` があり、主要ファイルは以下の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照あり、実装はプロジェクト内に別ファイルとして存在)
    - kill_switch.py
    - alert_manager.py (参照あり)
  - execution/
    - (ExecutionEngine 関連のモジュール群 — broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager 等)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - ...（上記）
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/ (ランタイムで生成される想定)
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - logs/ (デフォルトログ出力先)

（注）上は主要ファイルの抜粋です。実際のリポジトリにはさらに多くの実装ファイルが含まれます。

## 開発者向けメモ
- DuckDB 接続を渡して純粋関数でファクターや指標を計算する設計になっており、研究・テスト時に外部 API を叩かずに処理を検証できます。
- テスト時は外部 API 呼び出し（OpenAI など）を patch / mock することを想定した設計（例: _call_openai_api をモック可能）。
- 設定ファイル（config/*.yaml）が必要な場合、`scripts/generate_config.py` 等の補助スクリプトでテンプレート生成を行う設計想定（validate_config.py 中のメッセージ参照）。

---

不明点や README に追加したい環境別の実行例（systemd unit, docker-compose など）があれば教えてください。必要に応じて実運用向けのデプロイ手順や systemd ユニットのサンプルも作成します。