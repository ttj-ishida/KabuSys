KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・分析を支援する内部ライブラリおよび起動スクリプト群です。本リポジトリには以下の機能が含まれます。

- 実行エンジン（ExecutionEngine）の起動スクリプト（run_execution）
- システム監視ループ（SystemMonitor）起動スクリプト（run_monitoring）
- 環境設定ウィザード（config_setup）／設定検証ツール（validate_config）
- ペーパートレード検証レポート生成ツール
- ポートフォリオ構築・リスク調整・株数決定の純粋関数群（portfolio）
- ファクター計算・リサーチユーティリティ（research）
- ニュースNLP・レジーム判定（OpenAI を利用する AI モジュール）
- 監視 DB（SQLite）ラッパー、ログ・アラート関連ユーティリティ

特徴 / 主な機能
----------------
- 実行環境分離:
  - KABUSYS_ENV により development / paper_trading / live を切り替え。
  - paper_trading では MockBroker を使用し、ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）を使用。
- 監視:
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine。
  - 監視結果は SQLite（デフォルト data/monitoring.db）へ永続化。
  - Kill Switch による停止（data/kill.flag）をサポート。
- ログ管理:
  - 統一的なログ設定（コンソール + 日次ローテーションファイル logs/<app>.log）。
- ポートフォリオ構築:
  - 候補選定・等重 / スコア重み・リスク基づく株数決定・セクター上限適用等の純粋関数を提供。
- リサーチ:
  - DuckDB によるファクター計算（Momentum, Volatility, Value 等）と特徴量解析ツール。
- AI（任意）:
  - OpenAI を用いたニュースセンチメント（news_nlp）・市場レジーム判定（regime_detector）。
  - API キーは環境変数 OPENAI_API_KEY を指定。

前提条件
---------
- Python 3.10+（型注釈の構文などに依存）
- 主な依存パッケージ（環境により追加が必要）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config が YAML の中身検証を行う場合）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - 例:
     - git clone <repo>
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要なパッケージをインストールします（requirements.txt がある場合はそれを使用）。
   - 例:
     - pip install duckdb psutil openai
     - （validate_config の詳細チェックを使うなら pip install pyyaml）

3. .env を作成（推奨）:
   - 対話式ウィザードで作成できます:
     - python -m kabusys.config_setup
   - .env の自動読み込み:
     - デフォルトではプロジェクトルートにある .env / .env.local を自動で読み込みます。
     - OS 環境変数は優先され、.env.local は .env を上書きします。
     - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須環境変数（主なもの）
------------------------
- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード

その他主要な環境変数
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject、デフォルト instant）
- OPENAI_API_KEY — OpenAI を使う場合は設定
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL — SystemMonitor のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 本番での自動 kill.flag クリア（0 推奨）

使い方（コマンド）
-----------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳密モード（警告も FAIL として扱う）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使われ、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
    - 実行中に data/stop_requested.flag が存在すると安全に停止します。
    - 実行時に data/execution.pid を作成します。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定（デフォルト 60）。
  - Monitoring は環境にかかわらず本番 sqlite（Settings.sqlite_path）を参照する点に注意。
  - 停止：data/stop_requested.flag を作成して監視ループを停止できます。
  - kill_switch により data/kill.flag が書き込まれると ExecutionEngine 側が停止されます。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。別ファイルを指定する場合は --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用。

- AI / レジーム判定・ニューススコア
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API を使うため OPENAI_API_KEY を設定してください（または関数引数で渡す）。

ログ / PID / フラグ
-------------------
- ログ:
  - デフォルト: logs/<app_name>.log（日次ローテーション、30日保持）
  - コンソールへは stdout に出力されます。
- PID / フラグ:
  - 実行エンジン: data/execution.pid（作成）
  - 停止要求（外部からの即時停止）: data/stop_requested.flag を作成
  - Kill Switch（自動停止トリガ）: data/kill.flag を監視／作成
  - これらのパスは Settings を通じて変更可能です（PID_FILE_PATH / KILL_FLAG_PATH など）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings 管理（.env 自動読み込み機能含む）
- config_setup.py                — .env 作成対話ウィザード
- validate_config.py             — 起動前設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py                   — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py            — マクロ + ma200 で市場レジーム判定
- monitoring/
  - monitoring_db.py              — SQLite ベースの監視 DB ラッパー
  - system_monitor.py             — システム状態・データ鮮度監視
  - risk_monitor.py               — ドローダウン / ポジション上限監視
  - monitoring_engine.py          — 各 Monitor を束ねるエンジン
  - kill_switch.py                — kill.flag の作成 / 評価
  - alert_manager.py (参照)       — アラート送信管理（LINE 等）
  - trade_monitor.py (参照)       — トレード監視（滞留注文・約定異常等）
- execution/                      — Execution エンジン周り（broker, engine, order_manager 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py            — Momentum/Volatility/Value ファクター計算（DuckDB）
  - feature_exploration.py        — IC / forward returns / 統計サマリ
- tools/
  - paper_verification_report.py  — ペーパートレード検証レポート CLI
- utils/
  - logging_setup.py              — 共通ログ設定ユーティリティ
  - process_priority.py           — プロセス優先度 / CPU affinity 設定

設計上の注意点 / 運用メモ
-------------------------
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索して決定）を基に行われます。OS 環境変数は上書き保護されます。
- validate_config は .env の不足・config/*.yaml の存在（と PyYAML があれば内容）をチェックします。起動前に実行することを推奨します。
- Monitoring は監視用 SQLite（SQLITE_PATH）に常に書き込むようになっており、環境にかかわらず本番 sqlite_path を使用します。実行エンジンは paper_trading モード時に専用 DB を使用して本番と分離します。
- OpenAI など外部 API を使う処理はフェイルセーフ設計（API 失敗時はフォールバックして継続）です。ただし本番で AI 機能を使う場合はレート制御・API キー管理に注意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで動作を続けます。

よく使う例（環境変数を一時設定して起動）
---------------------------------------
- 監視ループ（ポーリング間隔 30 秒）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレードで実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 設定検証（厳密モード）:
  - python -m kabusys.validate_config --strict
- レポート生成（DB を明示）:
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11

サポート / 追加
----------------
- 依存関係やデプロイ手順（サービス化 / systemd / Docker 化など）は本 README に含まれていません。運用にあわせてプロセス管理・監視設定を追加してください。
- データベースやログのパス、各種閾値は Settings（環境変数）で調整できます。

ライセンス・バージョン
----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

以上。運用・開発で README に追加したい項目（例: requirements.txt の具体的内容、systemd ユニット例、Dockerfile など）があれば教えてください。必要に応じて追記します。