# KabuSys

日本株向け自動売買システムのサブセット実装。ポートフォリオ構築、発注エンジン、監視・アラート、研究用ファクター計算、ニュースNLP（OpenAI）連携などのコンポーネントを含む。

バージョン: 0.1.0

---

## 概要

このリポジトリは、KabuSys と呼ばれる日本株自動売買システムの主要機能群をモジュール化して実装しています。主な目的は以下：

- 戦略（ファクター計算・特徴量解析）とポートフォリオ構築
- 発注・約定の管理（ExecutionEngine 関連コンポーネント）
- 実行状況・リスクの監視（Monitoring）
- ニュースを用いた NLP スコアリング（OpenAI 経由）
- Paper Trading 用の分離された DB と検証レポート生成

各機能はライブラリとして利用でき、コマンドライン / サービスとして起動するエントリポイントも提供します。

---

## 主な機能一覧

- portfolio
  - 銘柄候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - セクター集中制限、レジーム乗数（apply_sector_cap / calc_regime_multiplier）
  - 発注株数算出（リスクベース・等配分等）
- research
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（Information Coefficient）等
- execution
  - OrderManager / OrderRepository / Reconciler（注文管理・再整合）
  - ExecutionEngine（起動スクリプトあり）
  - Broker クライアントの抽象化（本番 / Paper 環境対応）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor（CPU・データ鮮度・滞留注文・ドローダウン等）
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
  - KillSwitch（kill.flag による ExecutionEngine 停止）
  - AlertManager（LINE Push 通知）
  - Streamlit ダッシュボード（read-only 表示）
- ai
  - ニュースセンチメント（OpenAI）を銘柄ごとにスコア化して ai_scores に保存
  - 市場レジーム判定（ETF MA + マクロニュース + LLM）
- tools
  - paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要な主要パッケージ（代表例）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - requirements.txt がない場合は手動でインストール:
     - pip install duckdb psutil openai requests streamlit

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数設定
   - ルートに `.env` / `.env.local` を置くと自動読み込みされます（Settings モジュールがプロジェクトルートを探索して自動ロードします）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

6. 最低限必要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN — （必須）
   - KABU_API_PASSWORD — （必須）
   - OPENAI_API_KEY — OpenAI を使用する機能で必要
   - その他はデフォルト値を持ちます（README 下部の環境変数一覧参照）

注意: Paper Trading（KABUSYS_ENV=paper_trading）では paper 用の SQLite DB を分離して使用します（デフォルト: data/paper_trading.db）。

---

## 使い方（主要エントリポイント）

以下はいくつかの主要な起動方法と使い方例です。

1. Monitoring（ポーリング監視）を起動
   - 動作: SystemMonitor を定期ポーリングし、monitoring SQLite（デフォルト data/monitoring.db）へログを格納します。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。
   - 実行:
     - python -m kabusys.run_monitoring
   - ポーリング間隔を上書き:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     - デフォルトは 60 秒
   - 停止:
     - data/stop_requested.flag を作成するとループが検出して終了します（同ファイルはプロジェクトルート/data/stop_requested.flag）。

2. ExecutionEngine（発注エンジン）を起動
   - 実行:
     - python -m kabusys.run_execution
   - Paper Trading モード:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - paper_trading 時は MockBrokerClient を使い、data/paper_trading.db に結果を記録（本番DBと完全分離）。
   - 停止:
     - data/stop_requested.flag（存在時にエンジン起動を抑止／稼働中に検出して停止）
   - PID ファイル: data/execution.pid を生成・参照します。

3. Streamlit ダッシュボード（監視表示）
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only の表示で、monitoring DB が存在しない場合はエラー表示になります。

4. Paper Trading 検証レポート生成
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - オプション:
       - --from YYYY-MM-DD
       - --to YYYY-MM-DD
       - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）
   - 出力: 標準出力に検証レポート（稼働率 / 注文成功率 / 送信率 / レイテンシ等）。基準値はスクリプト内部で定義されています。

5. AI 機能（ライブラリ関数）
   - ニューススコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key=...)
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key=...)

---

## 環境変数一覧（主なもの）

