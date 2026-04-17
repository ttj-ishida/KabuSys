# KabuSys

日本株自動売買システムのサブセット実装（ライブラリ＆実行スクリプト群）

この README はリポジトリ内のコードベース（src/kabusys以下）を対象に、プロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを想定したモジュール群です。主な責務は以下の通りです。

- 注文管理（OrderManager / ExecutionEngine を想定）
- 発注/ブローカ連携の抽象化（BrokerClientFactory 等）
- リコンシリエーション（再起動時の同期）
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ計算）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- AI を用いたニュース NLP（OpenAI を利用したセンチメント算出）
- 研究向けファクター計算（DuckDB を利用）
- 付帯ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針として、可能な限り純粋関数化や DB とロジックの分離、フェイルセーフな処理（API失敗時のフォールバック）を採用しています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager（発注の作成・状態遷移）
  - Reconciler（再起動時の注文・ポジション照合）
  - RiskManager（発注前のリスク判定、設定可能）

- Monitoring
  - SystemMonitor（CPU / メモリ / ディスク / プロセス監視、データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - MonitoringEngine（各モニタの統合、定期実行）
  - AlertManager（LINE Push による通知）
  - Streamlit ダッシュボード（リアルタイム確認）

- Portfolio
  - 銘柄候補選定、等配分・スコア配分、リスク調整（セクターキャップ・レジーム乗数）
  - ポジションサイズ計算（単元株丸め、資金上限適用、スケーリング）

- Research / Data
  - DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー）
  - ファクター探索ユーティリティ（将来リターン、IC、統計要約）

- AI
  - ニュースセンチメント算出（OpenAI Chat API を利用）
  - 市場レジーム判定（ETF MA とマクロ NLP の組合せ）

- ツール
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）

---

## セットアップ手順

以下はローカル環境で動かすための最小手順例です。

1. リポジトリをクローンして作業ディレクトリを移動
   - 例: git clone <repo> ; cd <repo>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - requirements.txt が無ければ次のパッケージをインストールしてください（最低限）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトで別途 requirements.txt を用意している場合は `pip install -r requirements.txt` を実行してください。）

4. 環境変数（.env）を準備
   - プロジェクトルートの `.env` または `.env.local` に設定可能です。自動読み込みが有効（デフォルト）です。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. データディレクトリ
   - デフォルトで `data/` 下に DB ファイルや PID / フラグファイルを作成します。必要なら事前に作成してください。
   - 初回起動時は monitoring 用 DB（SQLite）等はスクリプト内で初期化されます（init_monitoring_db が実行されます）。

---

## 必要な環境変数（主なもの）

- KABUSYS_ENV: 起動環境。`development` / `paper_trading` / `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須: 一部機能）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須: 実ブローカー使用時）
- OPENAI_API_KEY: OpenAI を使う機能で必要（news_nlp / regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を使う場合
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant / partial / never / reject）（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。デフォルト 60）

例（.env）:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
MONITOR_POLL_INTERVAL=60
```

> 注意: Settings モジュールは .env / .env.local を自動読み込みします（OS 環境変数は上書きされません）。テスト等で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要スクリプト）

プロジェクトルートから Python モジュールとして起動することを想定しています。

