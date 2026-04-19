# KabuSys

日本株向けの自動売買システム用ライブラリ / 起動スクリプト群です。  
このリポジトリは取引実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）や OpenAI を使ったニュース NLP など、運用に必要なコンポーネント群を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を備えたモジュール群から構成されます。

- ExecutionEngine：発注・注文管理・リスク管理を担う実行エンジン（run_execution.py 起動）
- Monitoring：システム稼働状況・注文状況・リスク監視および Kill Switch（run_monitoring.py 起動）
- Portfolio：候補選定・重み付け・ポジションサイジング・セクター制約などの純粋関数
- Research：DuckDB 上の時系列データを用いたファクター計算・解析ツール
- AI：OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価・レジーム判定
- Tools：Paper Trading の検証レポート生成スクリプト 等
- Utilities：ロギング設定、プロセス優先度設定、設定読み込みユーティリティ 等
- 設定ウィザード / 検証ツール：.env の生成（config_setup.py） / 設定検証（validate_config.py）

設計方針として、ランタイムでのルックアヘッド（date.today() 等）を避ける、外部 API 呼び出しでの失敗はフェイルセーフで扱う、DB を使った永続化は明示的なスキーマ（SQLite / DuckDB）で行う、などが採用されています。

---

## 主な機能一覧

- 実行エンジン（ExecutionEngine）
  - ブローカークライアントの切り替え（paper_trading 用 Mock を含む）
  - 注文履歴・約定ログの永続化（SQLite）
  - リスク管理（ポジション上限・ドローダウン等）
  - PID / 停止フラグ連携

- 監視（Monitoring）
  - CPU / メモリ / ディスク使用率監視
  - ExecutionEngine の生存検査（PID ファイル）
  - 注文の滞留・約定異常検出
  - Kill Switch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
  - 監視ログ格納（SQLite）

- ポートフォリオ構築
  - 候補選定（スコア・ランク）
  - 等金額／スコア加重配分
  - リスクベースのポジションサイジング（単元丸め・aggregate cap）
  - セクター上限適用・レジームによる乗数調整

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン・IC（Information Coefficient）計算
  - 統計サマリー

- AI（OpenAI）
  - ニュース記事をまとめて銘柄別センチメントを算出し ai_scores テーブルへ書き込み
  - 市場レジーム判定（ETF MA + マクロニュースの組合せ）

- ツール
  - Paper Trading 検証レポート生成（paper_verification_report.py）
  - 設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）

---

## 要件

