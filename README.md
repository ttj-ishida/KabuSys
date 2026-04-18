# KabuSys

日本株自動売買システムの軽量ライブラリ群 / 実行スクリプト群のリポジトリドキュメント（README）。  
以下はソースコード（src/kabusys 以下）から抽出した概要・使い方・セットアップ手順です。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つ、自動売買・リサーチ・監視用のコンポーネント群です。

- ExecutionEngine：発注管理（実ブローカ／モック）・リスク管理・注文再照合
- Monitoring：システム健全性、注文ログ、リスク（ドローダウン等）の定期チェックとアラート・Kill Switch
- Portfolio construction：候補選定・重み付け・ポジションサイズ算出・セクター制限
- Research：ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析（IC、統計サマリー）
- AI モジュール：ニュース記事のセンチメント（OpenAI）によるスコアリングと市場レジーム判定
- ユーティリティ：設定読み込みウィザード、設定検証、ログ設定、プロセス優先度設定など
- ツール：Paper Trading 検証レポート生成スクリプト等

設計方針として、データベース（DuckDB / SQLite）によるローカル解析・ログの永続化、外部 API 呼び出し（OpenAI / kabuステーション / J-Quants）は設定に応じて動作、Paper Trading モードでは本番 DB と分離することを重視しています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV=paper_trading のときはモックブローカー）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔上書き可能、デフォルト 60 秒）
- 設定管理
  - config_setup.py — 対話式 .env ウィザード（.env の作成・更新）
  - validate_config.py — 設定検証 CLI（.env と config/*.yaml の存在・簡易検証）
- 監視（monitoring）
  - system_monitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - trade_monitor: 発注ログの監視（滞留注文、約定異常など）
  - risk_monitor: ドローダウン検出・ポジション上限監視・ダッシュボード更新
  - kill_switch: 条件に応じて data/kill.flag を出力し ExecutionEngine 停止をトリガー
  - monitoring_db: SQLite ベースのスキーマ初期化 / 永続化 API
- Execution（execution）
  - BrokerClientFactory によるブローカークライアント生成（実ブローカー or Mock）
  - OrderManager / OrderRepository / Reconciler / RiskManager / ExecutionEngine（発注・リスク制御）
  - Paper Trading では専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離
- ポートフォリオ（portfolio）
  - 候補選定、等比率／スコア加重の重み付け、リスクベースのポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ（research）
  - DuckDB を利用したファクター計算（momentum, volatility, value）および将来リターン / IC /統計サマリ
- AI（ai）
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector: ETF（1321）の MA200 乖離 と マクロニュースセンチメントを合成して market_regime を算出・保存
- ツール
  - tools/paper_verification_report.py — Paper Trading のログを解析して検証レポートを生成

---

## 必須・推奨依存ライブラリ

（プロジェクトの requirements.txt があればそれを使用してください。以下は主要ライブラリ例）

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行う場合に必要）
- その他、標準ライブラリのみで動く部分も多いです

インストール例:
pip install duckdb psutil openai pyyaml

---

## 環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要なオプション（デフォルト値を示す）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（default: development）
- DUCKDB_PATH — DuckDB ファイル（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）  
  ※ Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL — ログレベル（default: INFO）
- LOG_DIR — ログ出力ディレクトリ（default: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールを使う場合）
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant | partial | never | reject、default: instant）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知を使う場合

Kill Switch / flag 関連:
- KILL_FLAG_PATH — kill.flag のパス（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1"で有効、default: "0"）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくは手動で環境変数を設定
5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば .env を修正して再検証
6. データディレクトリ作成（必要に応じて）
   - mkdir -p data logs
7. 初期 DB（監視テーブルなど）は起動スクリプトで自動初期化されます（init_monitoring_db が呼ばれます）。手動実行は不要です。

---

## 使い方（主なコマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit 1）扱いになります

- ExecutionEngine の起動
  - python -m kabusys.run_execution
  - 動作: プロセス優先度を高に設定 → DB 接続（paper_trading なら専用 DB）→ broker を生成 → ExecutionEngine をスレッドで実行
  - 停止: data/stop_requested.flag が作成されるとエンジン停止をトリガー
  - PID ファイル: data/execution.pid（デフォルト）

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（デフォルト 60）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV にかかわらず）
  - 停止: data/stop_requested.flag の作成で監視ループを終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数で指定可）

- AI 関連（プログラムから呼び出す API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news を集約し OpenAI でセンチメント算出 → ai_scores に書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF MA200 とマクロセンチメントを合成して market_regime に書き込む
  - いずれも OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得

---

## 重要な運用上の注意

- Monitoring は監視用 SQLite（SQLITE_PATH）の DB を使用し、本番環境の監視ログを記録します。Paper Trading と分離したい場合、Execution 側で PAPER_TRADING_SQLITE_PATH を使用してください（run_execution は env に応じて切り替えます）。
- Kill Switch（data/kill.flag）は本番での自動停止用の重要な安全機構です。KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（デフォルトは 0）。
- OpenAI など外部 API を使用する機能は API キーと課金に注意してください。失敗時はフォールバックやスキップする設計ですが、使用ポリシーを確認してください。
- ログは logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリの権限・ディスク容量に注意してください。

---

## ディレクトリ構成（src/kabusys の主要ファイル群）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定管理（.env の自動読み込み、Settings クラス）
  - config_setup.py — .env 作成用対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - execution/  (発注・リスク関連コンポーネント)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py — システム健全性 / データ鮮度監視
    - trade_monitor.py
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - monitoring_engine.py — 各 Monitor の統合ポーリング
    - kill_switch.py — フラグファイルによる停止トリガー
    - alert_manager.py (参照箇所あり)
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数決定・利用キャッシュのスケーリング
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー ファクター
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）集約・書き込み
    - regime_detector.py — レジーム判定（MA200 + マクロセンチメント）
  - monitoring/monitoring_db.py — 監視用 DB スキーマとアクセスクラス

（上記のほか、細かいクラス・ユーティリティが多数あります。各ファイルの docstring を参照してください。）

---

## 開発・デバッグのヒント

- ロギングは kabusys.utils.logging_setup.setup_logging を各スクリプトで呼ぶ設計です。ログレベルは LOG_LEVEL 環境変数で制御できます。
- 自動で .env を読み込む仕組みが config.py にあります。テスト時に自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring のポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能です。0 以下の値は無効化されデフォルト（60 秒）にフォールバックします。
- Paper Trading を使う場合は KABUSYS_ENV=paper_trading に設定し、PAPER_TRADING_SQLITE_PATH を確認してください。Paper Trading は本番 DB と完全に分離して動作するよう設計されています。

---

README はここまでです。特定の操作（例: ExecutionEngine の内部 API の使い方、DB スキーマの詳細、テスト手順）についてさらに詳しいドキュメントが必要でしたら、どの機能の説明を深掘りするか教えてください。