- 実行エンジン（ExecutionEngine）を起動
  - 用途: 注文実行・一連の実行プロセスを起動します。
  - paper_trading モード: `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用して `data/paper_trading.db` に記録され、本番 DB と分離されます。
  - コマンド:
    - python -m kabusys.run_execution
    - または python src/kabusys/run_execution.py

- 監視ループを起動
  - 用途: SystemMonitor / TradeMonitor / RiskMonitor を定期実行して monitoring DB に記録、アラート判定を行います。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - コマンド:
    - python -m kabusys.run_monitoring
    - または python src/kabusys/run_monitoring.py

- Streamlit ダッシュボード（監視 UI）
  - コマンド:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 `--db` で監視 DB のパスを指定できます（デフォルト: data/monitoring.db）。

- Paper Trading 検証レポート生成
  - 用途: paper_trading DB を集計し稼働率や注文成功率・レイテンシ等を報告
  - コマンド:
    - python -m kabusys.tools.paper_verification_report
    - オプション:
      - --from YYYY-MM-DD
      - --to YYYY-MM-DD
      - --db PATH（PAPER_TRADING_SQLITE_PATH で指定する代替）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。各モジュールは API 呼び出しに失敗しても安全にフォールバックする設計です。
  - 関数呼び出し単位で利用します（例: kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime）。

---

## 実行時の停止 / フラグファイル

- 停止フラグ（監視 / 実行停止）
  - プロジェクトの data ディレクトリに `stop_requested.flag` を置くと、run_monitoring/run_execution のループが検出して優雅に停止します。
  - Kill Switch（監視が危険状態を検出した場合）:
    - `KillSwitch` が必要と判断すると `data/kill.flag` に理由を書き込み、ExecutionEngine に停止シグナルを送ります（ExecutionEngine は起動時にこのフラグがあれば起動を拒否します）。
  - PID ファイル:
    - ExecutionEngine は `data/execution.pid`（デフォルト）に PID を書きます。SystemMonitor はこれを参照してプロセス生存を検査します。

---

## DB とマイグレーションの扱い

- 監視用 SQLite（デフォルト: data/monitoring.db）は init_monitoring_db によって必要なテーブル・インデックスを冪等に作成します（初回起動で自動作成）。
- DuckDB（デフォルト: data/kabusys.duckdb）は研究/ファクター計算用の列指向 DB。
- Paper Trading モードでは監視用とは別の SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用します（本番 DB と完全分離）。

---

## ディレクトリ構成（抜粋）

src/kabusys 以下の主要構成:

- kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理（.env 自動ロード）
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py    — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py                     — ニュース NLP（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py              — 市場レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py                — SQLite 永続化層（monitoring テーブル群、MonitoringDB クラス）
    - system_monitor.py               — システム監視（CPU/MEM/DISK/データ鮮度）
    - trade_monitor.py                — 注文滞留・約定異常監視
    - risk_monitor.py                 — ドローダウン・ポジション上限監視
    - kill_switch.py                  — kill.flag 書き込みロジック
    - alert_manager.py                — LINE 通知
    - monitoring_engine.py            — 各モニタを束ねる
    - streamlit_dashboard.py          — Streamlit ダッシュボード
  - execution/
    - order_manager.py                — OrderManager（発注の外向 API）
    - reconciler.py                   — 再起動時のリコンシリエーション
    - (その他 broker / engine / repository 関連)
  - portfolio/
    - portfolio_builder.py            — 銘柄選定・重み付け
    - position_sizing.py              — 株数決定・スケールダウンロジック
    - risk_adjustment.py              — セクター制限・レジーム乗数
  - research/
    - factor_research.py              — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py          — IC/将来リターン/統計ユーティリティ
  - utils/
    - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (既定のデータ・DB 配置場所。リポジトリには含まれない)

（上記は抜粋。実際のファイル一覧はリポジトリを参照してください）

---

## 運用時の注意点 / 備考

- Paper Trading と Live（本番）は DB を分離する設計です。paper_trading を使用する場合は `KABUSYS_ENV=paper_trading` を設定してください。
- OpenAI 等外部 API 呼び出しにはレート制限やエラーが発生するため、モジュール側でリトライやフォールバックの実装があります。APIキーを安全に管理してください。
- process priority / CPU affinity の設定は psutil を利用します。権限やプラットフォームによって動作しない場合があります（ログに警告が出ます）。
- Settings（kabusys.config）はプロジェクトルートを .git または pyproject.toml で自動検出して `.env` / `.env.local` を読み込みます。CI / テストで自動読込を無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用してください。
- 監視・停止機構はファイルベースのシグナル（data/stop_requested.flag, data/kill.flag）を使用しています。運用環境での権限やファイル配置に注意してください。

---

## よく使うコマンドまとめ

- 開発仮想環境の作成:
  - python -m venv .venv
  - source .venv/bin/activate

- パッケージインストール（最小）:
  - pip install duckdb psutil requests openai streamlit

- Execution 起動:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボード起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコード構成と注目すべき設定、起動手順の要点をまとめたものです。追加で README に入れたい詳細（例えば requirements.txt の完全な一覧、.env.example のファイル、デプロイ例、systemd ユニットや Dockerfile など）があれば、それに合わせて追記を作成します。