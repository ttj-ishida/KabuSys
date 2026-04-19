KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株向けの自動売買/リサーチ/監視ツール群を含む Python パッケージです。  
README ではプロジェクト概要、機能、セットアップ手順、主要スクリプトの使い方、ディレクトリ構成を日本語でまとめます。

概要
----
KabuSys は自動発注（ExecutionEngine）、監視（Monitoring）、ファクター計算やポートフォリオ構築、AI を使ったニュース解析等の機能を備えたモジュール群です。  
各コンポーネントは疎結合に設計され、環境変数 (.env) で挙動を切り替えられます。ペーパートレード用に本番 DB と完全に分離したモードを持ちます。

主な機能一覧
-------------
- ExecutionEngine（run_execution.py）
  - 本番（live） / ペーパートレード（paper_trading）を環境変数 KABUSYS_ENV で切替
  - ブローカークライアントの抽象化（MockBroker を利用した paper_trading）
  - リスク管理、オーダー管理、照合（reconciler）を含む実行パイプライン
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム稼働状況（CPU/メモリ/ディスク）、データ鮮度、滞留注文、ドローダウン等を監視
  - Kill Switch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
  - アラート送信（LINE など、設定に応じて）
- Portfolio（kabusys.portfolio）
  - 候補選定、等ウェイト/スコアウェイト、リスク制約（セクターキャップ等）、ポジションサイズ算出
- Research（kabusys.research）
  - DuckDB 上の価格データを用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（kabusys.ai）
  - ニュースのセンチメント判定（OpenAI API を利用して銘柄別スコアを ai_scores に書き込み）
  - 市場レジーム判定（ETF・マクロ記事を組み合わせたレジーム判定）
- ツール
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- ログ設定ユーティリティ（utils/logging_setup.py）
- プロセス優先度 / CPU affinity 設定ユーティリティ（utils/process_priority.py）
- 監視用 SQLite DB 層（monitoring/monitoring_db.py）

セットアップ手順（開発環境向け）
-------------------------
1. リポジトリをクローンしてワークツリーに入る
   - 例: git clone ... && cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または .venv\Scripts\activate

3. 依存パッケージをインストール
   - 必須（主なもの）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（設定ファイル検証を有効にする場合）
   - 例:
     - pip install duckdb psutil openai pyyaml
   - （requirements.txt があれば pip install -r requirements.txt）

4. 環境変数 (.env) の用意
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考に）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 厳格モード（警告もエラー扱い）:
     - python -m kabusys.validate_config --strict

主要な環境変数（代表）
---------------------
- 動作モード / ログ:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - LOG_DIR: ログファイル出力先（デフォルト: logs/）
- API キー:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能を使う場合）
- データベース:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 SQLite、デフォルト: data/paper_trading.db）
- その他:
  - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレード挙動）
  - PID_FILE_PATH: 実行エンジンの PID 保存先（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill flag（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 1 で起動時に kill.flag を自動クリア（本番では 0 推奨）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値

使い方（実行例）
----------------
- 環境構築・設定確認
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading のときは MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録される（本番 DB と分離）

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラム呼び出し例）
  - OpenAI API キーを設定してから使用:
    - export OPENAI_API_KEY=...
    - 例: from kabusys.ai import score_news
      - score_news(conn, target_date, api_key=None)  # api_key None の場合は環境変数を参照

停止・Kill Switch
-----------------
- 監視プロセス / 実行プロセスの停止:
  - プロジェクトルート配下の data/stop_requested.flag を作成すると監視ループ・実行エンジンは検出して優雅に停止します（run_monitoring.py / run_execution.py が参照）。
- Kill Switch:
  - KillSwitch（監視ロジック）により条件を満たすと data/kill.flag に理由を書き込み、ExecutionEngine を停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時にこのフラグを自動クリアしますが、本番環境では危険なため 0 を推奨します。

ログ
---
- ログはコンソール（stdout）と日次ローテーションされたファイル（logs/<app_name>.log）に出力されます。ログの設定は kabusys.utils.logging_setup.setup_logging で統一管理されます。
- LOG_DIR 環境変数でログディレクトリを変更できます。

注意点 / 運用上の留意事項
-----------------------
- monitoring は環境にかかわらず本番向けの sqlite_path（Settings.sqlite_path）を使用します（監視ログは本番 DB に保存する想定）。
- execution は KABUSYS_ENV=paper_trading のとき PAPER_TRADING_SQLITE_PATH を使用し、本番 DB と分離されます。
- OpenAI を使用する機能は API 制限やレイテンシに依存するため、API キーの管理、レート制御、リトライロジックに注意してください（実装に指数バックオフあり）。
- .env を絶対にリポジトリへコミットしないでください（機密情報が含まれます）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数読み込み / Settings
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

kabusys/ai/
- news_nlp.py              — ニュース NLP（OpenAI）による ai_scores 書込み
- regime_detector.py       — 市場レジーム判定

kabusys/monitoring/
- monitoring_db.py         — SQLite 層（schema 初期化・永続処理）
- system_monitor.py        — システム状態 / データ鮮度監視
- trade_monitor.py         — （滞留注文 / 約定異常等の監視）※実装ファイルあり
- risk_monitor.py          — ドローダウン・ポジション上限監視
- kill_switch.py           — kill.flag の生成・管理
- monitoring_engine.py     — 各 Monitor の統合ランナー
- alert_manager.py         — アラート送信ロジック（LINE 等）※実装ファイルあり

kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py

kabusys/research/
- factor_research.py
- feature_exploration.py

kabusys/tools/
- paper_verification_report.py

kabusys/utils/
- logging_setup.py
- process_priority.py

data/
- デフォルトで使用される SQLite / PID / フラグファイル等（実行時に作成）
logs/
- ログファイル出力先（デフォルト）

貢献 / 拡張ポイント
-------------------
- ブローカークライアントの追加（実ブローカー接続プラグイン）
- 戦略設定（config/*.yaml）やログ分析の強化
- 単体テスト、CI（特に AI 呼び出し部分のモック化）
- 銘柄別 lot_size 対応、手数料モデルの詳細化

参考コマンド一覧
----------------
- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

最後に
-----
この README はコード内ドキュメントと注釈を元に作成しています。実運用前に必ず python -m kabusys.validate_config で設定をチェックし、.env の秘匿情報は安全に管理してください。質問や追記したい内容があればお知らせください。