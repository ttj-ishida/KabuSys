KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームです。  
シグナル生成・ポートフォリオ構築・注文実行・監視・レポーティングまでを含むモジュール群を備え、ローカル開発（development）・ペーパートレード（paper_trading）・本番（live）に対応します。

主な設計方針
- DuckDB / SQLite を用いた履歴・分析データ管理
- Execution (注文実行) と Monitoring（監視）は分離
- 環境変数 / .env による設定管理（config_setup.py によるウィザードあり）
- AI（OpenAI）を利用したニュースセンチメント・レジーム判定をオプションで提供
- フェイルセーフ設計（API失敗時のフォールバック・冪等書き込み・部分失敗の保護）

機能一覧
--------
- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録
- Monitoring（System / Trade / Risk）ポーリングループ（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用（環境に依らない）
- Kill Switch（リスクトリガーで data/kill.flag を書き込み、Execution を停止）
- Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- ポートフォリオ構築：候補選定 / 重み計算 / ポジションサイズ決定（等金額、スコア加重、リスクベース）
- AI モジュール
  - news_nlp: ニュース記事をまとめて OpenAI でセンチメント評価 → ai_scores テーブルへ書込
  - regime_detector: ETF の MA とマクロニュースの LLM センチメントを合成して日次の市場レジーム判定
- 研究用ユーティリティ（ファクター計算、特徴量探索、IC 計算 等）

必要要件（依存パッケージ）
------------------------
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の内容検証を行う場合。ただし必須ではない）

インストール（例）
-----------------
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   （用途によって openai / pyyaml は任意）

設定（.env）
------------
プロジェクトルートに .env を置くことで環境変数を管理します。自動ロード順序:
OS 環境変数 > .env.local > .env

設定ウィザード
- 実行: python -m kabusys.config_setup
- 対話式に .env を生成／更新します。

主な環境変数（抜粋）
- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の専用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（0/1、本番では 0 推奨）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）

設定検証
--------
- python -m kabusys.validate_config
  - 必須環境変数や config/*.yaml の存在・簡易パースをチェック
  - --strict を付けると警告もエラー扱いで exit(1)

使い方（主要コマンド）
--------------------

1) ExecutionEngine を起動
- python -m kabusys.run_execution
  - KABUSYS_ENV に応じてブローカークライアントを選択（paper_trading なら MockBroker）
  - paper_trading の場合、データは paper_sqlite_path（data/paper_trading.db 等）に記録され、本番 DB と分離
  - 実行中は data/execution.pid が作成される仕組みを使用
  - 停止は data/stop_requested.flag を作成するか、Kill Switch が kill.flag を書き込む（Monitoring 側）

2) Monitoring（ポーリング）を起動
- python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔指定（秒）
  - 監視は常に Settings.sqlite_path（本番）へ接続して監視ログを記録
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag を作成するとループを抜ける

3) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db を指定して別 DB を参照可能（環境変数 PAPER_TRADING_SQLITE_PATH も使用可）

AI（OpenAI）機能の利用
----------------------
- news_nlp.score_news, regime_detector.score_regime は OpenAI API キーが必要です（OPENAI_API_KEY）。
- API 呼び出しは最大バッチサイズやリトライ／バックオフなどを実装しており、失敗時は安全にフォールバック（例: 0.0）します。
- モデルはデフォルトで gpt-4o-mini を想定。API 利用は課金の対象となります。

監視・Kill Switch の動作（要点）
------------------------------
- Monitoring は SystemMonitor / TradeMonitor / RiskMonitor を定期実行してデータを monitoring.db（SQLite）に永続化します。
- RiskMonitor は Drawdown / Position count の閾値をチェックし、必要に応じて risk_logs に記録します。
- KillSwitch はリスクトリガーを検知すると data/kill.flag に理由を書き込み、ExecutionEngine 側がこれを見て安全に停止します。
- run_execution は起動時に data/stop_requested.flag が既にある場合は起動しません（誤起動防止）。
- 注意: 本番環境で KILL_FLAG_CLEAR_ON_START=1 にすると kill.flag が自動的にクリアされるため危険です（本番では 0 推奨）。

DB とマイグレーション
--------------------
- monitoring_db.init_monitoring_db(conn) が必要テーブルを冪等で作成します（system_status, trade_logs, positions, risk_logs, dashboard）。
- init_monitoring_db は既存 DB に対する簡易マイグレーション（列追加）も行います（例: trade_logs.latency_ms, dashboard.peak_value）。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の自動読み込みと Settings
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ
    - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - alert_manager.py       — （アラート送信管理）※実装ファイルあり
    - kill_switch.py         — kill.flag 制御
  - execution/                — Execution 関連（OrderManager 等）
  - portfolio/
    - portfolio_builder.py    — 候補選定 / 重み計算
    - position_sizing.py      — 株数決定 / aggregate cap
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — IC / 将来リターン / 統計サマリー
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading レポート

開発者向け補足
--------------
- process_priority.set_process_priority を呼んでプロセス優先度を上げる処理があります（psutil を使用）。権限や OS により設定に失敗する場合があり、その場合はログに警告が出ます。
- DuckDB 接続は各モジュールで渡して使う設計（SQL + Python で計算）。
- モジュールは可能な限り副作用を避け、関数は純粋関数であることが多い（特に portfolio/ 内）。

よくある操作例
--------------
- 初期設定ウィザード実行:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config

- Execution 起動（ペーパートレードを使うには .env の KABUSYS_ENV=paper_trading を設定）:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

注意事項 / ベストプラクティス
------------------------------
- .env は漏洩してはならないため絶対にリポジトリにコミットしないこと。
- 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨。自動クリアは危険。
- OpenAI を利用する機能は API キーと料金が必要。レート制限に配慮した設計になっていますが運用時は注意してください。
- Monitoring は本番の監視 DB を参照します。テスト・開発時は PAPER_TRADING_SQLITE_PATH を利用して DB を分離してください。

ライセンス
----------
（ここにプロジェクトのライセンスを記載してください）

最後に
------
この README はソースコードの主要モジュールに基づく概要と運用手引きです。詳細な実装や追加オプションは各モジュールの docstring / コメントを参照してください。必要なら README に追記・補足していきます。