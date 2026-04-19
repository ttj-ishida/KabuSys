# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行コンポーネント群）。

このリポジトリは取引エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ、AI（ニュースのセンチメント評価）などの機能を含んだ自動売買プラットフォームのコア実装群を提供します。

---

## プロジェクト概要

- 実行コンポーネント（ExecutionEngine）: 発注・注文管理・リスク管理を行う実行エンジン。
- 監視コンポーネント（MonitoringEngine）: システム稼働状況、注文・約定、リスク（ドローダウン / ポジション上限）を定期チェックしてログ・アラート・Kill Switch を管理。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ決定、セクターキャップ・レジーム調整などの純粋関数群。
- リサーチ: DuckDB 上の価格・財務データに基づくファクター計算・特徴量解析ツール。
- AI モジュール: OpenAI API を使ったニュースのセンチメント（銘柄ごと／マクロ）計算と市場レジーム判定。
- ユーティリティ: ログ設定、プロセス優先度／CPU affinity、.env ウィザード、設定検証、ツール類（Paper Trading の検証レポート等）。
- 永続化: DuckDB（分析用）・SQLite（監視 / 発注ログ用）を使用。多くのテーブルは起動時に自動生成・マイグレーションされる。

---

## 主な機能一覧

- Execution
  - 実際のブローカークライアントまたは Paper Trading 用 MockBroker による注文実行
  - OrderManager / Reconciler / RiskManager による注文制御とリスク制御
- Monitoring
  - CPU / メモリ / ディスク・プロセス稼働検出
  - データ鮮度（価格データ）チェック
  - 滞留注文・約定異常・ドローダウンやポジション上限の検出
  - Kill Switch による安全停止（kill.flag）
- Portfolio
  - 候補選定、等配分／スコア配分、リスクベース配分、セクター制限、レジーム乗数
- Research
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン・IC（Information Coefficient）計算や統計サマリ
- AI
  - ニュース記事をまとめて LLM に投げ、銘柄別スコアを ai_scores に保存
  - マクロニュース＋ETF MA200 による市場レジーム判定
- ツール
  - 環境設定ウィザード（.env 作成）
  - 設定検証 CLI（.env と config/*.yaml の検査）
  - Paper Trading 検証レポート生成スクリプト

---

## 必要条件（例）

- Python 3.9+
- 推奨パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証時）
- そのほか、ブローカークライアントに依存する追加パッケージがある場合あり

※ requirements.txt がある場合はそれを利用してください:
pip install -r requirements.txt

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （ある場合）pip install -r requirements.txt
4. 環境変数設定（.env）
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくはルートに .env を作成して必要なキーを設定する
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 一般的な設定キー:
       - KABUSYS_ENV (development | paper_trading | live)
       - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
       - SQLITE_PATH (デフォルト: data/monitoring.db)
       - PAPER_TRADING_SQLITE_PATH (Paper Trading 用 DB, デフォルト: data/paper_trading.db)
       - LOG_LEVEL (DEBUG/INFO/...)
       - OPENAI_API_KEY（AI 機能を使う場合）
       - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用）
       - KILL_FLAG_CLEAR_ON_START (0/1)
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告を厳格に扱いたい場合: python -m kabusys.validate_config --strict
6. データディレクトリの作成（必要に応じて）
   - data/（デフォルトの DB / PID / フラグファイル配置）

---

## 環境変数（代表的なもの）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- LOG_LEVEL — ログレベル（例: INFO）
- LOG_DIR — ログファイル出力先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒, default: 60）※ run_monitoring で使用
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか (0/1)

---

## 実行方法（主要コマンド）

- ExecutionEngine を起動（実取引または Paper Trading）:
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - エンジンは別スレッドで run_session を実行し、stop は data/stop_requested.flag と ExecutionEngine.stop() で行う
    - 実行中は PID ファイルを data/execution.pid に書きます

- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定（デフォルト 60 秒）
    - 監視は本番 sqlite_path を使用（環境に依らず同じ監視 DB を参照）
    - 停止は data/stop_requested.flag を作成して通知

- 環境設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗として exit(1)

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）

---

## 停止 / Kill Switch の取り扱い

- stop_requested.flag
  - run_execution / run_monitoring の起動スクリプトはこのファイルの存在を監視し、存在するとループを抜けて安全終了します。
  - ファイルパス: プロジェクトの data/stop_requested.flag

- kill.flag（Kill Switch）
  - RiskMonitor / KillSwitch の評価で危険が検知された場合に data/kill.flag に理由を出力して ExecutionEngine を停止させる仕組みです。
  - 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤って自動クリアしないため）。

---

## ログ

- ログはデフォルトで stdout とファイル（logs/<app_name>.log）へ出力されます。
- 日次ローテーション・30日分保持が設定されています。
- ログ出力設定は kabusys.utils.logging_setup.setup_logging を通して行われます。
- LOG_DIR 環境変数でログ保存先を変更可能。

---

## 主要なディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル・モジュール構成の要約です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理
  - config_setup.py                — .env ウィザード CLI
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py             — SQLite 監視 DB 永続化層
    - system_monitor.py            — システム監視
    - trade_monitor.py             — 注文/約定監視（該当ファイル）
    - risk_monitor.py              — ドローダウン・ポジション監視
    - monitoring_engine.py         — モニタリング統合エンジン
    - kill_switch.py               — Kill Switch 書き込みロジック
    - alert_manager.py             — アラート送信管理（該当ファイル）
  - execution/
    - execution_engine.py          — 実行エンジン本体
    - order_manager.py             — 注文管理
    - order_repository.py          — 注文レポジトリ / DB
    - broker_factory.py            — ブローカークライアント生成
    - reconciler.py                — ブローカーとの整合処理
    - risk_manager.py              — リスク制御
  - portfolio/
    - portfolio_builder.py         — 候補選定 / 重み計算
    - position_sizing.py           — 株数計算 / 集約制限
    - risk_adjustment.py           — セクター制限 / レジーム乗数
  - research/
    - factor_research.py           — ファクター計算（momentum/value/volatility）
    - feature_exploration.py       — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py                  — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py           — マクロ+MA200 によるレジーム判定

（実際のファイルは src/kabusys 以下に展開されています）

---

## 開発・デプロイの注意点

- KABUSYS_ENV により挙動が変わります:
  - development: 開発用（発注なし等）
  - paper_trading: MockBroker を用いる（paper DB に記録）
  - live: 実際の発注が行われるため設定を慎重に確認すること
- 本番環境での Kill Switch / アラート設定は必ず確認してください（LINE 設定等）。
- DuckDB / SQLite のパスは環境変数で上書き可能です。データファイルのバックアップ方針を検討してください。
- OpenAI を利用する機能は API コストとレイテンシ・エラーを考慮して運用してください（実装側でバックオフ等を実施していますが、使用ポリシーに注意）。

---

## 参考コマンドまとめ

- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

README はここまでです。さらに詳細な API ドキュメント（関数引数や戻り値の説明、内部 DB スキーマ等）が必要であれば、対象モジュールを指定していただければ個別に詳述します。