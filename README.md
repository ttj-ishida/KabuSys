# KabuSys

日本株向け自動売買システムのミニマル実装（ライブラリ + 起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・リスク管理・研究/解析・AI（ニュースセンチメント）連携など、自動売買システムに必要な主要コンポーネントをモジュール化したコードベースです。

主な特徴
- 実行エンジン（ExecutionEngine）／ペーパートレード対応（環境変数で分離）
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- リサーチ機能（ファクター計算、特徴量解析、IC算出など）
- OpenAI を使ったニュース NLP による銘柄センチメント評価（ai.news_nlp）
- ログ設定ユーティリティ（コンソール + 日次ローテート）
- .env 対応の設定ウィザード / 設定検証ツール
- Paper Trading 検証レポート生成ツール

機能一覧
- 起動スクリプト
  - run_execution.py: 発注エンジン起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用・専用 DB に記録）
  - run_monitoring.py: 監視ループ起動（システム状態・注文・リスクのポーリング）
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前の設定検証（--strict オプションあり）
  - config.Settings: アプリ設定の集中管理（環境変数抽出・バリデーション）
- 監視・アラート
  - monitoring/monitoring_db.py: SQLite を用いた監視ログ永続化
  - monitoring/system_monitor.py / trade_monitor.py / risk_monitor.py: 監視ロジック
  - monitoring/kill_switch.py: 条件を満たすと data/kill.flag を書き込み Execution を停止
  - monitoring/monitoring_engine.py: 各モニタを束ねるエンジン
- 発注・リスク管理（execution パッケージ）
  - Broker クライアントの抽象化（Paper/Live 切替）
  - OrderManager / OrderRepository / RiskManager / ExecutionEngine 等（エンジン実装）
- ポートフォリオ構築（portfolio パッケージ）
  - 候補抽出、等重・スコア重み、セクターキャップ、レジーム乗数、株数決定（lot 単位切り上げ/切り捨て）
- 研究（research パッケージ）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC（Spearman）・統計サマリー
- AI連携（ai パッケージ）
  - news_nlp.score_news: OpenAI を用いたニュースのセンチメント集約と ai_scores への書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースを合成した日次レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を集計して検証レポートを出力

セットアップ手順（最小）
1. Python 環境を準備
   - 推奨: Python 3.9+（コードは typing, psutil, duckdb, openai 等を使用）
2. 必要パッケージをインストール
   - 例:
     pip install duckdb psutil openai
     pip install PyYAML   # config 検証で YAML をパースしたい場合
   - 本リポジトリに requirements.txt があればそれを使用してください（無い場合は上記を参考に）。
3. プロジェクトルートで .env を作成
   - 対話式ウィザードを使用:
     python -m kabusys.config_setup
   - もしくは .env を手動作成。最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
     - OPENAI_API_KEY（ニュース NLP / レジーム判定を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（例: INFO）
4. 設定検証（任意だが推奨）
   python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで exit(1)
5. ログディレクトリ
   - デフォルト: logs/
   - 環境変数 LOG_DIR で変更可能

使い方（よく使うコマンド例）
- ExecutionEngine を起動（通常）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録します（本番 DB と分離）。
  - 実行中は data/execution.pid が PID ファイルとして使用されます。
  - 停止フラグ: data/stop_requested.flag を作成するとループが安全に終了します。
- Monitoring を起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は設定に関わらず sqlite_path（本番の監視 DB）を使用します。
- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH を参照）
- .env を自動ロード
  - config モジュールはプロジェクトルートの .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- AI 機能（プログラム的呼び出し）
  from kabusys.ai import score_news
  score_news(conn, target_date, api_key="...")

注意事項 / 運用メモ
- Paper Trading モードは本番 DB と完全に分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI API キーは機密情報です。.env を絶対に Git にコミットしないでください。
- Kill Switch（kill.flag）は監視コンポーネントが検出した致命的なリスク時に書き込まれ、ExecutionEngine を安全に停止させます。KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアしますが、本番では推奨されません。
- logging_setup は stdout と日次ローテーションファイル（logs/<app_name>.log）を設定します。ログディレクトリ作成に失敗してもコンソールログは動作します。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 設定読み込み / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — 監視ループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
  - utils/
    - logging_setup.py
    - process_priority.py

本 README はコードベースの概要ドキュメントです。詳細な設計（アルゴリズム仕様、DB スキーマ、StrategyModel/PortfolioConstruction ドキュメント）はリポジトリ内の設計資料やコードコメントを参照してください。必要であれば、起動スクリプトや各モジュールの使用例・API リファレンスを追加で作成します。