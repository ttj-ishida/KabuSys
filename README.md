# KabuSys

軽量な日本株自動売買システムのコアライブラリ群（監視・実行エンジン・ポートフォリオ構築・リサーチ・AI連携など）。  
このリポジトリには、実運用/ペーパートレードで使える実装の主要コンポーネントが含まれています。

注意: ここに示す起動例は開発環境での利用を想定しています。本番運用では権限・APIキー・ネットワーク設定等を十分検討してください。

---

## プロジェクト概要

KabuSys は以下の主要機能を備えたモジュール群です。

- 注文の生成・管理・リコンシリエーション（ExecutionEngine / OrderManager / Reconciler）
- システム健全性・注文状態・リスクの監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- LINE を用いたアラート送信（AlertManager）
- Paper Trading 用 DB と検証レポート生成ツール（tools.paper_verification_report）
- ニュースを LLM で解析する NLP スコアリング・レジーム判定（ai.news_nlp / ai.regime_detector）
- ポートフォリオ構築ロジック（portfolio/*）
- 研究用ファクター計算・特徴量解析（research/*）
- DuckDB / SQLite を使ったデータアクセス

設計方針の一部:
- DuckDB を分析用、SQLite を監視/注文ログ用に使い分け
- Paper Trading は本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH）
- LLM 呼び出しはフェイルセーフ（失敗時は安全なフォールバック）

---

## 主な機能一覧

- 実行エンジン（run_execution.py）
  - 本番 / ペーパートレードを切り替え可能
  - BrokerClientFactory により MockBroker を利用可能
  - PID ファイルを書き込み、stale PID の検出を行う

- 監視エンジン（run_monitoring.py / monitoring.*）
  - システム状態（CPU/Memory/Disk）、プロセス生存、データ鮮度を定期記録
  - 注文滞留・約定異常・ドローダウン等のリスク監視とログ化
  - Kill Switch による停止シグナル生成
  - Streamlit ダッシュボードで可視化可能

- AI（kabusys.ai）
  - news_nlp.score_news: OpenAI を用いたニュースセンチメントを ai_scores テーブルへ書込
  - regime_detector.score_regime: ma200 と LLM マクロセンチメントを合成して日次レジーム判定

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数

- リサーチ（kabusys.research）
  - ファクター計算（momentum / volatility / value / forward returns 等）
  - IC（Information Coefficient）や統計サマリの算出

- ユーティリティ
  - 環境変数自動読み込み（.env / .env.local）: kabusys.config.Settings
  - プロセス優先度設定・CPU affinity（kabusys.utils.process_priority）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <this-repo>
   cd <this-repo>
   ```

2. Python 仮想環境の作成（推奨: Python 3.10+）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell / cmd)
   ```

3. 必要パッケージをインストール（最低限）
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   ※ 実運用では requirements.txt / pyproject.toml を参照して下さい（本リポジトリに合わせて調整）。

4. 環境変数設定
   - プロジェクトルートの `.env` / `.env.local` を使って設定できます（自動読み込み）。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   代表的な環境変数（主なもののみ）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - OPENAI_API_KEY (LLM を使う場合必須)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (アラート送信用)
   - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
   - PAPER_FILL_MODE (instant | partial | never | reject) デフォルト: instant
   - PID_FILE_PATH (デフォルト: data/execution.pid)
   - KILL_FLAG_PATH (デフォルト: data/kill.flag)
   - MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒、デフォルト 60)

   例 (.env):
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   ```

5. DB の初期化
   - 監視用 SQLite は起動時に `init_monitoring_db` によってテーブル作成（冪等）されます。特別な手順は不要です。
   - DuckDB のスキーマ（prices_daily, raw_financials 等）は外部データ投入が必要です（CSV / ETL pipeline を想定）。

---

## 使い方

基本的な実行例を示します。プロジェクトルートでの実行を想定しています。

- 監視ループを起動
  - MONITOR_POLL_INTERVAL によりポーリング間隔を秒で上書き可能（デフォルト 60）
  ```
  # 直接ファイル実行
  python src/kabusys/run_monitoring.py

  # またはパッケージとして（パッケージをインストール / PYTHONPATH を通している場合）
  python -m kabusys.run_monitoring
  ```

  停止:
  - プロジェクトの data/stop_requested.flag を作成するとループが安全終了します（スクリプトは stop flag の存在をチェックします）。

- 実行エンジンを起動（Execution）
  - Paper trading で起動する例:
  ```
  KABUSYS_ENV=paper_trading python src/kabusys/run_execution.py
  ```
  - Live / development でも同様に環境変数を切り替えます。

  備考:
  - paper_trading 環境では MockBrokerClient が使用され、専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ書き込みます。
  - エンジンは PID ファイル（data/execution.pid）を使ってプロセス存在を検出します。
  - 停止フラグ (data/stop_requested.flag) が存在すると起動を中止、または実行中に検出して停止します。

- Streamlit ダッシュボード
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  引数の `--` 以降はスクリプト側へ渡るため、`--db` で DB パスを指定できます。

- Paper Trading 検証レポート
  ```
  # デフォルト DB を使う
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB パス明示
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI スコアリング / レジーム判定（ライブラリ API として）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  いずれも OpenAI API キーを引数で渡すか、環境変数 OPENAI_API_KEY を設定して使用します。

---

## 重要ファイル / フラグ

- data/stop_requested.flag
  - run_monitoring / run_execution が無限ループを終了するために参照する停止フラグ

- data/kill.flag
  - KillSwitch が書き込む停止シグナル。ExecutionEngine 等で検出すると安全停止処理を行う設計

- data/execution.pid
  - ExecutionEngine が書き込む PID ファイル。SystemMonitor は stale PID を検出して削除・アラート記録を行う

---

## ディレクトリ構成

主要なファイル/ディレクトリのツリー（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数/Settings 管理
    - run_monitoring.py             — 監視ループ起動スクリプト
    - run_execution.py              — 実行エンジン起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート CLI
    - ai/
      - news_nlp.py                 — ニュース NLP -> ai_scores 書込
      - regime_detector.py          — 市場レジーム判定
    - monitoring/
      - monitoring_db.py            — SQLite 監視 DB 層
      - system_monitor.py           — システム監視
      - trade_monitor.py            — 注文監視
      - risk_monitor.py             — リスク監視（ドローダウン等）
      - kill_switch.py              — KillSwitch フラグ制御
      - alert_manager.py            — LINE 通知
      - monitoring_engine.py        — 各 Monitor を束ねるエンジン
      - streamlit_dashboard.py      — Streamlit ダッシュボード
    - execution/
      - execution_engine.py         — ExecutionEngine（起動時に run_session 実行）
      - order_manager.py            — 注文管理
      - order_repository.py         — Orders DB
      - reconciler.py               — 起動時リコンシリエーション
      - broker_factory.py           — ブローカークライアント生成
      - ... (broker_api, order_record など)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - process_priority.py         — プロセス優先度設定ユーティリティ
    - data/                          — 実行時生成される SQLite / DuckDB 等の格納想定（git 管理外）
- pyproject.toml / .gitignore 等（プロジェクトルート）

---

## 運用上の留意点（抜粋）

- 環境分離:
  - paper_trading モードでは PAPER_TRADING_SQLITE_PATH に書き込まれるため、本番データと分離できます。運用時は KABUSYS_ENV を正しく設定してください。

- LLM 呼び出し:
  - OpenAI（gpt-4o-mini）を使用する実装があります。API キー漏洩やコストに注意してください。API 呼び出しはリトライ/フェイルセーフを組み込んでいます。

- 権限:
  - process priority の設定や PID 作成などで OS 権限に依存します。psutil による優先度変更で AccessDenied が出る場合はログを出してスキップします。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は簡易マイグレーション（カラム追加）を行います。より複雑なスキーマ変更は別途管理してください。

- テスト:
  - LLM 呼び出しや外部 API 呼び出し部分はモックしやすい設計（関数切り出し）になっています。ユニットテスト時は該当関数を patch してください。

---

## 開発者向けメモ

- Settings クラスは実行時に .env / .env.local の自動読込を行います（プロジェクトルートを .git または pyproject.toml で検出）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 多くのモジュールは DuckDB 接続を受け取り純粋関数（副作用最小）で結果を返します（リサーチ / ファクター計算等）。
- API 呼び出しのラップ関数（_call_openai_api 等）はテスト時に差し替えて検証が可能です。

---

必要であれば README を実際のプロジェクト構成に合わせて要求される詳細（requirements.txt、サービスユニットファイル、運用手順書、例示的 .env.example など）を追加します。どの情報を優先的に追記しますか？