# KabuSys

日本株向け自動売買システムのコアライブラリ / 実行スクリプト群です。  
本リポジトリは、シグナル計算・ポートフォリオ構築・発注エンジン・監視・AI（ニュースNLP / レジーム判定）・検証ツールを含む一連のコンポーネントで構成されています。

バージョン: 0.1.0

------------------------------------------------------------------------

## 概要

KabuSys は以下の役割を持つモジュール群から構成されます。

- シグナル / ファクター計算（research）
- ポートフォリオ構築（portfolio）
- 発注・注文管理・リスク管理（execution） — 実行エンジン
- 監視（monitoring） — システム状態・注文状態・リスク監視、Kill Switch
- AI モジュール（ai） — ニュースセンチメント、レジーム判定（OpenAI を利用）
- 設定ウィザード / 検証ツール / 検証レポート（config_setup、validate_config、tools）
- ユーティリティ（logging_setup、process_priority）

設計方針の一例:
- DuckDB / SQLite をデータ永続化に使用（DuckDB は分析、SQLite は監視/ペーパー取引用）
- Paper trading 環境は本番 DB とは完全分離（data/paper_trading.db を使用）
- .env（環境変数）を中心に設定管理。config_setup で対話的に .env を生成可能
- 本番起動時にプロセス優先度を上げる等の運用考慮あり

------------------------------------------------------------------------

## 機能一覧（主なもの）

- 設定関連
  - 対話式 .env ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config [--strict]

- 実行 / 監視
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用（paper_trading DB を使用）
    - 停止は data/stop_requested.flag、Kill Switch は data/kill.flag を利用
  - Monitoring 起動スクリプト: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60s）
    - 監視 DB（SQLite）は環境に関係なく本番 sqlite_path を使用

- 監視コンポーネント
  - SystemMonitor: CPU/Mem/Disk、実行プロセスの存在、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常などの検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限の監視、dashboard 更新、risk_logs 出力
  - KillSwitch: 条件発生時に data/kill.flag を書き込み Execution を停止させる

- ポートフォリオ / 建玉計算（純粋関数群）
  - 候補選定、等金額/スコア加重の重み計算
  - ポジションサイズ決定（単元株丸め、リスクベース等）
  - セクターキャップ・レジーム乗数

- リサーチ / ファクター
  - momentum / volatility / value 等のファクター計算（DuckDB 上の prices_daily/raw_financials を想定）
  - 将来リターン、IC（Spearman）計算、統計サマリー

- AI（OpenAI を利用）
  - news_nlp: ニュースを銘柄ごとに集約し LLM でセンチメントを算出 -> ai_scores に格納
  - regime_detector: ETF 1321 の MA200 乖離 と マクロニュースの LLM センチメントを合成して日次レジーム判定

- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

------------------------------------------------------------------------

## 前提 / 要件

- Python 3.10+（PEP604 の型注釈（|）等を使用）
- 必要な外部ライブラリ（主なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/ *.yaml の検証に任意で使用）
- SQLite（標準ライブラリで利用）
- ネットワーク接続（J-Quants API / kabuステーション / OpenAI を利用する機能を使う場合）

pip install の例（requirements.txt が無い場合の例）:
pip install duckdb psutil openai PyYAML

※ 実際の運用では requirements.txt を用意して pip install -r requirements.txt を推奨します。

------------------------------------------------------------------------

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、作業ディレクトリに移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考にすること）
   - 自動ロード: このライブラリはデフォルトでプロジェクトルートの `.env` / `.env.local` を自動読み込みします。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 厳密モード: python -m kabusys.validate_config --strict  （警告も失敗扱い）
6. データディレクトリ作成（必要に応じて）
   - data/（デフォルトの sqlite/duckdb/pid/flag ファイルはここに置かれる想定）
   - logs/（ログ出力先）

重要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番通知）
- LOG_LEVEL（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL（run_monitoring 用のポーリング秒数上書き）

