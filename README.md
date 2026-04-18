# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋起動スクリプト群）

このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AIを使ったニュース解析など、実運用を想定した機能群を含みます。モジュール設計はテスト・研究用途と本番運用を分離する方針に基づいています。

---

## プロジェクト概要

- ExecutionEngine：ブローカークライアント経由で発注を行う本体（本番 / ペーパートレードをサポート）。
- Monitoring：システム状態・注文状態・リスクを監視し、Kill Switch（フラグファイル）で発注エンジンを安全に停止可能。
- Portfolio：銘柄選定・重み付け・株数決定などの純粋関数群（DBに依存しない）。
- Research：DuckDB を使ったファクター計算・特徴量探索ユーティリティ。
- AI：OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・市場レジーム判定。
- Tools：ペーパートレード検証レポート生成などのユーティリティスクリプト。
- 設定ユーティリティ：対話式 .env ウィザードと設定検証 CLI。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートに基づく）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行 / 発注
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - Paper trading（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、データは分離された SQLite に保存

- 監視 / アラート
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / 発注プロセスの存否チェック
  - TradeMonitor：滞留注文・約定異常等の検出（trade_logs 参照）
  - RiskMonitor：ドローダウン、ポジション上限監視（dashboard / positions 参照）
  - KillSwitch：条件満たした場合に data/kill.flag を書き込み ExecutionEngine を停止
  - Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - 監視ログ永続化：SQLite（monitoring.db）用の層（monitoring_db.py）

- ポートフォリオ構築（純粋関数）
  - 候補選定、等金額・スコア重み、リスクベースのポジションサイズ計算
  - セクターキャップ、レジームに応じた資金乗数

- リサーチ
  - DuckDB を使ったファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 前方リターン計算、IC（Information Coefficient）や統計サマリー

- AI（OpenAI）
  - ニュースの銘柄別センチメントを LLM で評価して ai_scores テーブルへ書き込み
  - マクロニュースと ETF ma200 に基づく市場レジーム判定（market_regime テーブル）

- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

前提：
- Python 3.9+（プロジェクトの互換性に合わせてください）
- 必要な外部ライブラリ（下記参照）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成・有効化（任意だが推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install -r requirements.txt
   ※ requirements.txt がない場合、主に以下を想定してください:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で利用。任意）
   （プロジェクトに合わせて必要パッケージを追加してください）

4. .env の作成
   - 対話式ウィザードを使う（推奨）
     python -m kabusys.config_setup
   - または .env.example（存在する場合）を参考に .env を作成

5. 設定検証
   python -m kabusys.validate_config
   --strict オプションを付けると警告も FAIL 扱いになります:
   python -m kabusys.validate_config --strict

6. ディレクトリ作成
   ログとデータディレクトリは自動作成されますが、事前に用意しておきたい場合：
   mkdir -p data logs

注意:
- 必須環境変数：
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- OpenAI を利用する機能を使う場合：
  - OPENAI_API_KEY を .env に設定してください

主要な環境変数（抜粋）:
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト、monitoring 用）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: ログレベル（INFO 等）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

---

## 使い方

以下は主要なスクリプト・コマンド例です。

- 対話式設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループ起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で上書きできます（デフォルト 60 秒）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を参照します（環境に依らず本番パスを使う仕様）。
  - 停止はプロジェクトルートの data/stop_requested.flag ファイルを作成すると検知して終了します。

- 実行エンジン起動（発注）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）。
  - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に停止をリクエストする場合は data/stop_requested.flag を作成してください。

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルトの DB は data/paper_trading.db。--db で別パスを指定可能。

- AI モジュール（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...) が返す接続）を受け取り、DB のテーブル（raw_news, news_symbols, ai_scores, prices_daily 等）を参照・更新します。

ログ:
- デフォルトは logs/<app_name>.log に日次ローテーションで出力（TimedRotatingFileHandler）。
- コンソールは stdout に出力されます。
- setup_logging() でアプリケーション共通のログ設定を行います。

停止 / Kill Switch:
- KillSwitch はリスク条件を満たすと data/kill.flag を書き込み、ExecutionEngine がこれを検出して停止します。
- ExecutionEngine の PID ファイルは data/execution.pid（Settings.pid_file_path）等で管理されます。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番では推奨されません）。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル・モジュール構成例:

src/kabusys/
- __init__.py
- config.py                # 環境変数 / Settings
- config_setup.py          # 対話式 .env ウィザード
- validate_config.py       # 設定検証 CLI
- run_monitoring.py        # Monitoring 起動スクリプト
- run_execution.py         # ExecutionEngine 起動スクリプト

- ai/
  - news_nlp.py            # ニュース NLP スコアリング
  - regime_detector.py     # 市場レジーム判定

- monitoring/
  - monitoring_db.py       # SQLite 永続化層（system_status / trade_logs / risk_logs / dashboard / positions）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py       # （アラート通知の責務を持つ想定）

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

- tools/
  - paper_verification_report.py

- utils/
  - logging_setup.py
  - process_priority.py

トップレベル（ワークツリー）
- data/                    # 実行時に使用する DB・フラグファイル等（デフォルト）
  - monitoring.db
  - paper_trading.db
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/                    # ログファイル出力先（デフォルト）
  - execution.log
  - monitoring.log
- .env                     # 環境変数ファイル（.git にコミットしないこと）

---

## 開発上の注意・設計方針（抜粋）

- 設定の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行うため、CWD に依存せず動作する。
- Paper trading と本番データベースは分離される（PAPER_TRADING_SQLITE_PATH）。
- AI 呼び出しはリトライ・バックオフやレスポンス検証を内包し、失敗時はフォールバックやスキップでフェイルセーフに設計。
- ポートフォリオ / ポジション算出は純粋関数で副作用を持たない（単体テストが容易）。
- ログは stdout と日次ローテーションファイルに出力する統一的な仕組みを提供。
- プロセス優先度や CPU affinity の設定ユーティリティがあり、起動時に優先度を High に上げる処理が各起動スクリプトで行われる。

---

## よく使うコマンドまとめ

- .env を作る（対話式）
  python -m kabusys.config_setup

- 設定の検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視プロセス起動
  python -m kabusys.run_monitoring

- 発注エンジン起動
  python -m kabusys.run_execution

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に記載のない内部 API や細かい動作（テーブルスキーマ、各関数の引数仕様等）はソースコード内の docstring を参照してください。必要であれば、README を拡張して具体的な運用手順やデプロイ手順（systemd / supervisor / Docker など）を追記できます。