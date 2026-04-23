# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、株価データの研究・ファクター計算・ポートフォリオ構築、発注エンジン、監視、AI（ニュースセンチメント／レジーム判定）などを含む自動売買プラットフォームの一部実装です。

---

主な特徴・設計方針
- モジュール化された設計：研究（research）、ポートフォリオ（portfolio）、発注（execution）、監視（monitoring）、AI（news_nlp / regime_detector）などが分離されている。
- DuckDB を分析用 DB、SQLite を軽量永続化（監視・ペーパートレード等）に利用。
- 環境変数 / .env による構成管理を提供（自動ロード・ウィザード・検証ツールあり）。
- Paper trading（模擬発注）と Live（本番）を分離：KABUSYS_ENV による切り替え。paper_trading 時は MockBrokerClient を使用し、専用 SQLite に記録する。
- 監視コンポーネントは ExecutionEngine の挙動・データ鮮度・リスク制約を観測し、Kill Switch（ファイルを書き込む方式）で安全停止できる。
- OpenAI を利用したニュースセンチメント評価 / レジーム検出の骨組みを提供（APIキー必須）。
- ログは統一的に設定（コンソール + 日次ローテーションファイル）。

含まれる主要機能
- 環境設定ウィザード（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
- 実行エンジン起動スクリプト（kabusys.run_execution）
- 監視ループ起動スクリプト（kabusys.run_monitoring）
- 監視永続化（monitoring_db）と各種モニタ（System / Trade / Risk）
- ポートフォリオ構築ユーティリティ（候補選定・重み計算・ポジションサイズ算出・セクター制限）
- 研究用モジュール（ファクター計算、forward returns、IC、統計サマリ）
- AI モジュール（news_nlp: ニュースセンチメント、regime_detector: 市場レジーム判定）
- ツール: Paper Trading 検証レポート生成スクリプト

前提
- 推奨 Python バージョン: 3.10 以上（型アノテーションや | 型を利用）
- 主要依存パッケージ（必要に応じて追加）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイルの検証を行う場合に必要）
- SQLite は標準ライブラリで利用可能

セットアップ手順（ローカル開発向け）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - J-Quants トークン、kabuステーション API パスワード、KABUSYS_ENV 等を設定します。
   - 生成した .env は絶対にリポジトリにコミットしないでください。

4. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱いになります。

5. データディレクトリの準備（必要であれば）
   - デフォルトで data/、logs/ が使用されます。file 系パスは .env や環境変数で上書き可能。

主要環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 monitoring DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR（ログ保存先、デフォルト: logs/）
- OPENAI_API_KEY（AI モジュールを使う場合必須）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト: 60）
- PID_FILE_PATH（ExecutionEngine の pid ファイルパス、デフォルト: data/execution.pid）
- KILL_FLAG_CLEAR_ON_START（起動時に kill flag を自動クリアするか: 0/1）

使い方（よく使うコマンド例）
- .env を対話式で作る:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
    - 起動中に data/stop_requested.flag を作成するとエンジンは停止します。
    - PID ファイル: data/execution.pid（デフォルト）にプロセス情報を出す設計です。

- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
    - 監視は環境にかかわらず本番の sqlite_path（monitoring DB）を使用する実装になっています。
    - data/stop_requested.flag を作成すると監視ループが終了します。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（ニューススコアリング / レジーム判定）
  - OPENAI_API_KEY を環境変数に設定して利用します。
  - news_nlp.score_news / regime_detector.score_regime が主要なエントリポイント（通常はアプリケーション内から呼び出す）。

停止・Kill Switch（安全停止の仕組み）
- KillSwitch は監視サイドが評価してデータ/リスク条件を満たした場合に data/kill.flag を書き込みます。
- ExecutionEngine/run_execution は起動時に kill flag の状態を確認し、FLAG があると起動しない設計（オプションによる挙動）になっています。
- 手動停止用に data/stop_requested.flag を置くことで run_monitoring / run_execution のループを終了できます。

ディレクトリ構成（概要）
- src/kabusys/
  - __init__.py — パッケージ宣言
  - config.py — 環境変数・設定管理（.env 自動読み込みロジック含む）
  - config_setup.py — .env 作成の対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュースの LLM によるセンチメントスコアリング
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数算出・丸め・利用可能現金スケール
    - risk_adjustment.py — セクター制約・レジーム乗数
  - research/
    - factor_research.py — Momentum, Volatility, Value 等のファクター計算
    - feature_exploration.py — forward returns, IC, 統計サマリ等
  - monitoring/
    - monitoring_db.py — SQLite 利用の永続化層（テーブル作成・読み書き）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文関連）監視ロジック
    - risk_monitor.py — ドローダウン・ポジション数監視
    - kill_switch.py — ファイルを使った停止シグナル生成
    - monitoring_engine.py — 各 Monitor を束ねて実行
    - alert_manager.py — 通知管理（LINE 等、実装に依存）
  - execution/
    - execution_engine.py — 発注セッション管理（Engine 本体）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など（発注周り）
  - data/ (想定)
    - monitoring.db（SQLite、デフォルト）
    - paper_trading.db（Paper Trading 用）
  - logs/ (想定)
    - execution.log, monitoring.log など（ログ出力先）

開発時の注意
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- 設定検証ツール（validate_config）は PyYAML がインストールされていない場合、YAML の内容検証をスキップします（警告）。
- OpenAI API 呼び出しを含む機能はネットワークや API レート制限の影響を受けます。リトライ / フォールバック処理が組み込まれていますが、運用時は API キー・コスト・レート制限を考慮してください。
- execution/run_monitoring の停止は data/stop_requested.flag ファイルの作成で行います。運用環境では systemd やコンテナの停止シグナルとの連携を検討してください。

トラブルシュート
- ログが出力されない／ログファイルが作れない場合:
  - LOG_DIR 環境変数やログディレクトリのパーミッションを確認してください。logs/ ディレクトリの作成に失敗するとコンソール出力のみになります（警告が stderr に出ます）。
- 設定エラー:
  - python -m kabusys.validate_config でまずチェックしてください。
- OpenAI 関連エラー:
  - OPENAI_API_KEY が未設定だと例外が出ます。設定を確認してください。
  - レスポンスの形式検証や JSON パースに失敗するケースはログに警告されます（フォールバック動作あり）。

ライセンス・貢献
- この README ではライセンスファイルは明記していません。リポジトリの LICENSE を確認してください。
- 貢献の際は機密情報（.env・APIキー）を含めない Pull Request をお願いします。

---

以上がリポジトリの概要、セットアップ、使い方、主要ファイル構成の説明です。必要であれば各モジュール（例: ExecutionEngine の挙動、OrderRepository の API、monitoring のアラート条件など）について個別の詳細ドキュメントも作成します。どの部分を詳しく説明しましょうか？