PAPER_FILL_MODE（paper_trading の MockBroker 挙動）:
- instant | partial | never | reject（デフォルト "instant"）

------------------------------------------------------------------------

## 使い方（主要コマンド）

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（実際の発注 / ペーパートレード）
  - python -m kabusys.run_execution
  - 注意: 起動時に data/stop_requested.flag が存在すると起動しません
  - paper_trading モード: KABUSYS_ENV=paper_trading をセットすると MockBrokerClient を使用し、paper_trading 専用 DB に記録されます

- Monitoring を起動（定期監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db /path/to/paper_trading.db  もしくは env PAPER_TRADING_SQLITE_PATH を使用

- ライブラリ関数の利用例（Python import）
  - ポートフォリオ: from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - リサーチ: from kabusys.research import calc_momentum, calc_volatility, calc_value
  - AI スコアリング: from kabusys.ai.news_nlp import score_news  （引数は DuckDB 接続と日付）
  - レジーム判定: from kabusys.ai.regime_detector import score_regime

ログ:
- setup_logging() により stdout と logs/<app_name>.log（日次ローテーション）に出力されます。
- ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/ を使用します。

停止 / Kill Switch:
- 実行中の ExecutionEngine を監視から停止させるために、KillSwitch は data/kill.flag を作成します（監視が検出して書き込み）。
- 手動停止フラグ: data/stop_requested.flag（run_execution/run_monitoring は存在を監視して終了します）
- PID 管理ファイル: data/execution.pid（ExecutionEngine が PID を書きます）

------------------------------------------------------------------------

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings クラス、自動 .env ロード
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring 起動スクリプト

kabusys/utils/
- logging_setup.py          — ログ設定ユーティリティ
- process_priority.py       — プロセス優先度 / CPU affinity 設定

kabusys/monitoring/
- monitoring_db.py          — SQLite による監視ログ永続化
- system_monitor.py         — システム状態・データ鮮度監視
- trade_monitor.py          — 注文ログ監視（ファイル内にも存在）
- risk_monitor.py           — ドローダウン / ポジション上限監視
- kill_switch.py            — Kill Switch（kill.flag の作成）
- monitoring_engine.py      — 各監視を束ねるエンジン
- alert_manager.py          — （アラート送信の実装箇所）

kabusys/execution/
- execution_engine.py       — ExecutionEngine（発注セッション）
- order_manager.py
- order_repository.py
- reconciler.py
- risk_manager.py
- broker_factory.py

kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py

kabusys/research/
- factor_research.py
- feature_exploration.py

kabusys/ai/
- news_nlp.py               — ニュースNLP スコアリング（OpenAI）
- regime_detector.py        — レジーム判定（OpenAI）

kabusys/tools/
- paper_verification_report.py

その他:
- data/                     — データ/フラグ/DB の既定配置（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag）
- logs/                     — ログ出力先（setup_logging が生成）

------------------------------------------------------------------------

## 運用上の注意 / トラブルシューティング

- .env は絶対に Git にコミットしないでください（config_setup 内でも警告あり）。
- validate_config で必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）が未設定だとエラーになります。
- Paper trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH をご確認ください）。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライ・フォールバック処理がありますが、鍵の設定を忘れないでください。
- run_monitoring はデフォルトで本番 sqlite_path を使います（監視ログは本番 DB に記録される点に注意）。
- MONITOR_POLL_INTERVAL に不正な値（0 以下や非整数）を指定するとデフォルト（60 秒）にフォールバックされます。
- process_priority の設定や CPU affinity は OS や権限の制約で失敗する可能性があります（警告ログを確認してください）。
- DuckDB の SQL 実行や YAML パースは任意の外部パッケージ（duckdb, PyYAML）が必要です。validate_config は PyYAML が無ければ YAML 検証をスキップします。

------------------------------------------------------------------------

もし README に追加して欲しい内容（例: 実行例のスクリーンショット、API の詳細仕様、サンプル .env.example、開発フロー、テスト方法など）があれば教えてください。必要に応じて追記します。