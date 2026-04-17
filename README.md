# KabuSys

日本株向け自動売買システムのライブラリ群 / 実行コンポーネント群です。  
モジュール構成は「発注実行（ExecutionEngine）」「監視（Monitoring）」「ポートフォリオ構築」「リサーチ（ファクター計算）」「AI（ニュース NLP / レジーム判定）」等に分かれ、SQLite / DuckDB を使ってデータ永続化と分析を行います。

---

## 主な特徴（機能一覧）

- 設定管理
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 起動前の設定検証 CLI（kabusys.validate_config）
  - .env 自動ロード（`.env` → `.env.local`、OS 環境変数優先）
- 実行（Execution）
  - ExecutionEngine（本番 / ペーパートレード切替）
  - Broker クライアントファクトリ（本番/モック切替）
  - リスクマネージャ、オーダーマネージャ、Reconciler 等
  - 停止制御：PID / stop flag / kill flag による安全停止
- 監視（Monitoring）
  - SystemMonitor：プロセス生存、CPU/メモリ/ディスク、データ鮮度検査
  - TradeMonitor：滞留注文・約定異常検出
  - RiskMonitor：ドローダウン・保有上限監視、ダッシュボード更新
  - KillSwitch：重大リスク時に kill.flag を書き込んで ExecutionEngine を停止
  - MonitoringEngine：上記を定期ポーリングしてアラート発行
- ポートフォリオ構築（純粋関数）
  - 候補選定、等重配分 / スコア重み、ポジションサイズ計算、セクターキャップ、レジーム補正
- リサーチ（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Information Coefficient）等の統計ユーティリティ
- AI 統合
  - ニュース NLP（OpenAI）による銘柄ごとのセンチメント算出（ai.news_nlp）
  - レジーム判定（ETF MA + マクロニュースの LLM 評価の合成）
  - OpenAI 呼び出しはリトライ/バリデーション等の耐障害性を備える
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定（psutil ベース）
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）

---

## 前提 / 必要パッケージ

- Python 3.10+
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML をチェックしたい場合）
- インストールはプロジェクトに合わせた requirements.txt を用意している想定：
  - pip install -r requirements.txt

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートに移動
2. 仮想環境を作成して依存パッケージをインストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -r requirements.txt
3. 環境変数ファイルの作成
   - 対話式ウィザードを使う（.env を生成）
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照）
4. 設定の検証
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict
5. data ディレクトリ等の作成（必要に応じて）
   - デフォルト DB パス: data/kabusys.duckdb, data/monitoring.db
   - paper trading 用 DB: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）

重要な環境変数（一部）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 専用 DB。デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、run_monitoring 用、デフォルト 60）
- PAPER_FILL_MODE（paper_trading 時のモック約定挙動: instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START（本番での Kill フラグ自動クリア: 0/1。0 推奨）

自動 .env の読み込み
- 起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探し、
  .env → .env.local を読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要コマンド・実行例）

### 環境セットアップ / 検証
- 対話式で .env を生成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

### ExecutionEngine を起動
- 通常（開発）:
  - python -m kabusys.run_execution
- ペーパートレード（環境切替）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - ※ paper_trading の場合は MockBrokerClient を使い、デフォルトで data/paper_trading.db に記録されます（production DB と分離）。
- 停止方法:
  - 実行中の終了はプロセスの KeyboardInterrupt（Ctrl+C）。
  - 外部から停止指示を出すにはプロジェクトルートの data/stop_requested.flag を作成（run_execution はこのフラグを検出して安全停止します）。
  - KillSwitch による停止: monitoring が条件を満たすと data/kill.flag を書き込み、Engine がこれを検出して停止します。
- PID/フラグ
  - data/execution.pid: ExecutionEngine の PID を記録（存在チェックにより stale PID を検出）
  - data/stop_requested.flag: 外部停止リクエスト
  - data/kill.flag: KillSwitch による停止フラグ

### Monitoring を起動
- 単体起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL によってポーリング間隔を上書き可能（秒、デフォルト 60）
  - 注意: run_monitoring は監視用の sqlite_path（Settings.sqlite_path）を常に使用します（KABUSYS_ENV に依存しない）
- テスト用に MonitoringEngine を使って1回だけ実行するなど、ユニットテストが容易な設計です。

### Paper Trading 検証レポート
- レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 簡易的に稼働率 / 注文成功率 / レイテンシ等の指標を出力します。

### AI 機能（ニュース NLP / レジーム判定）
- OPENAI_API_KEY を設定しておくこと
- プログラムから呼ぶ例:
  - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
- レスポンス検証やリトライが組み込まれており、API 失敗時はフェイルセーフ（スコア 0.0 など）で継続します。

---

## 重要な仕様メモ / 運用注意

- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（validate_config で検出）
- KABUSYS_ENV の値: development / paper_trading / live。live は本番のため注意深く設定してください（validate_config は live 時の追加チェックを実施）。
- Paper trading は本番 DB と分離される（PAPER_TRADING_SQLITE_PATH）。
- Monitoring は監視用 sqlite DB を使用（デフォルト data/monitoring.db）。run_monitoring は常に Settings.sqlite_path を使います。
- OpenAI を使う機能は OPENAI_API_KEY を参照します。未設定だと例外またはフォールバック挙動になります。
- .env は Git に絶対にコミットしないこと（config_setup でもその注意書きがあります）。
- プロセス優先度設定は psutil を使いプラットフォーム差分を吸収します。権限不足時は警告でスキップされます。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル/ディレクトリは次の通りです（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前の設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装あり)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py
  - execution/                 — Execution 関連（OrderRepository 等、参照あり）
  - data/                      — 実行時に使用する DB/フラグ等（data/monitoring.db など）
  - config/                    — config/*.yaml（テンプレート / 実際の設定ファイル）

（本 README はソース内の docstring / コメントに基づいて要約しています。詳細は各モジュールの docstring を参照してください。）

---

## 開発者向けメモ

- DuckDB 接続は分析向けテーブル（prices_daily, raw_financials, raw_news 等）を参照する設計です。AI / リサーチからは DuckDB 接続を受け取る純粋関数群が多く、外部副作用を避けています。
- monitoring_db.py は SQLite のスキーマ初期化・マイグレーションロジックを持ち、冪等性を重視しています。
- OpenAI の呼び出し箇所はテスト用に _call_openai_api を patch してモック可能です。
- .env の自動ロードはプロジェクトルート検出機能を使うため、CWD に依存しない作りです。CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して自前で環境を制御してください。

---

この README はコード中の docstring と設計コメントを基にまとめています。実運用時は必ず python -m kabusys.validate_config で設定を検証し、KABUSYS_ENV=live の場合は慎重に .env と kill flag の設定を確認してください。