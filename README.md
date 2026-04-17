# KabuSys

日本株自動売買システムの一部を実装したリポジトリ。戦略のポートフォリオ構築、ポジションサイジング、監視・アラート、実行エンジン起動補助、Paper Trading 検証ツール、ニュース NLP / レジーム判定などのコンポーネントを含みます。

以下は本リポジトリに含まれる主要コンポーネントと利用方法をまとめた README です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境変数（設定）
  - 監視ループ起動 (Monitoring)
  - 実行エンジン起動 (Execution)
  - Paper Trading 検証レポート
  - 監視ダッシュボード (Streamlit)
  - AI 関連（ニュース NLP / レジーム判定）
- ディレクトリ構成
- 補足・運用メモ

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコンポーネント群です。本リポジトリでは主に以下を提供します。

- ポートフォリオ構築（候補選定・重み計算・リスク調整・ポジションサイジング）
- 実行エンジンを補助する OrderManager / Reconciler（ブローカー同期）
- 監視機能（システム稼働・データ鮮度・注文滞留・リスク監視）とアラート送信（LINE）
- Paper Trading 用の分離された DB と検証レポート生成スクリプト
- ニュースの LLM ベースセンチメント評価と市場レジーム判定（OpenAI）
- Streamlit による監視ダッシュボード

設計方針として、DB（SQLite / DuckDB）や外部 API へのアクセスを分離し、テストしやすい純粋関数群を多く含みます。

---

## 機能一覧

- portfolio
  - 銘柄候補選定 (select_candidates)
  - 等分配・スコア加重の重み計算 (calc_equal_weights / calc_score_weights)
  - セクターキャップ適用 (apply_sector_cap)
  - レジームに応じた乗数 (calc_regime_multiplier)
  - ポジションサイズ計算 (calc_position_sizes)
- research
  - ファクター計算: momentum / volatility / value
  - 将来リターン計算、IC 計算、統計サマリ
- execution
  - OrderManager（注文作成・同期）
  - Reconciler（再起動時の突合せ）
  - ExecutionEngine 起動スクリプト補助
- monitoring
  - SystemMonitor（CPU/メモリ/ディスク、プロセス・データ鮮度チェック）
  - TradeMonitor（滞留注文、約定価格異常検出）
  - RiskMonitor（ドローダウン、ポジション上限監視）
  - KillSwitch（条件により ExecutionEngine 停止フラグ書き込み）
  - AlertManager（LINE にプッシュ通知）
  - MonitoringEngine（各 Monitor を束ねてポーリング）
  - Streamlit ダッシュボード
- tools
  - paper_verification_report: Paper Trading の DB を集計し検証レポートを出力
- ai
  - news_nlp.score_news: raw_news を LLM で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF MA と LLM を合成して市場レジーム判定

---

## セットアップ手順

※ 実行に必要なパッケージはプロジェクトによって異なります。ここでは本コードベースで明示的に利用されている主な外部依存を示します。

推奨: 仮想環境を作成してからインストールしてください。

例（venv + pip）:
1. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージ（例）
   - pip install duckdb psutil requests openai streamlit
   - 実運用ではその他の依存（duckdb-driver などや、requirements.txt を用意してください）

3. データディレクトリ作成
   - mkdir -p data

4. 環境変数
   - ルートに .env または .env.local を置くと自動で読み込まれます（自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数（実行モードにより異なります）は下記「環境変数」の節を参照してください。

---

## 使い方

### 環境変数（Settings）

Settings クラスは環境変数から設定を読み込みます。主要なキー（例）:

必須（実行する機能に応じて必須）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

OpenAI / LINE / DB 関連
- OPENAI_API_KEY — OpenAI 呼び出しに必要（ai.news_nlp, ai.regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN — AlertManager 用（任意）
- LINE_USER_ID — AlertManager 用（任意）

環境設定
- KABUSYS_ENV — 起動環境。`development` / `paper_trading` / `live`（デフォルト: development）
  - `paper_trading` の場合、MockBroker を使用し、paper_trading 専用 SQLite を使います
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）

DB パス（デフォルト）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)

監視 / PID / フラグファイル
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

例の .env（最小）:
JQUANTS_REFRESH_TOKEN=your_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=paper_trading
DUCKDB_PATH=data/kabusys.duckdb

Settings は .env / .env.local を自動で読み込みます（OS 環境が優先）。自動ロードを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

### 監視ループ起動 (Monitoring)

- スクリプト: src/kabusys/run_monitoring.py
- 概要: SystemMonitor を定期実行して監視ログを SQLite に書き込みます。
- ポーリング間隔を環境変数で上書き: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
- 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが終了します（再起動時に削除してください）。

起動例:
python -m kabusys.run_monitoring

環境変数例:
export MONITOR_POLL_INTERVAL=30

注意:
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（monitoring DB は単独で保持されるため）。

### 実行エンジン起動 (Execution)

