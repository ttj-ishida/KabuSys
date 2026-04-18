# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリはトレードの実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント）等のコンポーネントを含むモジュール群です。各コンポーネントは可能な限りフェイルセーフかつ冪等（idempotent）に設計されています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動 / 各種コマンド）
- 環境変数（主要項目）
- ファイル / ディレクトリ構成

---

プロジェクト概要
- トレード実行（ExecutionEngine）とその監視（Monitoring）を行う Python コード群
- DuckDB を使った分析向けデータ、SQLite を使った監視・注文履歴保存
- Paper Trading モードを持ち、本番 DB と分離して検証可能
- ニュースを LLM（OpenAI）でセンチメント評価し、判定結果を格納する AI モジュール
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限等）
- 設定ウィザード（.env 生成）・設定検証ツール・紙上検証レポートジェネレータ等の CLI ユーティリティ

---

主な機能一覧
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて paper_trading（MockBroker）/ live を切り替え
  - paper_trading は専用 SQLite（data/paper_trading.db）を使用して本番と分離
- 監視ループ起動スクリプト（run_monitoring.py）
  - システム状態、データ鮮度、注文状況、リスク指標を定期的にチェックし SQLite に記録
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 停止フラグ（data/stop_requested.flag）検知によりループ終了
- 監視永続化層（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを管理
  - マイグレーション（カラム追加）を起動時に行う（冪等）
- Kill Switch（kill_switch.py）
  - ドローダウンやポジション制限トリガで data/kill.flag を書き込み ExecutionEngine を停止
- RiskMonitor / TradeMonitor / SystemMonitor / MonitoringEngine
  - 個別のチェックロジックとアラート発信（AlertManager 経由）
- AI モジュール
  - news_nlp: raw_news を OpenAI に送って銘柄ごとのセンチメント（ai_scores）を生成
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM スコアを合成して市場レジーム（bull/neutral/bear）を判定
- Research / Factor 計算
  - calc_momentum, calc_volatility, calc_value など DuckDB 上でファクターを計算
  - feature_exploration: 将来リターン、IC（Information Coefficient）等を計算
- Portfolio モジュール
  - 候補選定、等重／スコア重み、リスクに基づくポジションサイズ、セクターキャップ、レジーム乗数
- ユーティリティ
  - logging_setup: 統一ログ設定（console + 日次ローテートファイル）
  - process_priority: プロセス優先度（High など）や CPU affinity 設定
