# KabuSys

日本株向けの自動売買システム用ライブラリ / 実行スクリプト群。  
この README はリポジトリ内の主要モジュール（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI ニュース処理、ユーティリティ等）についての概要、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の機能を持つ日本株自動売買システムのコンポーネント群です。

- 注文発行・管理のための ExecutionEngine（実行エンジン）
- システム稼働状況・注文監視・リスク監視・Kill Switch（監視コンポーネント）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数）
- リサーチ用ファクター計算（モメンタム / ボラティリティ / バリュー 等）と特徴量解析
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント算出）およびレジーム判定
- ペーパートレード向けの専用 DB 分離、検証レポート生成ツール
- 環境設定ウィザード・設定検証 CLI、プロセス優先度設定ユーティリティ など

設計上のポイント：
- 本番 DB とペーパートレード DB は分離（KABUSYS_ENV により挙動が切り替わる）
- 時刻・データ参照においてルックアヘッドバイアスを防ぐ実装方針
- OpenAI 呼び出しは失敗時にフェイルセーフ（継続）する設計

---

## 主な機能一覧

- Execution
  - Broker クライアント（実口座 / モック）を切替可能（KABUSYS_ENV）
  - OrderRepository / OrderManager / RiskManager / Reconciler を備えた ExecutionEngine
- Monitoring
  - SystemMonitor（プロセス稼働、CPU/メモリ/ディスク、データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（フラグファイルで ExecutionEngine を停止）
  - MonitoringEngine（上記をまとめてポーリング）
- Portfolio
  - 候補選定、等金額／スコア加重、リスクベースの株数算出、単元株丸め
  - セクターキャップ、レジームに応じた乗数適用
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC 計算、統計サマリー
- AI（OpenAI）
  - news_nlp.score_news：ニュース記事から銘柄ごとのセンチメントを算出し ai_scores に書込
  - regime_detector.score_regime：ETF MA とマクロニュースで市場レジーム判定
- Tools
  - config_setup：.env を対話式に生成・更新
  - validate_config：環境変数・config/*.yaml の検証 CLI
  - paper_verification_report：ペーパートレードの検証レポート生成

---

## 前提（Prerequisites）

- Python 3.10+
- 必要な Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の検証を行う場合）
- システムに SQLite が利用可能（Python 標準ライブラリで OK）
- （OpenAI 機能を使う場合）OPENAI_API_KEY を取得して設定

依存はプロジェクトの requirements.txt / pyproject.toml にも記載されている想定です。無ければ下記をインストールしてください（例）:

pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン / 展開

2. Python 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .\.venv\Scripts\activate    (Windows)

3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - あるいは個別に: pip install duckdb psutil openai PyYAML

4. .env 作成（推奨: 対話ウィザードを使用）
   - python -m kabusys.config_setup
   - ウィザードの入力に従って .env を生成します。
   - 重要な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）

5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. data ディレクトリなど必要に応じて作成（自動作成される場合もありますが手動で準備しておくと良いです）
   - mkdir -p data

---

## 使い方（主要スクリプト・API）

基本的にモジュールは Python のパッケージとして利用できます。実行スクリプトはモジュール実行（-m）で起動可能です。

1. 実行エンジン（Execution）
   - 起動（デーモン的に使用する想定）:
     - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録
     - 本番 / live では本番 sqlite_path を使用
   - 停止:
     - 停止は data/stop_requested.flag の作成や kill.flag などの仕組みで制御します（KillSwitch を使用）

2. 監視ループ（Monitoring）
   - 起動:
     - python -m kabusys.run_monitoring
   - オプション:
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60 秒）
   - 注意:
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視データを記録します

3. 環境設定 / 検証
   - .env 作成: python -m kabusys.config_setup
   - 設定検証: python -m kabusys.validate_config [--strict]

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db

5. AI 関連（プログラムからの呼び出し）
   - AI スコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key=None)  # api_key を渡すか環境変数 OPENAI_API_KEY を設定
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key=None)

6. ライブラリ API（ポートフォリオ・リサーチ等）
   - ポートフォリオ:
     - from kabusys.portfolio import (
         select_candidates, calc_equal_weights, calc_score_weights,
         calc_position_sizes, apply_sector_cap, calc_regime_multiplier
       )
   - リサーチ:
     - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

---

## 重要な環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI を利用する場合に必要
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の fill モード（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（"1" で有効）

---

## 停止・制御（フラグファイル）

- data/stop_requested.flag — run_monitoring / run_execution が監視する停止フラグ（存在を検出して終了）
- data/kill.flag — KillSwitch が書き込むことで ExecutionEngine 停止を要求
- data/execution.pid — Execution が自分の PID を書き込むファイル（SystemMonitor が stale PID を検出して削除する）

注意:
- KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリアします。live 環境での自動クリアは危険となるためデフォルトは 0（無効）を推奨します。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要なパッケージ構成:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - execution/                — 実行エンジン関連（OrderManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （アラート関連）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — レジーム判定（OpenAI）
  - data/                     — （データファイル、DB を配置する想定）
  - tools/
    - paper_verification_report.py

（上記は抜粋です。細かな実装ファイルは各サブパッケージを参照してください。）

---

## トラブルシューティング / 注意点

- OpenAI 関連
  - OPENAI_API_KEY が未設定だと score_news / score_regime はエラーになります。api_key 引数で渡すこともできます。
  - API エラーはリトライロジックを備えていますが、制限や課金に注意してください。
- validate_config
  - PyYAML が未インストールだと config/*.yaml のパース検証はスキップされ、警告が出ます。
- DB
  - monitoring は常に SQLITE_PATH（本番パス）を使用して監視テーブルを初期化します（run_monitoring）。
  - run_execution は KABUSYS_ENV=paper_trading の場合に PAPER_TRADING_SQLITE_PATH を使用して完全分離を保ちます。
- プロセス優先度
  - set_process_priority は権限が不足すると警告が出てスキップされます（psutil の AccessDenied 等）。
- .env は決して Git にコミットしないでください（config_setup のヘッダにも注意書きがあります）。

---

## 開発者向けメモ

- テストしやすいように OpenAI 呼び出しなど一部関数は差し替え（patch）しやすい実装になっています（例: _call_openai_api の置換）。
- DuckDB 接続は関数に渡す形で設計されており、SQL + Python の混在で大規模データ処理を行います。
- 各モジュールは「DBや外部 APIに依存しない純粋関数」と「接続や永続化を担う層」に分離しており、単体テストが書きやすい構造です。

---

README に記載した以上の詳細や API の使い方は各モジュールの docstring / ソースコメントを参照してください。必要であれば、README に記載するコマンドの具体例や .env のテンプレート、起動フロー図などを追加できます。どの情報をより詳しく追加したいか教えてください。