- スクリプト: src/kabusys/run_execution.py
- 概要: ExecutionEngine を起動するためのラッパー。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB (data/paper_trading.db) に記録します。
- 起動はバックグラウンドスレッドでエンジンを動かし、data/stop_requested.flag による停止検知を行います。
- PID ファイル: data/execution.pid を使用（Settings.pid_file_path）

起動例:
python -m kabusys.run_execution

注意:
- 起動前に data/kill.flag が存在する場合はエンジンを起動しません（kill flag は ExecutionEngine 側停止のための信号）。
- stop フラグで安全にエンジンを停止できます。

### Paper Trading 検証レポート

- スクリプト: src/kabusys/tools/paper_verification_report.py
- 概要: Paper Trading 用 SQLite を解析して稼働率・注文成功率・レイテンシ等を集計し、PASS/FAIL を出力します。

実行例:
python -m kabusys.tools.paper_verification_report
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

デフォルト DB パス: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）

### 監視ダッシュボード (Streamlit)

- スクリプト: src/kabusys/monitoring/streamlit_dashboard.py
- 起動例:
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- データは読み取り専用で DB に接続します。MonitoringEngine を先に起動して監視データを生成してください。

### AI 関連（ニュース NLP / レジーム判定）

- OpenAI API キーが必要: OPENAI_API_KEY
- news_nlp.score_news:
  - raw_news と news_symbols を集約して LLM に渡し銘柄ごとのスコアを ai_scores テーブルへ書き込みます。
  - 大量の銘柄を扱うためバッチ処理（最大 20 銘柄/コール）およびリトライロジックを実装しています。
- regime_detector.score_regime:
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成し市場レジームを判定、market_regime テーブルへ書き込みます。
- いずれも API 呼び出し失敗時は安全側（0.0 やスキップ）で続行する設計です。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下をルートとして抜粋）

- src/kabusys/
  - __init__.py             — パッケージ定義
  - config.py               — 環境変数 / Settings 管理（.env 自動ロード）
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - run_execution.py        — ExecutionEngine 起動ラッパー
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py   — 候補選定・等分/スコア重み
    - position_sizing.py     — 発注株数計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py      — SQLite スキーマ + MonitoringDB クラス
    - system_monitor.py     — CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py      — 滞留注文・約定異常検知
    - risk_monitor.py       — ドローダウン・ポジション数監視
    - kill_switch.py        — kill.flag の書き込み / 管理
    - alert_manager.py      — LINE プッシュ通知
    - monitoring_engine.py  — 各 Monitor を束ねる Polling Engine
    - streamlit_dashboard.py— Streamlit ダッシュボード
  - execution/
    - order_manager.py      — 注文作成・状態遷移 API
    - order_repository.py   — DB への発注レコード永続化（参照あり）
    - reconciler.py         — 起動時の同期 / リコンシリエーション
    - ...                   — broker_factory, execution_engine 等（省略部あり）
  - research/
    - factor_research.py    — momentum / volatility / value 等の計算
    - feature_exploration.py— 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py           — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py    — 市場レジーム判定（MA200 + macro sentiment）
  - data/                   —  実行時データ / DB / flag ファイル（プロジェクトルートに生成）
  - utils/
    - process_priority.py   — プロセス優先度・CPU affinity 設定ユーティリティ

---

## 補足・運用メモ

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成を行い、既存 DB に対する軽微なマイグレーション（カラム追加）も自動実行します。

- 停止 / キル操作
  - data/stop_requested.flag を作成すると run_monitoring / run_execution の起動ループが検知して終了します（安全シャットダウン）。
  - KillSwitch（監視側ロジック）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine 起動を阻止したり外部シグナルとして利用します。

- Paper Trading
  - KABUSYS_ENV=paper_trading を使うと本番 DB とは別の PAPER_TRADING_SQLITE_PATH を用いて完全に分離された検証が可能です。
  - PAPER_FILL_MODE により MockBroker の約定挙動（instant/partial/never/reject）を制御できます。

- ログレベル
  - LOG_LEVEL 環境変数で設定可能（DEBUG / INFO / …）。run_* スクリプトは logging.basicConfig(level=logging.INFO) を行っていますが、Settings.log_level の読み取りなど別実装箇所もあります。

- プロセス優先度
  - run_monitoring / run_execution は起動時に set_process_priority("high") を呼び出してプロセス優先度を上げます。権限が不足する場合は警告を出してスキップします。

- テスト性
  - 多くのモジュールは外部副作用を抑えた純粋関数設計で、DuckDB/SQLite 接続を差し替え可能な実装になっています。OpenAI 呼び出し箇所はテスト時にモック可能です（関数内で呼ぶ _call_openai_api を patch）。

---

以上がこのコードベースの README（概要・セットアップ・使い方・構成）です。具体的な開発・運用フローや追加のデプロイ手順（systemd ユニット、Docker 化、CI 設定など）が必要であれば、用途に応じたガイドを別途作成します。