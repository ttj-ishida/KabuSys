# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ + 実行スクリプト）。  
このリポジトリは取引エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント / レジーム判定）等の主要コンポーネントを含みます。

---

## 概要

KabuSys は以下の関心事を分離して設計された Python ベースの自動売買コードベースです。

- ExecutionEngine：ブローカーとの発注・状態管理、リスク管理、リコンシリエーション
- Monitoring：プロセス生存、システム負荷、注文の滞留・約定異常、ドローダウン監視、アラート送信
- Portfolio：銘柄選定・重み付け・株数計算（等配分・スコア加重・リスクベース）
- Research：ファクター計算（Momentum / Volatility / Value）や特徴量解析
- AI：ニュースセンチメント（OpenAI）や市場レジーム判定（OpenAI を使用）
- Tools：Paper Trading 検証レポート生成、Streamlit ダッシュボードなど

設計方針として「本番データに対するルックアヘッド防止」「外部副作用の最小化」「クラッシュ時の冪等性」「フェイルセーフ（外部 API 失敗時のフォールバック）」などが採用されています。

---

## 主な機能一覧

- Execution
  - ブローカー抽象化（生の API 呼び出しを隠蔽）
  - 注文状態管理（OrderManager / OrderRepository）
  - 再起動時の自動リコンシリエーション（Reconciler）
  - RiskManager による発注制限

- Monitoring
  - SystemMonitor：CPU/メモリ/Disk、データ鮮度、PID ファイル確認
  - TradeMonitor：滞留注文、約定価格の異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件により ExecutionEngine 停止指示（flag ファイル）
  - AlertManager：LINE Push による通知（クールダウン制御）
  - Streamlit ベースの監視ダッシュボード

- Portfolio（純粋関数）
  - 銘柄候補選定（score ソート）
  - 等金額 / スコア加重重み計算
  - セクターキャップ適用
  - ポジションサイズ計算（単元丸め、aggregate cap）

- Research
  - モメンタム / ボラティリティ / バリューのファクター計算（DuckDB）
  - 将来リターン、IC（Information Coefficient）、統計サマリー

- AI
  - ニュースを LLM でセンチメント評価して ai_scores に保存（OpenAI）
  - マクロニュース + ETF MA200 による市場レジーム判定（OpenAI）

- Tools
  - paper_verification_report：Paper Trading の検証レポート生成
  - streamlit_dashboard：監視 DB を可視化するダッシュボード

---

## 必要条件（推奨）

- Python 3.10+
  - 型アノテーションに `X | Y`（PEP 604）を使用しているため 3.10 以上を推奨します。
- DuckDB（python パッケージ: duckdb）
- sqlite3（標準ライブラリ）
- psutil
- requests
- openai（OpenAI Python SDK）
- streamlit（ダッシュボード使用時）
- その他（必要に応じて）:
  - pip 等のパッケージ管理ツール

---

## セットアップ手順

1. リポジトリをクローン／配置
   - このリポジトリルートに移動します（.git / pyproject.toml を基準に自動 .env 読み込みが行われます）。

2. Python 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに pyproject.toml / requirements.txt があればそちらを使用）

4. 環境変数を設定
   - ルートに `.env`（または `.env.local`）を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 主な環境変数（Settings クラスに定義）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な場合）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV: 起動環境（development / paper_trading / live） — デフォルト development
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite ファイル（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
     - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
     - KILL_FLAG_PATH: Kill flag ファイル（デフォルト data/kill.flag）
     - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするなら "1"
     - PAPER_FILL_MODE: paper_trading 時の MockBroker の fill モード（instant|partial|never|reject）

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方

基本的な起動・コマンドの例を示します。

- ExecutionEngine を起動（本番または paper_trading に応じて内部で DB を分離）
  - python -m kabusys.run_execution
  - 実行前に環境変数 KABUSYS_ENV を設定:
    - 本番: export KABUSYS_ENV=live
    - Paper Trading: export KABUSYS_ENV=paper_trading
  - paper_trading の場合、MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。

- Monitoring を起動（プロセスのポーリング監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒単位に上書き可能（デフォルト 60 秒）。
  - Monitoring は常に本番用 sqlite_path（SQLITE_PATH）を使用します（環境に関係なく監視 DB は本番 DB を参照）。

