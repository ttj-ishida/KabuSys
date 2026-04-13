# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ向け README。  
この README はコードベースに基づき、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株自動売買のための統合フレームワークです。  
主な目的は以下：

- シグナル → 注文 → 注文管理 → リコンシリエーションまでの発注フロー管理
- モニタリング（システム状態、注文滞留、約定異常、リスク閾値監視）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制約）
- 研究用ファクター計算（DuckDB を利用したファクター算出）
- AI を利用したニュースセンチメント分析 / 市場レジーム判定（OpenAI）
- Paper Trading（モックブローカー）用の分離された記録・検証ツール
- Streamlit ベースの監視ダッシュボードと検証レポート生成ツール

設計方針として、ルックアヘッドバイアスの排除、フェイルセーフ（API失敗時のフォールバック）、DBの冪等初期化、テストしやすい純粋関数分離などが取られています。

---

## 機能一覧

- 実行系（ExecutionEngine）
  - ブローカー抽象化（本番／モック切替）
  - オーダー状態管理（OrderState マシン）
  - リスク管理（ポジション上限・利用率等）
  - 再起動時のリコンシリエーション（Reconciler）

- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/Disk、プロセス PID、価格データ鮮度を監視
  - TradeMonitor：滞留注文・約定価格異常を検出
  - RiskMonitor：ドローダウン警報・ポジション数上限監視
  - KillSwitch：深刻な問題発生時に flag ファイルを書き込んで ExecutionEngine を停止させる
  - AlertManager：LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only 接続で監視情報を可視化）

- ポートフォリオ構築（portfolio モジュール）
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数

- 研究（research モジュール）
  - モメンタム、ボラティリティ、バリューファクター計算
  - 将来リターン、IC（スピアマン）、統計サマリなど

- AI（ai モジュール）
  - ニュースのセンチメントスコアリング（OpenAI）
  - マクロセンチメント + 指標から市場レジームを判定し DuckDB に書込む

- ツール
  - paper_verification_report: Paper Trading 用の検証レポート生成（期間指定可）
  - streamlit_dashboard.py: Streamlit 監視ダッシュボード起動用スクリプト

- 設定管理
  - Settings クラス（環境変数・.env ファイルの自動ロード機構を提供）

---

## セットアップ手順

前提：
- Python 3.10+（typing/構文から推奨）
- DuckDB、SQLite が使用されます（ローカルファイルベース）

1. リポジトリをクローン／チェックアウト：

   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）：

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（requirements.txt がある想定）。主要な依存例：

   ```
   pip install duckdb psutil requests openai streamlit
   ```

   - duckdb: リサーチ用 DB
   - psutil: プロセス優先度 / CPU affinity / システム指標
   - requests: LINE API 通信
   - openai: LLM 呼び出し
   - streamlit: 監視ダッシュボード

4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を用意すると自動ロードされます（既存の OS 環境より低優先度 / .env.local は上書き）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な環境変数（代表例）：
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: monitoring DB（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading の約定動作（instant|partial|never|reject、デフォルト: instant）
   - PID_FILE_PATH / KILL_FLAG_PATH: 実行プロセス管理用ファイルパス
   - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
   - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

5. データディレクトリ作成（必要に応じて）：

   ```
   mkdir -p data
   ```

---

## 使い方

以下は代表的な起動方法とツールの使い方です。

- 監視ループの起動（SystemMonitor の単体スクリプト）：

  ```
  python -m kabusys.run_monitoring
  ```

  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を指定可（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番用の `SQLITE_PATH` を使用して監視 DB を書き込みます。

- 実行エンジンの起動（ExecutionEngine）：

  ```
  python -m kabusys.run_execution
  ```

  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し、Paper Trading 用 DB（`PAPER_TRADING_SQLITE_PATH`）へ記録します。本番 DB と完全に分離されます。
  - 実行開始時にプロセス優先度を "high" に設定する処理が行われます（psutil による）。権限不足で設定できない場合は警告になります。

