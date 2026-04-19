# KabuSys

日本株自動売買システムのモジュール群。ポートフォリオ構築・発注実行・監視・リサーチ・AI ニューススコアリングなどを含むライブラリと起動スクリプトの集合です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を持つ、自動売買システムの構成要素群です。

- 発注実行エンジン（ExecutionEngine） — ブローカークライアント経由で注文を管理・実行
- 監視（Monitoring） — システム状態・注文状態・リスク（ドローダウン・ポジション上限等）を定期チェックしログ・アラート・Kill Switch を管理
- ポートフォリオ構築（Portfolio） — 候補選定、重み付け、ポジションサイズ計算、セクター制限などの純粋関数群
- リサーチ（Research） — DuckDB の株価・財務データを用いたファクター計算・特徴量探索
- AI モジュール（AI） — OpenAI を用いたニュースセンチメント集約（news_nlp）と市場レジーム判定（regime_detector）
- ユーティリティ — ロギング設定、プロセス優先度設定、設定読み込みウィザード・検証ツールなど
- 各種ツール — Paper Trading の検証レポート生成など

設計方針の一部:
- DuckDB / SQLite を用いたローカル DB（分析用 / 監視用）に依存
- 本番・ペーパートレードの DB を分離（環境に応じて切替）
- 外部 API 呼び出し（OpenAI など）は明示的にキーを渡すか環境変数で管理
- ルックアヘッドバイアスを避ける設計（日時参照の扱いに注意）

---

## 機能一覧

- 起動・運用
  - run_execution.py: ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 起動時にプロセス優先度を "high" に設定
    - 停止フラグ（data/stop_requested.flag / data/kill.flag）で停止可能
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
    - 監視ログは sqlite (settings.sqlite_path) に記録（Monitoring は環境に関わらず本番 sqlite_path を使用）
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の起動前チェックツール
  - Settings クラス: 環境変数の取得・検証（KABUSYS_ENV, LOG_LEVEL, DB パスなど）
- 監視機能
  - monitoring_db.py: monitoring DB スキーマ初期化・永続化 API
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 各種チェック（プロセス死活、データ鮮度、滞留注文、ドローダウン等）
  - kill_switch.py: 条件で kill.flag を書き込み ExecutionEngine に停止シグナルを送る
  - monitoring_engine.py: 各モニタを束ねて定期実行・アラート連携
- ポートフォリオ構築
  - portfolio_builder.py: 候補選定、等重・スコア重みの計算
  - position_sizing.py: 株数計算（リスクベース、等分配等）、単元株丸め、aggregate cap のスケール処理
  - risk_adjustment.py: セクター上限・レジーム乗数の適用
- リサーチ
  - research.factor_research: Momentum / Volatility / Value ファクター算出（DuckDB 経由）
  - research.feature_exploration: 将来リターン、IC、統計サマリー等
- AI（OpenAI）
  - ai.news_nlp: ニュース記事を集約し OpenAI に送って銘柄ごとのセンチメントを ai_scores に書き込む
  - ai.regime_detector: ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成して market_regime を判定・書き込み
- ツール
  - tools.paper_verification_report: ペーパートレード DB のレポート生成（稼働率・成功率・レイテンシ等）

---

## セットアップ手順（開発・ローカル実行向け）

1. Python 環境
   - 推奨: Python 3.9+（DuckDB、psutil、openai 等が必要）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Linux/macOS) または .venv\Scripts\activate (Windows)

2. 依存パッケージのインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 主要依存（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML (config の YAML 検証に必要だが必須ではない)
   - 開発インストール（パッケージ化されている場合）:
     - pip install -e .

3. プロジェクトルートの特定と .env の作成
   - 対話式で .env を作る:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI を使う場合）
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - LOG_LEVEL（DEBUG/INFO/...）
     - PAPER_FILL_MODE（paper_trading の注文成立モード: instant/partial/never/reject）

4. 設定検証
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けて警告も FAIL 扱いに

