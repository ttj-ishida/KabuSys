README
=====

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤です。  
主な目的は「戦略によるシグナル生成 → ポートフォリオ構築 → 発注実行 → 監視・リスク管理」を一貫して実行できることです。  
設計上の特徴:
- 実行（Execution）と監視（Monitoring）を分離したプロセス構成
- DuckDB / SQLite を使ったデータ分析および軽量永続化
- Paper Trading（モックブローカー）と Live を環境で切り替え可能
- ニュースセンチメントやレジーム判定に OpenAI を利用する拡張機能
- ログ・PID・Kill Switch 等の運用機能を備える

主な機能一覧
--------------
- ExecutionEngine（発注エンジン）
  - ブローカークライアントを抽象化し、paper_trading 環境では MockBrokerClient を使用して data/paper_trading.db に記録
  - リスク管理（RiskManager）、オーダー管理（OrderManager）、Reconciler 等を統合
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス生存確認
  - TradeMonitor: 注文の滞留・約定異常検出（trade_logs を参照）
  - RiskMonitor: ドローダウン／ポジション上限監視と kill.flag 制御
  - MonitoringEngine: 上記をまとめてポーリング・アラート連携
- Data / Research
  - DuckDB 上でファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- Portfolio（ポートフォリオ構築）
  - 候補選定、等重・スコア重み、ポジションサイズ計算（単元株丸め・aggregate cap）
  - セクターキャップやレジーム乗数適用
- AI（OpenAI 統合）
  - news_nlp: raw_news を用いた銘柄別センチメントスコア化（ai_scores テーブルへ書込）
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM スコアを合成して market_regime を決定
- ユーティリティ
  - logging_setup: 統一的なログ設定（stdout + 日次ローテート）
  - process_priority: プロセス優先度 / CPU affinity 設定
  - config_setup: .env を対話的に生成・更新するウィザード
  - validate_config: 起動前チェック（必須環境変数・ファイル存在など）
  - tools.paper_verification_report: Paper Trading の検証レポート生成

セットアップ手順
---------------
前提
- Python 3.9 以上（duckdb / psutil 等が必要）
- 必要ライブラリ（例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config の YAML 検証を行う場合）
インストール例（仮想環境推奨）:
  python -m venv .venv
  source .venv/bin/activate   # Windows の場合は .venv\Scripts\activate
  pip install -r requirements.txt
（requirements.txt がない場合は個別に pip install duckdb psutil openai pyyaml など）

初期設定
1. プロジェクトルートに移動（.git や pyproject.toml があるディレクトリ）
2. .env を作成
   - 対話形式のウィザードを使う:
       python -m kabusys.config_setup
   - または .env.example を参考に手動で作成
   主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   任意・推奨:
     - OPENAI_API_KEY（AI 機能を利用する場合）
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
3. 設定検証（起動前チェック）:
     python -m kabusys.validate_config
   --strict を付けると警告もエラー扱いになります。
4. ディレクトリ作成:
   - data/（DB・PID・flag ファイルを格納）
   - logs/（ログ出力）
   ほとんどのスクリプトは起動時に自動作成しますが、権限に注意してください。

使い方
-----
起動スクリプト（プロセスとして運用する主要コマンド）
- 実行エンジン（ExecutionEngine）を起動:
    python -m kabusys.run_execution
  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動を行いません。
  - 実行中に data/stop_requested.flag が作成されるとエンジンに停止要求が送られます。
  - PID ファイルは data/execution.pid（環境変数 PID_FILE_PATH で上書き可）。

- 監視ループを起動:
    python -m kabusys.run_monitoring
  挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。
  - data/stop_requested.flag を検知すると監視ループを終了します。

ツール
- Paper Trading 検証レポート生成:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で別 DB を指定可。環境変数 PAPER_TRADING_SQLITE_PATH を優先します。
- .env 作成ウィザード:
    python -m kabusys.config_setup
- 設定検証:
    python -m kabusys.validate_config [--strict]

ライブラリとしての利用例
- ポートフォリオモジュールを直接呼ぶ:
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
- AI スコアリング（プログラム呼出し）:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="...")

運用上の注意
- Live 環境では設定を十分に確認してください（validate_config が警告を出します）。
- Kill Switch: RiskMonitor → KillSwitch により data/kill.flag が書き込まれると ExecutionEngine に停止シグナルが送られます。KILL_FLAG_CLEAR_ON_START に注意（本番では 0 推奨）。
- ログ: デフォルトで logs/<app_name>.log に日次ローテート（30 日保持）され、コンソールは stdout に出力されます。
- OpenAI API を利用する場合は OPENAI_API_KEY を設定してください。API 失敗時はフェイルセーフで処理を継続する設計ですが、結果が N/A や中立になることがあります。

ディレクトリ構成（主要ファイル）
--------------------------------
src/
  kabusys/
    __init__.py
    config.py                    # 環境変数 / Settings
    config_setup.py              # .env ウィザード
    validate_config.py           # 設定検証 CLI
    run_execution.py             # ExecutionEngine 起動スクリプト
    run_monitoring.py            # SystemMonitor 起動スクリプト

    execution/                   # 発注エンジン関連（OrderManager, RiskManager 等）※実装ファイル群
      ...

    monitoring/
      monitoring_db.py           # SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
      system_monitor.py          # システム監視（CPU/メモリ/ディスク、データ鮮度）
      trade_monitor.py           # 注文系監視（trade_logs）
      risk_monitor.py            # ドローダウン / ポジション上限監視
      kill_switch.py             # kill.flag の作成・管理
      monitoring_engine.py       # 各 Monitor を束ねる

    portfolio/
      portfolio_builder.py       # 候補選定・重み計算
      position_sizing.py         # 株数算出・アグリゲートキャップ
      risk_adjustment.py         # セクター上限・レジーム乗数
      __init__.py

    research/
      factor_research.py         # ファクター計算（momentum/value/volatility）
      feature_exploration.py     # 将来リターン・IC・統計サマリ
      __init__.py

    ai/
      news_nlp.py                # ニュースNLP(LLM) による銘柄センチメント
      regime_detector.py         # マクロ + MA200 を用いたレジーム判定
      __init__.py

    tools/
      paper_verification_report.py  # Paper Trading 検証レポート
      __init__.py

    data/                         # 実行時に使用する (例)
      monitoring.db (デフォルト SQLite)
      paper_trading.db (paper_trading 用)
      kill.flag
      stop_requested.flag
      execution.pid

    logs/                         # ログファイル（logs/<app_name>.log）

補足: よくあるトラブルと対処
--------------------------
- .env が読み込まれない / 環境変数が足りない:
  - python -m kabusys.validate_config で不足項目を確認してください。
  - 自動ロードを無効化している場合（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）には .env を手動で読み込んでください。
- PyYAML が無いと config/*.yaml の内容検証はスキップされます（validate_config が警告を出します）。内容検証が必要なら pip install pyyaml。
- DuckDB / SQLite ファイルのパス（DUCKDB_PATH / SQLITE_PATH）に書き込み権限があるか確認してください。
- OpenAI 呼び出しエラー（RateLimit 等）は内部でリトライ/フェイルセーフしていますが、APIキーの設定と送信量管理に注意してください。

ライセンス / 貢献
-----------------
このリポジトリのライセンス情報はプロジェクトに含まれていません。公開・配布する場合は LICENSE ファイルを追加してください。貢献は Pull Request / Issue を通じて受け付けてください（プロジェクト固有の貢献ルールがあれば追記してください）。

以上。README に記載してほしい追加項目（サンプル .env、具体的な依存バージョンなど）があれば教えてください。