- Paper Trading 検証レポート生成：

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

  または DB を明示する場合：

  ```
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

  - レポートは稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを出力し、基準値と比較して PASS/FAIL を表示します。

- Streamlit ダッシュボード起動（監視 DB を read-only で開く）：

  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

  - ダッシュボードは監視情報（ダッシュボードサマリ、ポジション、最近の注文、最新のシステム状態、リスクログ）を表示します。
  - DB が存在しなければエラー表示されます（MonitoringEngine を先に起動してください）。

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キーを `OPENAI_API_KEY` に設定してから、該当モジュールの関数を呼び出してください（score_news / score_regime）。
  - これらは DuckDB 内の `raw_news` / `news_symbols` / `prices_daily` 等のテーブルを参照します。

注意点：
- `config.Settings` クラスは `.env` の自動ロードを行います。`.env.example` を参考に必要な環境変数を設定してください。
- Paper Trading と本番 DB は分離されています。Paper Trading の操作が本番データに影響を与えることはありません。

---

## ディレクトリ構成

以下は主要なファイル / パッケージ構成（src/kabusys 以下を中心に抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env 自動読み込み / Settings
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（OpenAI）と ai_scores 更新
    - regime_detector.py         — マクロ + ETF MA200 による市場レジーム判定

  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite 監視 DB 初期化 / 永続層
    - system_monitor.py          — CPU/メモリ/Disk / データ鮮度 / PID チェック
    - trade_monitor.py           — 滞留注文 / 約定異常検出
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — kill.flag の書き込み / 管理
    - alert_manager.py           — LINE 通知（クールダウン管理）
    - monitoring_engine.py       — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py     — Streamlit ダッシュボード

  - execution/
    - order_manager.py           — オーダー作成 / 送信 / 同期（OrderManager）
    - reconciler.py              — 再起動時の注文・ポジション照合
    - (その他 broker / engine / order_repository 等の実装ファイル)

  - portfolio/
    - portfolio_builder.py       — 候補選定 / 重み計算
    - position_sizing.py         — 株数決定 / 単元丸め / aggregate cap
    - risk_adjustment.py         — セクター上限 / レジーム乗数
    - __init__.py

  - research/
    - factor_research.py         — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py     — 将来リターン / IC / 統計サマリ
    - __init__.py

  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

  - utils/
    - __init__.py
    - process_priority.py        — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/                         — デフォルト DB / PID / flag ファイル置き場（アプリ起動時に使用）
  - kabusys.duckdb (default DUCKDB_PATH)
  - monitoring.db (default SQLITE_PATH)
  - paper_trading.db (default PAPER_TRADING_SQLITE_PATH)
  - execution.pid (default PID_FILE_PATH)
  - kill.flag (default KILL_FLAG_PATH)

---

## 追加メモ・運用上の注意

- DB マイグレーション： monitoring_db.init_monitoring_db は冪等で実行され、既存 DB に不足カラムがあれば加える簡易マイグレーション処理が含まれます（例: `peak_value`、`latency_ms`）。
- プロセス優先度： 起動スクリプトはまず `set_process_priority("high")` を呼びます。権限が無い場合は警告のみで継続します。
- Fail-safe： OpenAI 等外部 API 呼び出しはリトライやフォールバック（ゼロスコア等）を行う設計で、API 失敗でプロセスが止まらないよう配慮されています。
- ログレベル： `LOG_LEVEL` 環境変数で調整できます（INFO デフォルト）。
- Paper Trading： 本番 DB と混ざらないよう `KABUSYS_ENV=paper_trading` の時に `PAPER_TRADING_SQLITE_PATH` を使う設計です。

---

この README はコードベースの現状に基づいて作成しています。実際の運用時はリポジトリの README / docs / .env.example を参照し、環境ごとの設定・シークレット管理に十分注意してください。必要があればデプロイ手順（systemd ユニット / Dockerfile / コンテナ化）や CI の説明も追加できます。