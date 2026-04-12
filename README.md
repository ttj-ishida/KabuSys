# KabuSys

日本株自動売買システムのコードベース README（日本語）

この README はリポジトリ内の主要コンポーネントと使い方、セットアップ手順、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主な機能は以下の通りです。

- 注文管理・ブローカー連携（ExecutionEngine / OrderManager / Reconciler）
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築（候補選定・重み付け・株数計算・リスク調整）
- 研究用ファクター計算（momentum, volatility, value）と特徴量解析
- ニュース NLP による銘柄ごとのセンチメント評価（OpenAI）
- 市場レジーム判定（MA と LLM による合成）
- Paper Trading 用の分離された DB と検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

設計方針として、データ読み取りは DuckDB、監視や注文ログは SQLite を用い、外部 API（kabu/station, J-Quants, OpenAI 等）は明示的に扱います。Paper Trading 環境は本番 DB と完全分離されます。

---

## 主な機能一覧

- Execution（実行）
  - OrderManager: 注文作成 / 送信 / 同期
  - ExecutionEngine: 発注セッションの実行
  - Reconciler: 起動時の自動復旧・リコンシリエーション
  - BrokerFactory: 本番 / モックの切り替え（KABUSYS_ENV=paper_trading）

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス有無、データ鮮度確認
  - TradeMonitor: 滞留注文・約定異常チェック
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件により ExecutionEngine 停止フラグを書き込む
  - AlertManager: LINE Push による通知
  - Streamlit ダッシュボード（read-only モード）

- Portfolio（銘柄選定 / 配分）
  - 候補選定、等配分 / スコア加重、リスクベースの株数算出、セクターキャップ、レジーム乗数

- Research（研究）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）, 統計サマリー

- AI
  - news_nlp.score_news: raw_news から OpenAI を用いて銘柄別 ai_score を生成
  - regime_detector.score_regime: ETF MA とマクロニュースで日次レジーム判定

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10+（typing に union 演算子などを利用）
- SQLite は標準同梱
- DuckDB、psutil、requests、openai、streamlit などが必要

1. 仮想環境作成と有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

3. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須や推奨される環境変数（Settings クラス参照）:

     必須（未設定だと例外）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

     任意 / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG|INFO|...)
     - OPENAI_API_KEY — AI 機能使用時に必要
     - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH — 監視 DB デフォルト `data/monitoring.db`
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB デフォルト `data/paper_trading.db`
     - PAPER_FILL_MODE — paper_trading の約定挙動（instant|partial|never|reject、デフォルト `instant`）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

   簡易の .env 例:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

4. データディレクトリ作成
   - mkdir -p data

5. 初回 DB 初期化
   - 多くの起動スクリプトで自動的に monitoring DB のテーブル作成 (init_monitoring_db) を行います。初期化はそれらのスクリプト実行時に自動で行われます。

---

## 使い方（主要スクリプト例）

- 監視ループ（MonitoringEngine の一部を単独実行する簡易起動スクリプト）
  - python -m kabusys.run_monitoring
  - 環境変数: MONITOR_POLL_INTERVAL（ポーリング間隔秒、デフォルト 60）
  - 実行時にプロセス優先度を "high" に設定し、monitoring DB（Settings.sqlite_path）および DuckDB に接続します。

- ExecutionEngine（注文実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し `data/paper_trading.db` を利用（本番 DB と分離）。
  - 実行時にプロセス優先度を "high" に設定します。

- Streamlit 監視ダッシュボード（読み取り専用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 指定期間:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None) — DuckDB コネクションを渡して実行
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  注意: OpenAI API キーが必要（環境変数 OPENAI_API_KEY か api_key 引数）。API コストやレート制限に留意してください。

- ライブラリとしての利用
  - 例: ポートフォリオ構築関数
    - from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

---

## 監視・フェイルセーフの挙動（重要点）

- KillSwitch:
  - RiskMonitor が閾値超過（ドローダウン / ポジション上限）を検出すると `data/kill.flag` を書き込み、ExecutionEngine 停止のトリガーとなります。
  - KillSwitch のフラグは既存なら上書きしません（冪等）。

- Paper Trading 分離:
  - KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（通常 data/paper_trading.db）を用いて本番とログを完全に分離します。

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` があると自動で読み込まれます。OS 環境変数は保護されます。
  - 自動ロードを停止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env 自動読み込み等）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite ベースの監視ログ永続化層
  - system_monitor.py — システム状態 / データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常の監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書込みロジック
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 各モニタの取りまとめ
  - streamlit_dashboard.py — Streamlit ダッシュボード

- src/kabusys/execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py （注文 DB 操作）
  - execution_engine.py, broker_factory.py, broker_api.py（ブローカー抽象）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定, 重み計算
  - position_sizing.py — 株数決定 / 単元丸め / 投下資金調整
  - risk_adjustment.py — セクターキャップ, レジーム乗数

- src/kabusys/research/
  - factor_research.py — momentum/volatility/value 計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

- src/kabusys/ai/
  - news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores に書込
  - regime_detector.py — MA とマクロニュースで日次レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成ツール

- src/kabusys/utils/
  - process_priority.py — クロスプラットフォームのプロセス優先度 / CPU affinity 設定

---

## 追加の注意点 / ベストプラクティス

- 本番運用では KABUSYS_ENV を `live` に設定し、適切な DB パス・API 機密情報は OS 環境変数や安全なシークレット管理に置いてください。
- OpenAI を使う機能（news_nlp, regime_detector）は API キーと利用料が必要です。ローカルテストや CI ではモック化がおすすめです（コード中に API 呼び出し箇所は差し替え可能に設計されています）。
- Monitoring 周りは監視データの永続化やアラートの重複抑止（cooldown）等を備えていますが、運用時は通知先（LINE）・閾値（CPU, memory, dd 等）を適切に調整してください。
- Paper Trading 検証（tools.paper_verification_report）は稼働率・注文成功率・レイテンシ等をチェックするためのユーティリティです。運用改善時の指標として活用してください。

---

## よく使うコマンドまとめ

- 仮想環境作成・依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil requests openai streamlit

- 監視起動（ローカル）
  - python -m kabusys.run_monitoring

- Execution 起動（Paper か Live を環境変数で切替）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの主要点を要約したものです。詳細な設計やアルゴリズム（PortfolioConstruction.md や StrategyModel.md 等の参照）がリポジトリ内にある想定ですので、実装・運用の際は該当ドキュメントを併せて参照してください。質問や追加で README に載せたい内容があれば教えてください。