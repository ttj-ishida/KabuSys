# KabuSys

日本株自動売買システムのコアライブラリと起動用スクリプト群。本リポジトリは戦略・ポートフォリオ構築、実行エンジン、監視・アラート、研究用ユーティリティ、LLM を使ったニュース NLP 等を含むモジュール群を提供します。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主なもの）
- ディレクトリ構成（主要ファイル説明）
- 運用上の注意 / トラブルシュート

---

プロジェクト概要
- KabuSys は日本株の自動売買を想定したモジュール群。
- 主要機能はシグナル生成 / ポートフォリオ構築 / 発注エンジン / 実行監視 / リスク管理 / レポート生成 / LLM を用いたニュースセンチメント評価など。
- DB は分析用に DuckDB（デフォルト: data/kabusys.duckdb）、監視や発注ログ用に SQLite（デフォルト: data/monitoring.db、ペーパートレード時は data/paper_trading.db）を使用。

---

主な機能一覧
- 実行エンジン（run_execution.py）
  - live / paper_trading / development の各環境に対応。
  - paper_trading では MockBrokerClient を利用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH）。
  - リスク管理（RiskManager）、注文管理（OrderManager）、再整合（Reconciler）等を統合して実行セッションを動かす。
- 監視（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた監視ループ。
  - kill.flag による ExecutionEngine 停止（KillSwitch）。
  - 監視ログの永続化（monitoring_db.py）。
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等重/スコア重み割当、リスク補正（セクター制限、レジーム乗数）、株数決定（単元丸め）等の純粋関数群。
- 研究・解析（research パッケージ）
  - ファクター計算（モメンタム、バリュー、ボラティリティ）、特徴量解析、IC 計算、将来リターン計算など。DuckDB を直接利用する設計。
- AI（ai パッケージ）
  - ニュース NLP（news_nlp.py）：OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントスコアを生成し ai_scores テーブルへ保存。
  - レジーム判定（regime_detector.py）：ETF MA とマクロニュースセンチメントを組み合わせて日次の市場レジームを判定・保存。
- ユーティリティ
  - 環境設定ウィザード（config_setup.py）で .env を対話式に作成。
  - 設定検証 CLI（validate_config.py）で .env と config/*.yaml の基本チェック。
  - ログ設定ユーティリティ（utils.logging_setup）。
  - プロセス優先度 / CPU affinity 設定ユーティリティ（utils.process_priority）。
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）。

---

セットアップ手順（ローカル開発用）
1. Python (3.9+) を用意してください。
2. 必要パッケージ例（環境により適宜調整）:
   - duckdb
   - openai
   - psutil
   - （任意）PyYAML（config/*.yaml の構文チェック用）
   例:
     pip install duckdb openai psutil pyyaml
   ※ requirements.txt は本リポジトリに含まれていないため、環境に応じてパッケージをインストールしてください。
3. プロジェクトルート（.git または pyproject.toml がある場所）に移動すると、config モジュールが自動で .env を読み込みます。
4. 対話式ウィザードで初期 .env を作成:
     python -m kabusys.config_setup
   ウィザード完了後、.env がプロジェクトルートに生成されます。
5. 設定検証:
     python -m kabusys.validate_config
   --strict を付けると警告も失敗（exit code 1）扱いになります。
6. DB ディレクトリの作成（必要に応じて）:
     mkdir -p data logs

---

使い方（主要コマンド）
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動
  - python -m kabusys.run_execution
  - 注意: 実行前に .env の KABUSYS_ENV を適切に設定（development / paper_trading / live）。
  - paper_trading モードでは PAPER_FILL_MODE や PAPER_TRADING_SQLITE_PATH が適用され、本番 DB と分離されます。
- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path を参照します（monitoring は環境にかかわらず本番監視 DB を使用）。
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - DB パスは --db、または環境変数 PAPER_TRADING_SQLITE_PATH、または data/paper_trading.db が使用されます。
- 監視 / 実行の停止
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループで検知して停止処理が行われます。
  - Kill Switch（強制停止）: data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（KillSwitch）。

---

主な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境 / ログ
  - KABUSYS_ENV — 実行モード: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト INFO）
  - LOG_DIR — ログディレクトリ（デフォルト logs/）
- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- Paper トレード関連
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト instant）
- AI
  - OPENAI_API_KEY — OpenAI API キー（ai.news_nlp, ai.regime_detector で使用）
- 監視 / Kill Switch
  - PID_FILE_PATH — 実行エンジン PID ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" はクリア、開発向け）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

（上記以外にも細かい閾値設定等の環境変数がコード内 Settings クラスに定義されています）

---

ディレクトリ構成（主要ファイル説明）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定読み込みユーティリティ（.env 自動読み込みロジック含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（メインの実行エントリ）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py — 監視用 SQLite の初期化・永続層
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 発注ログ監視（滞留注文・約定異常など）※実装ファイルがある想定
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書込ロジック
    - monitoring_engine.py — 各 Monitor を束ねるエンジン（テスト用/本番ループ）
    - alert_manager.py — アラート送信管理（LINE 等への通知）※実装ファイルがある想定
  - execution/ — 実行エンジン関連コンポーネント（OrderManager, ExecutionEngine, BrokerFactory など）
  - portfolio/
    - portfolio_builder.py — 候補選定・重みづけ
    - position_sizing.py — 株数計算・丸め・キャップ適用
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/ — ファクター計算・特徴抽出用モジュール（DuckDB 利用）
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI を使って銘柄ごとにセンチメントを算出）
    - regime_detector.py — 市場レジームの判定（ETF MA + マクロ NLP）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（Stream + 日次ローテーションファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定

---

運用上の注意 / トラブルシュート
- .env は決して Git にコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。
- OpenAI API を利用する機能を使う場合は OPENAI_API_KEY を設定してください。キー未設定時は該当処理が例外を投げます（score_news / score_regime 等）。
- run_monitoring は監視 DB（sqlite_path）へ常に接続します。monitoring は KABUSYS_ENV に依存せず本番監視 DB を使用します。
- run_execution の paper_trading モードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を利用）。
- MONITOR_POLL_INTERVAL に 0 や負の値を指定するとフォールバックして 60 秒になります（不正値は警告ログ）。
- process_priority.set_process_priority は OS によって管理権限が必要になる場合があります（psutil.AccessDenied の警告が出る場合は権限がないためスキップされます）。
- DuckDB / SQLite の互換性や executemany の空リスト等、バージョン依存の挙動に注意（コード内に互換性対応処理あり）。
- 監視・Kill Switch の挙動は冪等性（既存 flag がある場合は上書きしない）を考慮していますが、本番運用では手動クリアや自動クリア設定を慎重に扱ってください（KILL_FLAG_CLEAR_ON_START）。

---

貢献 / 拡張案（参考）
- 設定項目を増やして運用しやすくする（各閾値の YAML 化など）。
- 銘柄別単元（lot_size）をマスタに保持して position_sizing を拡張。
- アラート送信先を増やす（Slack / PagerDuty 等）。
- テスト用に OpenAI 呼び出しのモックを提供（現在はモジュール内で差し替えしやすい設計）。

---

ライセンス / 著作権
- 本リポジトリ内のライセンス表記に従ってください（README はコードベースのドキュメント生成用です）。

---

何か追加で README に入れたい情報（例: 実際のコマンド例、環境変数テンプレート、デプロイ手順など）があれば教えてください。必要に応じて .env.example のサンプルや systemd unit ファイルの例も作成できます。