- 設定ツール
  - config_setup.py: 対話式で .env を生成・更新
  - validate_config.py: .env と config/*.yaml の整合性チェック
- 補助ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポートを出力

---

セットアップ手順（開発環境向け）
1. Python バージョン
   - Python 3.10 以上を推奨（型注釈や union 型を使用）

2. 必要パッケージ（例）
   - pip install duckdb psutil openai
   - PyYAML は config 検証時に利用（任意）: pip install pyyaml
   - 他に標準ライブラリ（sqlite3, threading, logging など）を使用

   具体例:
   pip install duckdb psutil openai pyyaml

3. ディレクトリ作成（初回）
   - data/ と logs/ を作成しておくと良い（自動作成も試みられます）
     mkdir -p data logs

4. .env を作成
   - 対話式ウィザードを使うと簡単です:
     python -m kabusys.config_setup
   - 自動ロード:
     - 起動時、プロジェクトルート（.git または pyproject.toml がある場所）から .env を自動読み込みします
     - .env.local があれば優先して上書き読み込み（OS 環境変数は保護）
     - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証
   - 生成・編集した .env を検証:
     python -m kabusys.validate_config
   - --strict を付けるとワーニングも失敗扱い:
     python -m kabusys.validate_config --strict

6. データベース初期化
   - 起動スクリプトが必要に応じて監視 DB のテーブル作成（init_monitoring_db）を行います
   - DuckDB ファイルは初回アクセス時に作成されます

7. OpenAI を使う場合
   - 環境変数 OPENAI_API_KEY を設定するか、該当関数に引数で渡す必要があります

---

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR（ログ出力先、デフォルト: logs/）
- OPENAI_API_KEY（AI モジュール用）
- PAPER_FILL_MODE（paper_trading の埋め方: instant/partial/never/reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1、デフォルト: 0）

注意:
- .env は決して Git にコミットしないこと（秘密情報を含む）

---

使い方（起動 / CLI）
- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - デフォルト（ポーリング 60 秒）:
    python -m kabusys.run_monitoring
  - ポーリング間隔を変更:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが検知して終了します

- 実行エンジン起動（Execution）
  - 本番 / paper_trading は KABUSYS_ENV に依存:
    python -m kabusys.run_execution
  - paper_trading の場合、MockBroker を用い data/paper_trading.db に記録します
  - エンジン停止のためには data/stop_requested.flag を作成するか、kill.flag による停止シグナルを評価して停止します
  - 実行中は pid ファイル（デフォルト data/execution.pid）を作成します

- Paper Trading 検証レポート（ツール）
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
    --db PATH で paper_trading DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / リサーチ関数
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - research.calc_momentum(conn, date), calc_volatility, calc_value, calc_forward_returns, calc_ic などは DuckDB 接続を受け取って呼び出す

---

停止・Kill Switch の仕組み
- KillSwitch はリスク（ドローダウンやポジション数上限）により data/kill.flag を書き込みます
- ExecutionEngine は kill.flag の存在を検知して自動停止する設計
- run_monitoring / run_execution は data/stop_requested.flag により即時停止できるルーチンを持っています

---

ログ
- logging_setup.setup_logging(app_name="execution" 等) を利用
- 出力先:
  - コンソール（stdout）
  - 日次ローテートファイル: <LOG_DIR>/<app_name>.log（デフォルト logs/）
- 既定で 30 日分のローテーションを保持

---

ディレクトリ構成（主要ファイル）
（src/kabusys 以下を例示）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス、自動 .env 読み込みロジック
  - config_setup.py          — .env 対話型ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py        (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        (参照あり)
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に使用されるディレクトリ: SQLite/DuckDB, flag, pid)
  - config/ (外部 YAML 設定ファイルが置かれる想定: system_config.yaml 等)

補足:
- ファイル名や関数の多くはドメイン固有のロジックを分離しており、ユニットテストで差し替え可能（例えば OpenAI 呼び出しのラッパーをモック可能）
- DuckDB 接続は分析用テーブル（prices_daily / raw_financials / raw_news / ai_scores 等）を想定

---

よくある操作例（まとめ）
- 初期セットアップ:
  pip install -r requirements.txt   # requirements.txt がある場合
  mkdir -p data logs
  python -m kabusys.config_setup
  python -m kabusys.validate_config

- 監視をデーモン的に起動（開発）:
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジン起動（paper_trading）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

トラブルシューティング / 注意点
- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）が未設定だと起動前検証で FAIL になります
- .env の自動読み込みはプロジェクトルート検出が必要（.git または pyproject.toml）
- DuckDB / SQLite ファイルパスの親ディレクトリが存在しない場合は警告となり、起動時に自動作成される場合があります
- OpenAI 呼び出しでエラーが発生してもフェイルセーフでスコア計算は続行しますが、AI 部分の書き込みはスキップされることがあります

---

開発・拡張
- Execution / Broker 周り、OrderManager、Reconciler、RiskManager 等は実装の差し替えや拡張を想定したファクトリ/インターフェース設計
- DuckDB のスキーマや分析クエリは research 側で集中管理。テスト用データを用意して単体テストを実行してください

---

ライセンス・貢献
- 本 README にはライセンス情報を含めていません。実際の配布時は適切な LICENSE を追加してください。
- 貢献する際はテストと validate_config による検証を行い、.env 等の秘密情報をコミットしないでください。

---

この README はリポジトリ内のコードと docstring を元に作成しています。必要に応じて実行環境に合わせてパスや環境変数を調整してください。質問や追加ドキュメントが必要であればお知らせください。