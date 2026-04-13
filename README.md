# KabuSys

日本株の自動売買システム（プロトタイプ）。  
このリポジトリは取引実行・リスク管理・監視・ポートフォリオ構築・研究用のファクター計算・ニュースNLP（OpenAI）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の責務を分離して実装したモジュール群です。

- Execution（ExecutionEngine）: ブローカークライアントを通じた発注／注文状態管理、リコンシリエーション
- Monitoring: システム状態（CPU/メモリ/ディスク/プロセス）、注文滞留、ドローダウン、アラート送信（LINE）、ダッシュボード（Streamlit）
- Portfolio construction: 候補選定、重み計算、ポジションサイズ決定、セクターキャップ・レジーム補正
- Research: DuckDB を用いたファクター（Momentum/Volatility/Value）や特徴量探索（IC 等）の計算
- AI: ニュース記事のセンチメント（OpenAI）に基づく ai_scores の生成や市場レジーム判定
- Tools: Paper Trading 検証レポートの生成などの補助スクリプト

設計方針の一部:
- DuckDB は時系列・研究向けデータ（prices_daily / raw_financials / raw_news 等）を保持・集計する用途
- SQLite は監視ログ（monitoring.db）や Paper Trading 用の取引ログ（paper_trading.db）に使用
- 環境依存設定は環境変数または .env ファイルで管理（自動読み込みサポート）
- 本番と Paper Trading は DB を分離して安全性を確保

---

## 機能一覧

主な機能（抜粋）:

- Execution
  - Broker クライアント生成（実口座 or Mock）
  - OrderManager：Order の作成、送信、同期（sync）
  - Reconciler：再起動時の注文／ポジションリコンシリエーション

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態、データ鮮度チェック
  - TradeMonitor：滞留注文・約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限チェック
  - KillSwitch：条件に応じて flag ファイルを書き ExecutionEngine を停止
  - AlertManager：LINE へのプッシュ通知（クールダウン付き）
  - Streamlit ダッシュボード（監視表示）

- Portfolio
  - 候補選定（score順）、等金額／スコア重み配分
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（リスクベース / 等配分 / スコア基準）、単元株丸め、aggregate cap

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）や統計要約

- AI
  - news_nlp.score_news: raw_news を集約して OpenAI に送り、ai_scores を書き込み
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースでレジーム判定、market_regime に書き込み

- Tools
  - paper_verification_report: Paper Trading DB を解析し稼働率・成功率・レイテンシ等の検証レポートを標準出力に表示

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール  
   （プロジェクトに requirements.txt がない場合は少なくとも以下を入れてください）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit

   例:
   - pip install duckdb psutil requests openai streamlit

3. 環境変数を設定  
   最低限設定が必要なもの（用途）:
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（データ取得に使用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（ブローカー操作）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   推奨／デフォルトパス:
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
   - PID_FILE_PATH: data/execution.pid
   - KILL_FLAG_PATH: data/kill.flag

   その他（代表例）:
   - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
   - PAPER_FILL_MODE: instant | partial | never | reject  （paper_trading 時の約定挙動）
   - MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、デフォルト 60）

   .env を使う場合はプロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. データディレクトリ作成
   - mkdir -p data

5. DuckDB / SQLite の初期化は各起動スクリプトが必要なテーブルを自動作成します（init_monitoring_db 等）。

---

## 使い方（主要スクリプト／API）

コマンドラインから直接モジュールを起動できます（パッケージのルートで実行）。

- ExecutionEngine を起動（本番または paper_trading は KABUSYS_ENV に依存）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution
  - 補足:
    - paper_trading モードでは MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録され本番 DB と分離されます。
    - 起動時にプロセス優先度を上げ、PID ファイル（設定された PID_FILE_PATH）を使用します。
    - kill.flag による外部停止機構（KillSwitch）が組み込まれています。

- Monitoring を起動（監視ループ）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルト間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書きできます。
  - 監視は常に本番用 sqlite_path（settings.sqlite_path）を使用して監視ログを永続化します。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで監視 DB を開きます（デフォルト: data/monitoring.db）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH で DB を明示的に指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI モジュール（Python API として利用）
  - ニューススコア付与:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="sk-...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")

  - これらは DuckDB 接続（kabusys.data で作る接続など）を受け取り DB のテーブルを参照して結果を書き戻します。OpenAI API key が必要です。

- ライブラリ的な利用例（ポートフォリオ・リサーチ関数）
  - from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
  - from kabusys.research import calc_momentum, calc_volatility, calc_value

---

## 主要な環境変数（要約）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants を利用する機能に必要）
- KABU_API_PASSWORD: 必須（kabuステーション API 用）
- OPENAI_API_KEY: OpenAI を利用する場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch 用フラグ（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定モード（instant/partial/never/reject）

詳細な設定は `kabusys.config.Settings` クラスを参照してください（バリデーションとデフォルトがここに記載されています）。

---

## ディレクトリ構成

リポジトリの主要ファイル・モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                        — 環境変数／設定の読み込み
    - run_execution.py                 — ExecutionEngine 起動スクリプト
    - run_monitoring.py                — Monitoring ポーリング起動スクリプト
    - utils/
      - process_priority.py            — プロセス優先度・CPU affinity ユーティリティ
    - execution/
      - order_manager.py
      - reconciler.py
      - order_repository.py (他)       — 注文管理・ブローカー抽象
      - ...
    - monitoring/
      - monitoring_db.py               — SQLite スキーマ／永続化
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
      - streamlit_dashboard.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - data/ (想定)
      - prices / DuckDB / SQLite ファイル等
    - tools/
      - paper_verification_report.py
      - __init__.py

（上記は主要なファイルのみを抜粋しています。実際のリポジトリにはさらに execution/broker_* や data/pipeline 等のモジュールが存在します。）

---

## 運用上の注意

- Paper Trading モードは本番 DB と分離されますが、設定ミスに注意してください（環境変数の確認を推奨）。
- KillSwitch は監視コンポーネントからファイル書き込みによって ExecutionEngine 停止を要求します。flag ファイルの存在は Execution 起動時に確認・クリアされる挙動を設定できます（KILL_FLAG_CLEAR_ON_START）。
- OpenAI を使う機能は API 呼び出しの失敗やレート制限に対してエクスポネンシャルバックオフやフェイルセーフを組み込んでいますが、API キーや課金に注意してください。
- Streamlit ダッシュボードは監視 DB を read-only で開きます。監視 DB を同時に読み書きする場合のロックに注意してください（SQLite URI モードで読み取り専用に接続）。

---

## 参考（よく使うコマンド例）

- 仮想環境作成とパッケージインストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil requests openai streamlit

- Execution 起動（paper_trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動（ポーリング間隔 30 秒）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に入れる具体的な環境変数一覧（.env.example 形式）、起動時のログ例、よくあるトラブルシュート項目、あるいは各モジュールの API 使用例（コードスニペット）を追記します。どの情報が必要か教えてください。