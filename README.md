# KabuSys

日本株向けの自動売買システムのサブセット実装です。  
このリポジトリは戦略の生成・ポートフォリオ構築・注文管理（Execution）・監視（Monitoring）・研究用ユーティリティ・AI ベースのニュースセンチメント評価など、運用に必要な主要コンポーネントを含みます。

以下はこのコードベースを使い始めるための README です。

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- 環境変数 / 設定
- セットアップ手順
- 実行方法（使い方）
  - ExecutionEngine の起動
  - Monitoring の起動
  - 監視ダッシュボード（Streamlit）
  - Paper Trading 検証レポート生成ツール
  - AI モジュール（ニュース NLP / レジーム判定）
- 運用上の注意点（フラグファイル・PID・ポーリング間隔）
- ディレクトリ構成（主要ファイル説明）

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。  
主な役割は以下の通りです：

- Execution: シグナル受領 → 注文作成 → ブローカー（実ブローカー or モック）へ発注 → 注文状態管理
- Monitoring: システム状態・注文状態・リスク指標を定期ポーリングしてログ・アラート・キルスイッチを管理
- Portfolio: 候補選定・重み計算・ポジションサイズ算出・セクター調整
- Research: DuckDB 上の株価・財務データからファクターを計算するユーティリティ群
- AI: OpenAI を利用したニュースセンチメント（news_nlp）および市場レジーム判定（regime_detector）
- Tools: Paper Trading の検証レポート生成など運用補助ツール

---

## 機能一覧

- 注文管理（OrderManager / OrderRepository / ExecutionEngine）
- ブローカー抽象化（実ブローカーと paper_trading 用の MockBroker 切替）
- 自動リコンシリエーション（再起動時の注文/ポジション同期）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）
  - CPU / メモリ / ディスク使用率のログ化
  - 注文滞留・約定異常価格の検知
  - ドローダウン / ポジション上限の監視と kill.flag への書き出し
- アラート送信（LINE Messaging API 経由、cooldown 管理）
- Monitoring DB（SQLite）への永続化 + Streamlit ダッシュボード
- Portfolio 構築ユーティリティ（候補選別、等重・スコア重み、リスクベース配分）
- Research 用ファクター計算（Momentum, Volatility, Value 等）
- AI ベースのニュースセンチメント集計（OpenAI）
- Paper Trading 用検証レポート出力ツール

---

## 必要条件

- Python 3.10+
- 依存ライブラリ（主なもの）
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード起動時)
  - openai (AI モジュール利用時)
  - その他（標準ライブラリのみで動く部分も多い）

requirements.txt が無い場合は上記を pip でインストールしてください。

例:
pip install duckdb psutil requests streamlit openai

---

## 環境変数 / 設定

自動読み込み:
- プロジェクトルートにある `.env` と `.env.local` が自動読み込みされます（OS 環境変数が優先）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（Settings で参照されるもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI 利用時の API キー（AI モジュール使用時に必須）
- KABUSYS_ENV: 実行モード ("development" | "paper_trading" | "live")（デフォルト: development）
  - paper_trading の場合、MockBroker を使用し、Paper Trading 用の専用 SQLite を使用します
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB パス（デフォルト: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定時は通知スキップ）
- PID_FILE_PATH, KILL_FLAG_PATH: 実行時に使用するファイルパス（デフォルトを参照）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（"DEBUG"|"INFO"|...）

必須環境変数が足りない場合、Settings が ValueError を投げます。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests streamlit openai
4. 環境変数を用意
   - プロジェクトルートに `.env` を作成（.env.example を参考に）
   - 例（.env）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development
5. データディレクトリを作成（任意）
   - mkdir -p data

DuckDB / SQLite の初期スキーマは実行時に必要なテーブルを作成する処理が含まれています（monitoring_db.init_monitoring_db など）。

---

## 使い方

以下は主要なエントリポイントの実行方法例です。プロジェクトルート（src 配下が PYTHONPATH に含まれる状態）で実行してください。パッケージとしてインストールしている場合は python -m モードで動きます。

注意: 実運用で ExecutionEngine を動かす際は KABUSYS_ENV を適切に設定してください。paper_trading を使うと本番 DB を汚染しません。

### ExecutionEngine の起動

- コマンド:
  - python -m kabusys.run_execution
- 動作:
  - プロセス優先度を high に設定（可能な場合）
  - Settings に従い SQLite / DuckDB に接続
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用して paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録
  - data/stop_requested.flag が存在する場合は起動せず終了
  - 実行中は data/execution.pid に PID を書きます

