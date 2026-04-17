README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。本リポジトリは以下の機能群を含みます。

- 実行エンジン起動スクリプト（ExecutionEngine）
- 監視（Monitoring）コンポーネント（プロセス/データ鮮度/注文モニタ等）
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ計算）
- ファクター計算・リサーチユーティリティ（DuckDB を用いた集計）
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント集約）
- 環境設定ウィザード・設定検証ツール
- Paper Trading 検証レポート生成ツール

特徴
----
- モジュールは可能な限り純粋関数・DBに依存しない箇所を分離（テスト容易性向上）。
- 実行環境（development / paper_trading / live）を切替え可能。paper_trading は本番 DB と完全分離。
- 監視用 SQLite（monitoring.db）に稼働ログ・取引ログ・リスクログ等を永続化。
- DuckDB を分析基盤として使用（ファクター計算・リサーチ処理に利用）。
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価と、それに基づくレジーム判定。
- Kill Switch（フラグファイル）により実行エンジンを安全に停止可能。

主な機能一覧
--------------
- 環境設定ウィザード: kabusys.config_setup (python -m kabusys.config_setup)
- 設定検証: kabusys.validate_config (python -m kabusys.validate_config)
- 実行エンジン起動: kabusys.run_execution (python -m kabusys.run_execution)
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading.db に記録
- 監視ループ起動: kabusys.run_monitoring (python -m kabusys.run_monitoring)
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は環境にかかわらず Settings.sqlite_path（本番監視 DB）を使用
- Paper Trading 検証レポート: kabusys.tools.paper_verification_report (python -m kabusys.tools.paper_verification_report)
- ポートフォリオ構築:
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（risk_based / equal / score）
  - apply_sector_cap, calc_regime_multiplier
- ニュース NLP / レジーム検出:
  - kabusys.ai.score_news（OpenAI を使って銘柄ごとのセンチメントを ai_scores へ書込み）
  - kabusys.ai.regime_detector.score_regime（ETF とマクロニュースを組合せて市場レジーム判定）
- 監視コンポーネント:
  - SystemMonitor: プロセス存在・CPU/メモリ/ディスク・データ鮮度をチェック
  - TradeMonitor: 注文滞留・約定異常価格をチェック
  - RiskMonitor: ドローダウン・ポジション上限を監視、リスクイベントを記録
  - KillSwitch: 条件成立時に data/kill.flag を書き込んで ExecutionEngine を停止

セットアップ手順
----------------
1. Python 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須（主なもの）:
     - duckdb
     - psutil
     - openai
   - 任意（機能により必要）:
     - PyYAML（config の YAML 検証を有効化）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （本リポジトリに requirements.txt が無ければ上記を手動でインストールしてください）

3. データディレクトリを作成（必要に応じて）
   - mkdir -p data

4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または手動で .env を作成。主な環境変数（必須・推奨）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
     - OPENAI_API_KEY (ニュース NLP / レジーム判定を使う場合)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知用、任意)
     - PAPER_FILL_MODE (instant|partial|never|reject) — paper_trading の約定挙動（デフォルト instant）
     - KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動クリアするか（デフォルト 0）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いにする

使い方
------
起動・停止に関する基本的な使い方：

- 実行エンジン（ExecutionEngine）起動
  - デフォルト（development / live / paper_trading を .env で切替）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。
    - 実行中は data/execution.pid に PID を書きます。PID ファイルが stale（存在はするが該当 PID が稼働していない）だと監視側で検知・削除されます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視ループは stop_requested.flag を検知すると終了します（パス: data/stop_requested.flag）
  - 監視は Settings.sqlite_path を監視 DB として常に使用します（run_monitoring 内の設計上の挙動）

- 停止（手動）
  - 実行エンジンや監視ループを安全に停止するにはプロジェクトルートの data ディレクトリに stop フラグを置く運用や Kill Switch を利用します。
  - Kill Switch: RiskMonitor 等が条件を満たすと data/kill.flag を作成し、ExecutionEngine が検知して停止します。
  - run_execution / run_monitoring は stop_requested.flag を見てループ終了判定を行います。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- ニュース NLP / レジーム判定（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。未設定だと例外になります。

運用上の注意
-------------
- run_monitoring は「監視専用 DB（Settings.sqlite_path）」を使う設計です。環境にかかわらず本番監視 DB が使われるため、監視対象の DB 設定には注意してください。
- run_execution は paper_trading 環境時に paper_sqlite_path を使い DB を分離します（本番 DB と混同しない）。
- .env の自動読み込み:
  - kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を自動読み込みします。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PID / Flag ファイル:
  - data/execution.pid : 実行エンジンの PID（run_execution が作成）
  - data/stop_requested.flag : run_execution / run_monitoring のループを終了させるために使用できる汎用停止フラグ
  - data/kill.flag : Kill Switch による停止理由が書き込まれます（監視コンポーネントが生成）

ディレクトリ構成
-----------------
以下はソースツリー（src/kabusys 配下）の主要ファイルと概要です（抜粋）。

- src/kabusys/
  - __init__.py                     — パッケージ定義
  - config.py                        — 環境変数 / 設定読み込みロジック (.env 自動ロード含む)
  - config_setup.py                  — 対話式 .env ウィザード
  - validate_config.py               — 設定検証 CLI
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py                    — ニュース NLP スコアリング（OpenAI 呼出し）
    - regime_detector.py             — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py

  - monitoring/
    - monitoring_db.py               — 監視用 SQLite 永続化層
    - system_monitor.py              — システム・データ鮮度監視
    - trade_monitor.py               — 注文滞留・約定異常監視
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - monitoring_engine.py           — 各モニタを束ねるエンジン
    - kill_switch.py                 — kill.flag 書き込みユーティリティ
    - alert_manager.py               — （アラートの管理、実装ファイルあり）

  - execution/                       — 発注関連（order_manager 等） ※抜粋されているが存在
  - portfolio/
    - portfolio_builder.py           — 候補選定・等重・スコア重み
    - position_sizing.py             — 株数算出・制限・丸め処理
    - risk_adjustment.py             — セクター上限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py             — モメンタム/ボラティリティ/バリュー等の計算（DuckDB）
    - feature_exploration.py         — 将来リターン・IC 計算・統計サマリー
    - __init__.py

  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート生成 CLI
    - __init__.py

  - utils/
    - process_priority.py            — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

追加情報 / 開発者向け
--------------------
- DuckDB の接続は研究・AI モジュールで頻繁に使用します。prices_daily / raw_financials / raw_news 等のテーブル定義に依存するため、まずデータパイプラインで DuckDB にデータを用意してください。
- OpenAI まわりはリトライや JSON の厳密検証を実装していますが、API の仕様変更に備えてテスト時は _call_openai_api をモックすることを推奨します（コード内にテスト用置換箇所あり）。
- ローカル開発では KABUSYS_ENV=development を使い、実際の発注 API への接続がない状態で動作確認できます。paper_trading モードは発注処理を擬似化して挙動検証に便利です。

ライセンス・貢献
----------------
- 本リポジトリの README にライセンス情報や貢献ガイドを追加してください（本ファイルには含まれていません）。

以上。質問や追加して欲しいセクション（例: API リファレンス、実運用チェックリスト）があれば教えてください。