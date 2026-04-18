# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋起動スクリプト群）の README。  
このドキュメントはリポジトリ内の主要な機能、セットアップ・起動手順、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: 実際の運用では .env に機密情報（API トークン・パスワード等）を含め、絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム売買を想定したモジュール群です。主な役割は以下です。

- データ処理・研究（DuckDB を使ったファクター計算や特徴量解析）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
- Execution Engine（発注ロジック。本番 / ペーパートレード分離）
- モニタリング（システム状態・注文状況・リスク監視、Kill Switch）
- AI 支援（ニュースセンチメント、レジーム判定）  
- ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、設定検証 等）

設計方針として、データ計算は DuckDB、監視や永続化は SQLite、実際のブローカー呼び出しは抽象化／ファクトリ経由で扱われます。ペーパートレード時は本番 DB と分離して記録します。

---

## 主な機能一覧

- 環境設定管理
  - 対話式 .env 作成ウィザード: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`

- 起動スクリプト
  - ExecutionEngine 起動: `run_execution.py`
    - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し DB を分離
    - 停止は data/stop_requested.flag / kill.flag / pid ファイルで制御
  - Monitoring 起動: `run_monitoring.py`
    - システム・データ鮮度・注文リスクのポーリング
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）

- モニタリング
  - system_monitor: CPU・メモリ・ディスク・プロセス・データ鮮度を監視
  - trade_monitor: 注文滞留・約定異常などを検出（trade_logs 参照）
  - risk_monitor: ドローダウンやポジション上限をチェック、リスクログ記録
  - KillSwitch: 条件により data/kill.flag を作成して ExecutionEngine を停止

- ポートフォリオ構築
  - 候補選定、等金額／スコア重み、リスクに基づくポジションサイズ計算
  - セクター制限・レジーム乗数の適用

- 研究用（Research）
  - ファクター計算（モメンタム／バリュー／ボラティリティ）
  - 前方リターン、IC 計算、統計サマリ

- AI（OpenAI）
  - ニュースのセンチメントを LLM で評価して ai_scores に記録（news_nlp）
  - ETF とマクロニュースで市場レジーム判定（regime_detector）
  - 失敗時はフェイルセーフ（例: API 失敗で中立スコア 0 を採用）

- ツール
  - ペーパートレード検証レポート生成スクリプト（paper_verification_report）

---

## 必要な依存パッケージ（例）

最低限必要な主要ライブラリ:

- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config ファイル検証を行う場合）

インストール例（仮に requirements.txt を用意する場合）:
- pip install duckdb psutil openai pyyaml

（プロジェクトに requirements があればそちらを使用してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

3. 対話式に .env を作成（推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って J-Quants トークン、Kabu API パスワード 等を入力して保存

4. 設定を検証
   - python -m kabusys.validate_config
   - 問題が指摘されたら .env や config/*.yaml を修正

5. データディレクトリの準備（必要なら）
   - data/（SQLite やログの保存先）
   - logs/（ログディレクトリは自動作成されますが、権限等で問題があれば手動作成）

---

## 環境変数（主要なもの）

主な環境変数とデフォルト値・役割:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI 呼び出しに必要（AI 機能）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト `development`）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB: data/monitoring.db（monitoring は環境にかかわらず本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading 用の約定モード: instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒・デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか (0/1、デフォルト 0)

※ .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基に行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 起動 / 実行方法

コマンドはパッケージモジュールとして実行できます。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict オプションで警告を FAIL 扱いにできます

- ExecutionEngine 起動（本番 / ペーパー共通）
  - python -m kabusys.run_execution
  - 動作中は data/execution.pid が作成され、停止は data/stop_requested.flag または data/kill.flag 等で制御されます
  - KABUSYS_ENV=paper_trading の場合、MockBroker が使われ data/paper_trading.db に記録されます

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で指定可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に settings.sqlite_path（本番 DB path）を使用します

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別の DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュールの呼び出し（スクリプトや REPL から利用）
  - 例: python -c "from kabusys.ai.news_nlp import score_news; import duckdb, datetime, os; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date(2026,4,1), api_key=os.getenv('OPENAI_API_KEY')))"

注意: AI 関連は OpenAI API キーが必要です。API 呼び出しはリトライ・フェイルセーフ等の仕組みが入っていますが、課金やレート制限に注意してください。

---

## ログとファイル（運用上の重要点）

- ログ: logs/<app_name>.log（TimedRotatingFileHandler で日次ローテーション、バックアップ 30 日）
  - setup_logging(app_name="execution" | "monitoring") で統一設定
- PID / Stop flag:
  - data/execution.pid — ExecutionEngine の PID（設定によりパス変更可）
  - data/stop_requested.flag — ローカル停止フラグ。run_execution/run_monitoring が検知して終了します
  - data/kill.flag — Kill Switch により書き込まれる停止フラグ（手動／自動で書かれる）
- DB:
  - DuckDB: デフォルト data/kabusys.duckdb（分析用）
  - SQLite (監視): data/monitoring.db
  - SQLite (paper_trading): data/paper_trading.db（ペーパートレード用に分離）

---

## 開発用ユーティリティ

- 設定検証は config/*.yaml（system_config.yaml 等）も検査します。PyYAML が無い場合は YAML 検証はスキップされます。
- scripts/generate_config.py（参照あり）で config/*.yaml の雛形を作成できる想定（リポジトリにあれば利用してください）。

---

## ディレクトリ構成（概要）

以下は主要なモジュールと役割のツリー（src/kabusys 配下）:

- kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / 設定管理（Settings クラス）
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト

  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
    - __init__.py

  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — システム監視（CPU/メモリ/ディスク/データ鮮度/プロセス）
    - trade_monitor.py — 注文監視（滞留 / 約定異常 等）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各モニタの統合エンジン
    - alert_manager.py — （アラート送信の実装）※コード内参照あり

  - execution/
    - broker_factory.py — ブローカークライアント生成
    - execution_engine.py — ExecutionEngine 本体
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 実行系コンポーネント

  - portfolio/
    - portfolio_builder.py — 候補選定・重み
    - position_sizing.py — 株数算出、aggregate cap
    - risk_adjustment.py — セクター上限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — モメンタム / バリュー / ボラティリティ ファクター計算
    - feature_exploration.py — 将来リターン / IC /統計サマリ
    - __init__.py

  - data/
    - pipeline.py / stats.py / ...（データ取得・補助関数群 — DuckDB 操作用）

  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py — 市場レジーム判定（ETF + マクロニュース）
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
    - __init__.py

（実際のファイル数や追加ディレクトリはリポジトリの内容によります。上は主要ファイルの役割説明です）

---

## 運用上の注意 / FAQ

- 監視（run_monitoring）は常に Settings.sqlite_path を使うため、KABUSYS_ENV に関わらず監視用 DB は production path を参照します。ペーパートレードの検証は tools の paper_verification_report を使って paper_trading DB を指定してください。
- ペーパートレードと本番は DB を分離する設計です（PAPER_TRADING_SQLITE_PATH を設定）。
- Kill Switch（データベースのリスク検知での kill.flag）は冪等で動作します。運用時に KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動消去されますが、本番では 0（クリアしない）を推奨します。
- OpenAI や外部 API を使う機能はネットワーク失敗時にリトライやフェイルセーフを備えていますが、API 利用料・レート制限に注意してください。

---

## 参考コマンド例まとめ

- .env 作成（対話式）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動:
  - python -m kabusys.run_execution

- Monitoring 起動（ポーリング間隔 30 秒に変更）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

この README はソース内の docstring・コメントを元に作成しています。より詳細な設計情報や運用手順（デプロイ、サービス化、監視アラートの受け取り先設定 等）は別途ドキュメントを用意してください。必要であれば README に含める追加情報（例: systemd サービスファイル例、Docker 化手順、CI 設定など）を作成します。