- Python 3.9+
- パッケージ（一部必須・一部オプション）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - pyyaml (config/*.yaml のパースチェックを行う場合)
- SQLite（標準ライブラリを利用）
- ネットワークアクセス（本番のブローカー API / OpenAI を使う場合）

インストール例（仮想環境推奨）:
- pip install -r requirements.txt
（requirements.txt を用意している場合）
あるいは必要に応じて:
- pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成して依存をインストール
3. .env の作成（推奨: 対話式ウィザードを利用）

対話式で .env を作る:
- python -m kabusys.config_setup

手動で作る場合は .env.example を参考に以下などを設定してください（主な環境変数）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB パス、デフォルト: data/paper_trading.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR)
- OPENAI_API_KEY (AI 機能を使う場合)
- PAPER_FILL_MODE (paper_trading の注文振る舞い: instant|partial|never|reject)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか。開発時のみ 1 を推奨)

自動 .env ロード:
- config.py はプロジェクトルートに `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化するには環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 設定検証:
- python -m kabusys.validate_config
- 警告も FAIL 扱いにする: python -m kabusys.validate_config --strict

5. 必要なディレクトリ作成:
- data/（SQLite DB・PID/フラグファイル）
- logs/（ログファイル。setup_logging が自動作成を試みます）

---

## 使い方（主要コマンド）

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、記録先 DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）になります。
    - 起動前に data/stop_requested.flag が存在すると起動を行いません。
    - 実行中は data/execution.pid に PID を書き込みます。

- Monitoring 起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 監視は常に Settings.sqlite_path を使用して監視 DB に接続します（environment に依存しない）。
  - 停止: data/stop_requested.flag を作成することで監視ループが検知して終了します。

- 設定ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1) になります

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

- AI / レジーム・ニューススコアリング（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続オブジェクトを受け取り、必要に応じて OPENAI_API_KEY を参照します。

ログ設定:
- ログは kabusys.utils.logging_setup.setup_logging(app_name="...") を各起動スクリプトで呼び出して統一的に設定します。
- デフォルト: logs/<app_name>.log を日次ローテーションで保管（30日分）

プロセス優先度:
- 起動スクリプトは初期化時に set_process_priority("high") を呼んでいます（psutil 必須。権限により失敗する場合は警告で継続）。

Kill Switch / 停止フラグ:
- 監視側で条件に達した場合 data/kill.flag を書き込み ExecutionEngine を停止させます（ExecutionEngine は定期的に停止フラグを確認します）。
- kill.flag のパスは Settings.kill_flag_path（デフォルト data/kill.flag）で指定できます。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアします（本番では注意）。

---

## 主要な設定と DB パス（デフォルト）

- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db
- PID ファイル: data/execution.pid
- 停止要求フラグ: data/stop_requested.flag
- Kill Switch フラグ: data/kill.flag
- ログ: logs/<app_name>.log

これらは環境変数で上書き可能（.env に設定）。

---

## ディレクトリ構成

（主要なファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                       # 環境変数読み込み・Settings
    - config_setup.py                 # .env 対話式ウィザード
    - validate_config.py              # 設定検証 CLI
    - run_execution.py                # ExecutionEngine 起動スクリプト
    - run_monitoring.py               # Monitoring 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  # Paper Trading 検証レポート
    - ai/
      - __init__.py
      - news_nlp.py                   # ニュース NLP（OpenAI） → ai_scores
      - regime_detector.py            # 市場レジーム判定（MA + LLM）
    - monitoring/
      - monitoring_db.py              # monitoring 用 DB 層（SQLite スキーマ）
      - system_monitor.py             # システム監視（CPU/メモリ/データ鮮度）
      - trade_monitor.py              # (注文監視ロジック、ファイル内に実装あり)
      - risk_monitor.py               # ドローダウン / ポジション上限監視
      - kill_switch.py                # Kill Switch（flag 書き込み）
      - monitoring_engine.py          # 各 Monitor の統合とループ
      - alert_manager.py              # (アラート送信ロジック、ファイル内に実装あり)
    - execution/
      - execution_engine.py           # 実行エンジン本体（EngineConfig / run_session）
      - broker_factory.py             # Broker クライアント生成
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - research/
      - __init__.py
      - factor_research.py            # Momentum / Volatility / Value 等
      - feature_exploration.py        # IC / forward returns / stats
    - portfolio/
      - __init__.py
      - portfolio_builder.py          # 候補選定・重み付け
      - position_sizing.py            # 発注株数計算
      - risk_adjustment.py            # セクターキャップ等
    - utils/
      - __init__.py
      - logging_setup.py              # ルートロガー設定ユーティリティ
      - process_priority.py           # プロセス優先度 / CPU affinity
    - data/ (実行時に生成される想定)
      - *.db, *.pid, kill.flag, stop_requested.flag
    - logs/ (実行時に生成される想定)
      - *.log

---

## 開発者向けメモ / 注意点

- DB マイグレーション:
  - monitoring_db.init_monitoring_db はテーブル作成と簡易マイグレーション（列追加）ロジックを含みます。運用環境での DB 変更は慎重に行ってください。

- 環境区分:
  - KABUSYS_ENV は "development" / "paper_trading" / "live" をサポートします。
  - paper_trading は本番 DB と完全に分離し、MockBroker を使います。
  - live モードは実資金での運用に相当します。validate_config は live でいくつかの追加警告を出します。

- AI 機能:
  - OpenAI 呼び出しは外部 API に依存します。API キーは OPENAI_API_KEY を設定してください。
  - API 呼び出しはリトライ・クラッシュ耐性を備えていますが、コスト・レート制限に注意してください。

- ロギング:
  - setup_logging() は起動スクリプトから呼び出して統一的に使ってください。ログディレクトリ作成に失敗した場合はコンソールのみの出力になります。

- テスト:
  - 各モジュールは外部副作用（DB / API）を引数で注入する設計になっているため、モックしやすくテストが可能です。例えば ai.news_nlp の _call_openai_api はテストで差し替え可能です。

---

以上が本リポジトリ（KabuSys）の概要と使い方のまとめです。実運用の前に必ず python -m kabusys.validate_config で設定を確認し、.env と DB パス、ログ設定などを適切に構成してください。