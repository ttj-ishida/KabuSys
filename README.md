# KabuSys

日本株自動売買システムのライブラリ／実行スクリプト群です。  
このリポジトリはトレード用エンジン、監視（Monitoring）、リサーチ・ファクター計算、AI を用いたニュース評価などの機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 使い方（主なコマンド・例）
- 重要な環境変数と挙動
- 停止・Kill スイッチについて
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買システム用のコンポーネントを集めた Python パッケージです。
- 発注エンジン（ExecutionEngine）、監視（MonitoringEngine／各種 Monitor）、ポートフォリオ構築・ポジション算出、リサーチ（ファクター計算・特徴量解析）、および OpenAI を使ったニュース NLP / レジーム判定などを含みます。
- 設定は .env ファイル（または環境変数）で行い、config 設定の対話式ウィザード・検証ツールが用意されています。

---

機能一覧
- Execution
  - ExecutionEngine（発注エンジン）起動スクリプト
  - Paper Trading モード（mock broker / 本番 DB と分離された data/paper_trading.db）
  - リスク管理・OrderManager・Reconciler 等の統合
- Monitoring
  - SystemMonitor: プロセス稼働状況、CPU/メモリ/ディスク、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定の異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視（KillSwitch 連携）
  - MonitoringEngine: 各 Monitor を束ねてポーリング
  - SQLite ベースの監視 DB（monitoring_db）
- Portfolio
  - 候補選定、等重/スコア重み付け、セクターキャップ適用、ポジションサイズ計算（lot 単位、aggregate cap）
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC 計算、統計サマリー
  - DuckDB を使った高速分析
- AI
  - ニュース NLP（OpenAI）による銘柄別センチメント算出（ai_scores テーブル書き込み）
  - 市場レジーム判定（MA200 + マクロセンチメント合成）
  - API 呼び出しは再試行・フォールバックを備えた堅牢設計
- ツール
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）

---

前提条件
- Python 3.9+
- pip でインストールする主な依存（プロジェクトに requirements.txt が無い場合は個別に）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を使用する場合）
- SQLite（標準ライブラリ）
- ネットワーク接続（OpenAI を使う場合）
- （任意）kabuステーション API とその接続設定（本番運用時）

例:
pip install duckdb psutil openai PyYAML

---

セットアップ手順（推奨の流れ）
1. リポジトリをクローンして、作業ディレクトリをプロジェクトルートにする。
2. 仮想環境を作成・有効化し、依存をインストールする。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install duckdb psutil openai PyYAML
3. .env を作成する（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークンや KABU_API_PASSWORD など必須項目を案内します。
   - .env は絶対に VCS にコミットしないでください。
4. 設定検証を実行
   - python -m kabusys.validate_config
   - 本番前に --strict を付けて警告も失敗扱いにできます: python -m kabusys.validate_config --strict
5. DB 用ディレクトリを用意（自動作成される場合が多いですが手動で作る場合）
   - mkdir -p data
6. （Paper Trading を使う場合）PAPER_FILL_MODE 等を .env に設定可能

---

使い方（主なコマンド・例）
- 実行エンジンを起動（本番 / development / paper_trading は KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db に記録（本番 DB と完全分離）
    - エンジンは data/execution.pid を作成してプロセス検出に利用します
    - 起動前に data/stop_requested.flag が存在すると起動せず終了します
- 監視ループを起動
  - python -m kabusys.run_monitoring
    - デフォルトのポーリング間隔は 60 秒
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（例: MONITOR_POLL_INTERVAL=30）
    - monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視は一貫した DB を見るため）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]

ライブラリ API（プログラムから呼ぶ場合の例）
- ai:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key=...)
- research:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
- portfolio:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

（詳細なパラメータは各モジュールの docstring を参照してください）

---

重要な環境変数（抜粋）
- KABUSYS_ENV: "development" | "paper_trading" | "live"（default: development）
  - paper_trading: mock broker を利用、paper_db に記録
  - live: 本番。注意して設定してください
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、default: instant）
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）
- OPENAI_API_KEY: OpenAI 呼び出しに使用
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、default: 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリア（"1" 有効。default: "0"）

設定の自動ロード
- プロジェクトルートにある .env, .env.local を自動で読み込みます（既存 OS 環境変数は保護）。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

停止・Kill スイッチ・フラグファイル
- 停止要求（run_execution / run_monitoring の外部停止）
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが終了します（起動スクリプトが参照）。
- Kill Switch（自動停止トリガ）
  - KillSwitch コンポーネントは指定のパス（Settings.kill_flag_path、default: data/kill.flag）に理由テキストを書き込むことで ExecutionEngine に停止を促します。
  - KillSwitch は RiskMonitor などの監視結果に基づいて書き込みます。
  - ExecutionEngine 側には KILL_FLAG_CLEAR_ON_START 設定があり、起動時に kill.flag を自動でクリアするかどうか制御できます（本番では 0 推奨）。
- PID ファイル
  - Execution は data/execution.pid を作成し、SystemMonitor がプロセス存否をチェックします。古い PID ファイルは stale と見なされ削除されます。

---

運用上の注意
- .env ファイルは機密情報を含むため絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では LINE 通知トークンやログ設定を十分に確認してください（validate_config は本番向けの追加チェックを行います）。
- OpenAI API 使用時はレート制限や課金に注意。AI モジュールはリトライとフォールバックを備えていますが、費用リスクは運用者の責任です。
- process priority / CPU affinity の設定は psutil を利用します。権限や OS によって失敗することがあるため警告ログに留まります。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定読み込みと Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト
  - execution/               — 発注エンジン周辺コンポーネント（OrderManager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - utils/
    - process_priority.py
  - data/ (実行時に生成される想定)
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (paper_trading モード時)
    - execution.pid
    - kill.flag / stop_requested.flag

（上記はソースツリーの概要です。各サブモジュールにさらに実装ファイルが存在します）

---

トラブルシューティング
- .env の自動ロードが働かない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - プロジェクトルートが正しく検出されるか（.git または pyproject.toml を探索）
- OpenAI 呼び出しが失敗する場合:
  - OPENAI_API_KEY を確認、ネットワーク、レート制限、モデル利用可能性をチェック
- psutil によりプロセス優先度の設定が失敗する場合:
  - 権限不足やプラットフォーム非対応の可能性があるためログを確認（警告でスキップされます）

---

参考・次のステップ
- 初期設定: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- 実運用: KABUSYS_ENV=live 環境で監視とエンジンを別プロセスで起動・監視することを推奨

何か特定の部分（API 使用例、設定例、デプロイ手順等）の README 追記を希望されればお知らせください。