- KABUSYS_ENV
  - 有効値: development | paper_trading | live
  - デフォルト: development

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API 用トークン

- KABU_API_PASSWORD (必須)
  - kabuステーション API パスワード

- OPENAI_API_KEY
  - OpenAI 呼び出し時に使用

- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
  - AlertManager（LINE Push）用。未設定なら送信はスキップされログのみ。

- PAPER_FILL_MODE
  - Paper Trading の MockBrokerClient fill mode
  - 有効値: instant | partial | never | reject
  - デフォルト: instant

- PAPER_TRADING_SQLITE_PATH
  - paper_trading 用 SQLite パス（デフォルト: data/paper_trading.db）

- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH
  - 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）

- PID_FILE_PATH
  - ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）

- KILL_FLAG_PATH
  - KillSwitch 用フラグファイル（デフォルト: data/kill.flag）
  - KillSwitch を使うと該当条件で flag を書き込み ExecutionEngine に停止を促す

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング秒数（デフォルト: 60）
  - 0 以下 / 不正な値はデフォルトにフォールバック

- LOG_LEVEL
  - ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - デフォルト: INFO

その他、細かい閾値やパスは Settings クラスで確認できます（src/kabusys/config.py）。

---

## 注意事項 / 実装上のポイント

- DB 分離
  - paper_trading 環境は paper_sqlite_path を使い、本番 monitoring DB と完全に分離します。
  - Monitoring は KABUSYS_ENV にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用します。

- Kill/Stop 管理
  - data/stop_requested.flag: run_monitoring/run_execution の外部停止用フラグ
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止シグナルを送る用途
  - ExecutionEngine は PID ファイル（data/execution.pid）を参照し stale PID を検出すると削除・アラート出力します。

- OpenAI 呼び出し
  - ニュースNLP・レジーム判定はいずれも OpenAI API（gpt-4o-mini）を使用する想定。API 呼び出しはリトライやフォールバック（失敗時の安全動作）を備えています。
  - API キーは引数で渡すか OPENAI_API_KEY 環境変数を設定してください。

- ロギングと優先度
  - 起動直後に set_process_priority("high") を呼び出してプロセス優先度を上げます（psutil を利用、権限がない場合は警告ログのみ）。

- DuckDB
  - 研究用ファクター計算や AI の集約処理は DuckDB に対して SQL を発行する設計です。prices_daily / raw_financials / raw_news 等のテーブル想定。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - utils/
      - __init__.py
      - process_priority.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 execution 関連モジュール)
    - tools/
      - __init__.py
      - paper_verification_report.py
- data/
  - monitoring.db (デフォルトの監視 SQLite)
  - paper_trading.db (paper_trading 用 DB)
  - execution.pid
  - stop_requested.flag
  - kill.flag

（注）上は主要ファイルを抜粋した構成です。実際のリポジトリでは他の補助モジュールやマスタが存在することがあります。

---

## よくある運用コマンド（サンプル）

- Monitoring をバックグラウンドで起動（systemd 等を使う想定）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring &

- ExecutionEngine を Paper モードで起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper 検証レポート（2026-04-01 〜 2026-04-11）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 開発者向けメモ

- Settings（src/kabusys/config.py）はプロジェクトルート（.git または pyproject.toml を基準）を探して `.env` / `.env.local` を自動ロードします。テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MonitoringDB（monitoring_db.py）は初回実行時にテーブル・インデックスを作成し、マイグレーション的にカラム追加（例: latency_ms, peak_value）を行います。
- AI 関連の OpenAI 呼び出しは外部ネットワークに依存するため、単体テスト時は _call_openai_api をモックすることを推奨します。
- 単体関数群（portfolio/*, research/*）は副作用がなく純粋関数設計になっているため、ユニットテストを作成しやすいです。

---

必要であれば README に以下を追加できます：
- sample .env.example（推奨される環境変数の雛形）
- systemd / supervisor 用のサービスユニット例
- さらなる運用手順（バックアップ、DB 初期化方法、ローテーション等）

上記追加を希望する場合は、どの内容を優先して追加するか教えてください。