### Monitoring の起動

- コマンド:
  - python -m kabusys.run_monitoring
- 動作:
  - Settings に従い monitoring 用 SQLite（Settings.sqlite_path）および DuckDB に接続
  - SystemMonitor.check_once をポーリング（デフォルト 60 秒、MONITOR_POLL_INTERVAL で上書き可能）
  - stop_requested.flag 検知でループを終了
- ポーリング間隔の設定:
  - MONITOR_POLL_INTERVAL=30 など（秒）。不正値はデフォルト 60 秒にフォールバック。

### 監視ダッシュボード（Streamlit）

- コマンド:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 動作:
  - monitoring の SQLite（読み取り専用推奨）を参照してダッシュボードを表示

### Paper Trading 検証レポート生成ツール

- コマンド:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB:
  - 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
- 出力:
  - 指定期間の稼働率・注文成功率・送信率・レイテンシ等をまとめて標準出力に表示

### AI モジュール（ニュース NLP / レジーム判定）

- 事前準備:
  - OPENAI_API_KEY を環境変数に設定するか、関数引数で渡す
- 主要関数:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores を使ってニュースごとのセンチメントを ai_scores に書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF (1321) の MA200 とマクロニュースを合成して market_regime テーブルへ書き込む
- 注意:
  - API 呼び出しはリトライやフェイルセーフが組み込まれていますが、API キー未設定だと例外になります
  - LLM レスポンスのバリデーションを行い、スコアは範囲でクリップされます

---

## 運用上の注意点

- kill.flag / stop_requested.flag:
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を記したファイルを書き込み、ExecutionEngine に停止シグナルを送ります。
  - run_execution/run_monitoring は data/stop_requested.flag を参照して終了判定を行います。
- PID ファイル:
  - run_execution は data/execution.pid に PID を書きます。SystemMonitor は PID ファイルを参照してプロセスの健全性を判定します。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は必要なテーブルと一部カラム（peak_value, latency_ms）の追加を行うマイグレーションを含みます（冪等）。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合は本番 DB と完全分離して paper_trading 用 SQLite に記録されます（PAPER_TRADING_SQLITE_PATH）。
- ログレベル:
  - Settings.log_level を使ってログ出力レベルを制御できます（環境変数 LOG_LEVEL）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールとファイルの説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込みと Settings クラス（.env 自動ロード、必須チェック）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（PID / stop flag / paper_trading 対応）
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL）
  - execution/
    - execution_engine.py (エンジン本体) — ※主要ロジックのエントリポイント
    - broker_factory.py / broker_api.py (ブローカー抽象化)
    - order_manager.py (OrderManager)
    - order_repository.py (DB 操作)
    - reconciler.py (再起動時のリコンシリエーション)
    - ...
  - monitoring/
    - monitoring_db.py (SQLite 永続化層)
    - system_monitor.py (CPU/メモリ/ディスク、データ鮮度、PID チェック)
    - trade_monitor.py (滞留注文・約定異常検出)
    - risk_monitor.py (ドローダウン・ポジション上限監視)
    - kill_switch.py (kill.flag 制御)
    - alert_manager.py (LINE 通知)
    - monitoring_engine.py (各 Monitor の統合)
    - streamlit_dashboard.py (Streamlit ダッシュボード)
  - portfolio/
    - portfolio_builder.py (候補選定、重み付け)
    - position_sizing.py (株数計算、lot 単位切り捨て・スケール調整)
    - risk_adjustment.py (セクターキャップ、レジーム乗数)
  - research/
    - factor_research.py (Momentum/Volatility/Value 計算)
    - feature_exploration.py (将来リターン、IC、統計サマリー)
  - ai/
    - news_nlp.py (ニュース文章を OpenAI でスコアリング)
    - regime_detector.py (マクロ + MA200 を用いたレジーム判定)
  - tools/
    - paper_verification_report.py (Paper Trading の検証レポート出力)
  - utils/
    - process_priority.py (プロセス優先度・CPU affinity 設定ユーティリティ)

---

## 参考コマンドまとめ

- 実行
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Python モジュールとして関数呼び出し（AI など）
  - Python スクリプト内で import kabusys.ai as ai; ai.score_news(conn, date(2026,4,1))

---

README は以上です。実運用・開発で追加のドキュメントや運用手順（デプロイ、監視、バックアップ、 secrets 管理）が必要であれば、その点を教えてください。さらに詳しいセットアップ手順（systemd / docker / CI 用設定例）も作成できます。