5. 初期 DB / ディレクトリ
   - 起動スクリプトが必要なディレクトリを作成します（例: data/ logs/）
   - monitoring 起動時に monitoring DB スキーマが自動作成されます

---

## 使い方（起動・運用）

- ExecutionEngine 起動
  - 本番（例）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード（MockBroker を使用、専用 DB に記録）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 挙動:
    - 起動時にプロセス優先度を high にセット
    - data/stop_requested.flag が存在すると起動を抑制、もしくは実行中であれば停止処理が走る
    - 実行中、data/execution.pid に PID を書き出す設計（pid_file を Settings で指定可能）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 監視は Settings.sqlite_path（本番 sqlite）を使用してログを記録します（環境にかかわらず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - データベース指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH
  - 出力: コンソールに指標と PASS/FAIL 判定を表示

- AI スコアリング / レジーム判定（プログラム的呼び出し）
  - news_nlp.score_news:
    - 例:
      from kabusys.ai.news_nlp import score_news
      import duckdb
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, target_date, api_key="sk-...")
  - regime_detector.score_regime:
    - 例:
      from kabusys.ai.regime_detector import score_regime
      import duckdb
      conn = duckdb.connect("data/kabusys.duckdb")
      score_regime(conn, target_date, api_key="sk-...")
  - 注意:
    - OPENAI API 呼び出しには OPENAI_API_KEY（または api_key 引数）が必要
    - API エラーはリトライやフェイルセーフで処理されるが、キー未設定は例外になる

- Kill Switch / 停止フラグ
  - KillSwitch はリスク条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）に理由をファイル書き込みします
  - ExecutionEngine はこのファイルを検知して停止します
  - 起動時に自動で kill.flag をクリアするかどうかは KILL_FLAG_CLEAR_ON_START で制御（本番では 0 推奨）

---

## 重要なファイル / デフォルトパス

- データ・ログ
  - data/kabusys.duckdb （DuckDB、分析データ）
  - data/monitoring.db （監視用 SQLite）
  - data/paper_trading.db （ペーパートレード用 SQLite）
  - data/kill.flag （Kill Switch フラグ）
  - data/stop_requested.flag （外部停止要求）
  - data/execution.pid （ExecutionEngine PID）
  - logs/<app_name>.log （ログファイル、デフォルト logs/ ディレクトリ）

- 設定
  - .env（プロジェクトルート）
  - config/*.yaml（追加設定、validate_config で検証。PyYAML があればパースチェックを実施）

---

## ディレクトリ構成（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — Settings クラス・自動 .env ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - (その他: execution/*, data/* のモジュール群が想定)

---

## 開発上の注意点 / ベストプラクティス

- 環境分離
  - KABUSYS_ENV を正しく設定してください。paper_trading モードは本番 DB と分離する設計になっています。
  - 本番運用時は KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）
- データ鮮度 / ルックアヘッド
  - research / AI モジュールはルックアヘッドを避ける工夫がなされています（target_date 未満データの使用など）
- ログ
  - setup_logging() を全スクリプトから呼び出して統一されたログ管理を行っています。logs/ に日次ローテートで出力されます。
- テスト
  - OpenAI 呼び出し部分はテスト時に差し替え可能なように抽象化されています（ユニットテストではモックを推奨）。
- DB 互換
  - DuckDB / SQLite のバージョン互換性に注意。monitoring_db.init_monitoring_db は既存 DB に対する簡単なマイグレーションを含みます。

---

## よくあるコマンドまとめ

- .env 初期作成（対話式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコアリング（スクリプトから実行）:
  - python -c "from kabusys.ai.news_nlp import score_news; import duckdb, datetime; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date(2026,4,1), api_key='sk-...'))"

---

必要に応じて README にサンプル .env や requirements.txt、起動/運用手順の詳細（systemd/cron 用の例、Docker 化の説明など）を追加できます。どの形式で補足を作成しましょうか？