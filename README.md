# KabuSys

日本株自動売買システムのコードベース抜粋の README（日本語）。

この README はリポジトリ内の主要モジュール・起動スクリプト・設定方法・利用方法・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買／ポートフォリオ構築／監視／リサーチを目的とした Python ベースのシステムです。本リポジトリには以下の主要機能群が含まれます。

- 発注エンジン（ExecutionEngine）: ブローカー API 経由で注文を発行・管理。paper_trading 環境ではモックブローカーを使用して本番 DB と分離。
- 監視（Monitoring）: システム稼働状況・注文滞留・リスク（ドローダウン・ポジション上限）を定期チェックしログ・アラート・kill スイッチを扱う。
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、ポジションサイズ算出、セクター制限やレジーム調整。
- リサーチ（Research）: DuckDB 上の価格・財務データからファクター（モメンタム／ボラティリティ／バリュー）や将来リターン、IC 等を計算。
- AI モジュール（AI）: ニュースを LLM（OpenAI）でスコアリングし、マクロセンチメントと組み合わせて市場レジームを判定。
- ユーティリティ: プロセス優先度設定、Streamlit ダッシュボード、検証レポート生成ツール等。

---

## 主な機能一覧

- Execution
  - ブローカー抽象化（BrokerClientFactory）
  - OrderManager / OrderRepository / Reconciler による注文管理・再整合
  - リスク管理（RiskManager）
- Monitoring
  - SystemMonitor: CPU/Memory/Disk・データ鮮度・プロセス監視
  - TradeMonitor: 注文滞留・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: リスク条件で kill.flag を書き込み Execution を停止
  - AlertManager: LINE push による通知（クールダウン管理あり）
  - Streamlit ダッシュボード（read-only な monitoring.db 表示）
- Portfolio
  - 候補選定・スコアに基づく重み計算・等配分
  - ポジションサイズ計算（単元株丸め・aggregate cap）
  - セクター制限・レジーム乗数
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC・統計サマリ
- AI
  - news_nlp: raw_news を LLM で銘柄ごとにセンチメント評価して ai_scores に書き込み
  - regime_detector: ETF MA200 とマクロニュースを LLM で組み合わせて market_regime を判定
- Tools
  - paper_verification_report: Paper Trading DB を解析し検証レポートを生成

---

## セットアップ手順

下記は一般的な開発環境の準備手順です。実際のプロジェクトでは pyproject.toml / requirements.txt を参照して依存関係をインストールしてください。

1. Python をインストール（3.9+ を想定）
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - （SQLite は標準ライブラリで利用可能）
4. リポジトリルートに `.env` を作成（任意）。自動読み込みについては下記参照。

必須/重要な環境変数（最低限設定が必要なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用アクセストークン（必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY — OpenAI API を利用する機能を使う場合
- KABUSYS_ENV — 実行環境。allowed: development, paper_trading, live（デフォルト: development）

その他の主要な環境変数（省略可能／デフォルトあり）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (instant|partial|never|reject, default: instant)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まない（テスト等で便利）

.env 自動読み込み
- ルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` が起動時に自動でロードされます（OS 環境変数が優先、`.env.local` は上書き）。
- 自動読み込みをオフにするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定します。

---

## 使い方（実行例）

実行はパッケージルート（src を PYTHONPATH に含める、またはパッケージとしてインポート可能な状態）から行ってください。

1. 監視ループ起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 実行時にプロセス優先度を "high" に設定します。
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（秒、デフォルト 60）。
   - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが終了します。

2. Execution エンジン起動（発注エンジン）
   - python -m kabusys.run_execution
   - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使い paper_trading.db に書き込みを行い本番 DB と分離します。
   - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
   - 実行中に停止するには data/stop_requested.flag を作成するか、Monitoring の KillSwitch が `data/kill.flag` を書き込むことで停止シグナルを発行できます。

3. Streamlit ダッシュボード（監視 UI）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で monitoring.db を開き、ダッシュボード・ポジション・注文履歴・最新システム状態・リスクログを表示します。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - もしくは明示的に DB を指定: --db path/to/paper_trading.db
   - 各種合格基準（稼働率・注文成功率・送信率・P95 レイテンシ）に基づく PASS/FAIL レポートを標準出力に出力します。

5. AI／レジーム判定・ニューススコア
   - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼び出して利用します（OpenAI API キーが必要）。

停止フラグ・kill フラグについて
- data/stop_requested.flag: run_monitoring/run_execution の外部停止制御に使用（存在で停止）。
- data/kill.flag: Monitoring の KillSwitch が書き込むフラグ。ExecutionEngine 側で検出して安全停止を行います。
- フラグの削除は手動または KillSwitch.clear() で可能。

ログ
- 起動スクリプトは logging.basicConfig(level=logging.INFO) で INFO レベル以上を表示します。環境変数 LOG_LEVEL で変更可能（DEBUG/INFO/...）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージのメタ情報（__version__ 等）
  - config.py — 環境変数・設定管理（.env 自動ロード含む）、Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py — ニュースを LLM でセンチメント評価し ai_scores に書き込む
    - regime_detector.py — ETF MA200 とマクロニュースの合成でレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション数監視
    - kill_switch.py — kill.flag の生成／管理
    - alert_manager.py — LINE push 通知（クールダウン管理）
    - monitoring_engine.py — 各 monitor を束ねるループ（テスト用 run_once/本番 run）
    - streamlit_dashboard.py — Streamlit での監視 UI
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (参照あり)
    - order_record.py (参照あり)
    - broker_factory.py / broker_api.py (ブローカー抽象)
    - execution_engine.py (起動・セッション管理)
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - tools/
    - paper_verification_report.py — Paper Trading DB の評価レポート生成
  - utils/
    - process_priority.py — OS に依存しないプロセス優先度/CPU affinity 設定
  - data/ (実行時に利用するファイルを置く想定)
    - monitoring.db (SQLite)、paper_trading.db、kabusys.duckdb、stop_requested.flag、kill.flag、execution.pid など

（補足）DuckDB はリサーチ・AI 関連の大規模/列志向クエリに用いられ、prices_daily / raw_financials / raw_news / ai_scores / market_regime 等のテーブルを扱います。監視ログは SQLite（monitoring.db）で永続化されます。

---

## 備考 / 運用上の注意

- Paper Trading と本番 DB は分離されています。KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使って別 DB に記録されます（本番DBと完全分離）。
- .env パーサはシェル風のクォート・エスケープとインラインコメントをある程度サポートします。`.env.local` により開発者固有の上書きを想定しています。
- OpenAI（LLM）呼び出しはリトライ（指数バックオフ）・レスポンスのバリデーション・スコアクリップなどのセーフガードを備えています。API キーの漏洩に注意してください。
- process priority / cpu affinity の設定はプラットフォーム差分を吸収しますが、権限不足により失敗する場合は警告に留めます。
- monitoring_db.init_monitoring_db は冪等でスキーママイグレーション（列追加）を簡易的に行います。DB バックアップを運用に組み込んでください。

---

この README はコードコメント・モジュール構成に基づいて作成しています。実際の運用では pyproject.toml / requirements.txt / .env.example 等の補足ドキュメントを参照し、適切なセキュリティ・監視・運用プロセスを整備してください。