- Streamlit ダッシュボード（監視データの可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - または Python モジュールとして:
    - python -m kabusys.monitoring.streamlit_dashboard --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 関連（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要です（環境変数 OPENAI_API_KEY または関数引数）。
  - ニューススコアリングをプログラムから呼ぶ例:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, date(2026, 4, 1))
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, date(2026, 4, 1))

注意点:
- 実行スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil 権限がない場合は警告が出ます）。
- kill.flag（Settings.kill_flag_path）を書き込むことで ExecutionEngine に停止要求を出す設計です（KillSwitch が判定してファイルを書きます）。ExecutionEngine 側はこの flag を確認して適切に終了する実装が前提です。

---

## 設定（主な Settings の一覧）

Settings クラスにより以下のプロパティが提供されます（環境変数名は括弧内）。

- J-Quants / 外部 API
  - jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
- kabu ステーション API
  - kabu_api_password (KABU_API_PASSWORD)
  - kabu_api_base_url (KABU_API_BASE_URL, デフォルト http://localhost:18080/kabusapi)
- LINE 通知
  - line_channel_access_token (LINE_CHANNEL_ACCESS_TOKEN)
  - line_user_id (LINE_USER_ID)
- DB パス
  - duckdb_path (DUCKDB_PATH, default data/kabusys.duckdb)
  - sqlite_path (SQLITE_PATH, default data/monitoring.db)
  - paper_sqlite_path (PAPER_TRADING_SQLITE_PATH, default data/paper_trading.db)
  - paper_fill_mode (PAPER_FILL_MODE, default "instant")
- 監視 / PID / kill flag
  - pid_file_path (PID_FILE_PATH, default data/execution.pid)
  - kill_flag_path (KILL_FLAG_PATH, default data/kill.flag)
  - kill_flag_clear_on_start (KILL_FLAG_CLEAR_ON_START, "1" or "0")
  - cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct
- システム
  - env (KABUSYS_ENV): development / paper_trading / live
  - log_level (LOG_LEVEL)

---

## ディレクトリ構成（主なファイル）

リポジトリの主要モジュールと簡単な説明を示します（抜粋）。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリング起動スクリプト

  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (存在)
    - execution_engine.py (存在)
    - broker_factory.py / broker_api.py（ブローカー抽象）
    - ...（発注関連）

  - monitoring/
    - monitoring_db.py — SQLite による監視 DB 層
    - system_monitor.py — CPU/メモリ/DISK / データ鮮度 / PID チェック
    - trade_monitor.py — 注文滞留 / 約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の読み書き
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各 Monitor を束ねるランナー
    - streamlit_dashboard.py — Streamlit ベースの監視 UI

  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み付け
    - position_sizing.py — 株数算出（丸め・スケーリング）
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — Momentum / Volatility / Value 計算（DuckDB利用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
    - __init__.py

  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書込
    - regime_detector.py — ETF MA200 + マクロニュースでレジーム判定
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
    - __init__.py

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意 / ベストプラクティス

- Paper Trading と本番 DB は完全分離してください（KABUSYS_ENV により paper_trading 時は PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API キーは安全に管理し、必要な場合にのみ設定してください。AI モジュールは API 失敗時にフォールバックする設計ですが、誤ったキーだと期待する出力が得られません。
- Monitoring は常に本番監視 DB（SQLITE_PATH）を参照するため、テストや別環境で実行する場合は別 DB を用意するか、環境変数を調整してください。
- pid ファイルと kill.flag の運用ルールを運用手順書にまとめ、誤った停止を防いでください。
- DuckDB の prices_daily / raw_financials / raw_news 等のテーブルはリサーチ/AI モジュールの前提となるため、適切にデータを投入してください。

---

## ライセンス / 貢献

README に記載のない事項（テスト、CI、パッケージ化設定等）は pyproject.toml / LICENSE 等を参照してください。  
バグ報告・改善提案は Issue を立ててください。

---

この README はコード内の docstring と Settings に基づいて作成しています。必要があれば起動例・env サンプル・運用手順書（runbook）を別ドキュメントとして追加できます。必要な内容を教えてください。