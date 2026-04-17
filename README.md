# KabuSys

KabuSys は日本株向けの自動売買フレームワーク（プロトタイプ）です。銘柄選定・ポジションサイズ計算、実行エンジン、監視・アラート、研究用ファクター計算、AI（ニュースの NLP）など、取引システムの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

- Python ベースの自動売買基盤（日本株向け）。
- DuckDB を用いた研究・分析データ、SQLite を用いた監視・発注ログ。
- 本番（live）／ペーパー（paper_trading）／開発（development）の実行モードをサポート。
- OpenAI を利用したニュースセンチメント評価や市場レジーム判定機能を搭載（APIキー必要）。
- 監視モジュール（System / Trade / Risk）により稼働状況やリスクをログ/通知し、必要時に Kill Switch を発動して Execution を停止可能。

---

## 主な機能一覧

- 実行（ExecutionEngine）
  - 本番は実際のブローカークライアント、ペーパーは MockBroker（DB を分離して記録）。
  - 注文管理、リスク管理、オーダーの調整（Reconciler）を備える。

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor: 滞留注文（stale orders）、約定異常（価格偏差）監視
  - RiskMonitor: ドローダウン・ポジション上限の検出とログ化
  - KillSwitch: 重大リスク時に flag ファイルを書いて ExecutionEngine に停止シグナルを送信
  - MonitoringEngine: 各 Monitor をまとめてポーリング、アラート送信（AlertManager 経由）

- ポートフォリオ構築
  - 候補選定、等重・スコア重み、セクターキャップ、レジーム乗数、ポジションサイズ算出（単元株丸め、利用可能現金のスケール調整など）

- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー、将来リターン計算、IC（情報係数）計算、ファクター統計サマリ

- AI（OpenAI）連携
  - ニュース記事のセンチメントを LLM でスコアリング（ai_scores テーブルへ書込）
  - マクロニュース + ETF MA200 乖離を用いた市場レジーム推定

- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）

- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）

---

## セットアップ手順（例）

前提: Python 3.10+（タイプヒント等を利用しているため）、git が利用可能であること。

1. リポジトリをクローン
   - git clone <リポジトリ URL>
   - cd <project_root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai
   - 解析用/設定検証のため PyYAML を利用するなら: pip install PyYAML

   （プロジェクトに requirements.txt があればそれを利用してください）

4. .env の作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照して必要な値を設定）
   - 自動ロード:
     - パッケージ起動時、プロジェクトルートに .env / .env.local があれば自動で読み込まれます。
     - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリの確認
   - デフォルトでは data/ 以下に SQLite / DuckDB / PID / flag ファイルが置かれます（環境変数で上書き可）。
   - 必要に応じてディレクトリを作成してください（多くの実行時処理で自動作成されますがパーミッションに注意）。

---

## 主要な環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行モード
  - KABUSYS_ENV: development|paper_trading|live（デフォルト: development）

- データベース / ファイルパス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)  — Monitoring 用
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 用 SQLite
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)

- Paper Trading
  - PAPER_FILL_MODE: instant|partial|never|reject（デフォルト: instant）

- モニタリング
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60 秒）

- ログ / その他
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - OPENAI_API_KEY: OpenAI を使う場合に必要（ai/news_nlp, ai/regime_detector）

---

## 使い方（主要コマンド）

- 環境作成ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し paper_trading.db に記録（本番 DB と分離）。
    - 起動前に data/stop_requested.flag があると起動をスキップします。
    - 停止は data/stop_requested.flag を作成するか（スクリプトが参照）、Kill Switch (data/kill.flag) を利用します。

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
    - 監視は設定にかかわらず monitoring 用の sqlite_path を使用します（本番 DB を参照）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）

- Kill / Stop の操作
  - ExecutionEngine を外部から停止したい場合:
    - Kill Switch を発動するために data/kill.flag を作成（KillSwitch が存在を検知して Execution を停止）。
    - 実行プロセス自体を停止（run_execution は stop_requested.flag も監視しているため stop_requested.flag を作ることでループが終了します）。
  - 注意: .env の設定 KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険（自動クリアされます）。

---

## 実行モードの挙動（簡単）

- development
  - 発注は行わない（ローカル開発向け）
- paper_trading
  - MockBroker を使い、発注はペーパー DB（PAPER_TRADING_SQLITE_PATH）に記録
- live
  - 実際のブローカー API を用いて注文を送信（設定は慎重に）

---

## トラブルシューティング / 注意点

- 必須の環境変数未設定で起動すると ValueError が発生します。validate_config で事前チェックしてください。
- .env は絶対にリポジトリにコミットしないでください（ConfigSetup ウィザードのヘッダにも注意喚起あり）。
- OpenAI 連携を使う機能は OPENAI_API_KEY が必要です。未設定の場合は該当関数が例外を送出します。
- psutil を使ったプロセス優先度変更は OS と権限による制約があります（Linux では sudo が必要な場合あり）。失敗してもログに警告を出してスキップします。
- DuckDB / SQLite のバージョンや API 互換性により executemany の空リスト等に注意（コード中にワークアラウンドあり）。
- 監視や KillSwitch による停止はファイルベース（data/kill.flag, data/stop_requested.flag）です。自動クリアや誤消去に注意してください。

---

## ディレクトリ構成（主要ファイル）

（project_root = src ディレクトリの親）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - order_record.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
    （Execution 関連の実装）

  - monitoring/
    - monitoring_db.py       — SQLite の永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    （監視・KillSwitch・アラート関連）

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - ai/
    - news_nlp.py             — ニュースの NLP（OpenAI）
    - regime_detector.py      — マクロ + MA200 によるレジーム判定

  - tools/
    - paper_verification_report.py

  - utils/
    - process_priority.py     — プロセス優先度・CPU affinity ユーティリティ

- data/                      — 実行時に使用される各種 DB / flag / pid（デフォルト）
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - kill.flag
  - stop_requested.flag

---

## 開発メモ / 将来的な拡張点（コード内コメント抜粋）

- position_sizing は将来的に銘柄別の lot_size 対応を想定（現在は一律 100）。
- sector cap の exposure 計算で価格欠損時のフォールバックを改善する余地あり。
- AI 呼び出しはリトライ戦略を実装済みだが、レスポンスの堅牢性向上（フォーマットの厳密化・検証）に余地あり。
- DuckDB の一部操作はバージョン依存の挙動（executemany の空リストなど）を回避するために工夫している。

---

必要であれば、README に「実行例」や「.env のサンプル」などのセクションを追加できます。どの情報を補足しましょうか？