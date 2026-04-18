# KabuSys

日本株自動売買システムのコードベース（ドキュメント用サマリ）。

この README はリポジトリ内の主要スクリプト・モジュールから生成された情報を元に、セットアップ・起動方法、各コンポーネントの役割、ディレクトリ構成などを日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な目的は以下：

- シグナル生成 → ポートフォリオ構築 → 発注（ExecutionEngine）までのワークフローを支援
- モニタリング（リソース、データ鮮度、注文状況、リスク）と自動停止（Kill Switch）
- Paper Trading（模擬発注）と Live（実環境）の切替
- DuckDB を用いた分析（ファクター計算等）および SQLite による監視/ログ永続化
- OpenAI を利用したニュース NLP・レジーム判定機能（オプション）

プロジェクトはモジュール構成で、ライブラリとしても利用できる設計です。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine（発注エンジン）の起動
  - run_monitoring.py: SystemMonitor のポーリングループ起動
- 環境設定
  - config_setup.py: .env を対話的に生成/更新するウィザード
  - validate_config.py: .env と config/*.yaml の検証 CLI
- モニタリング
  - system_monitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス監視
  - trade_monitor: 発注ログの監視（滞留注文、約定異常など）
  - risk_monitor: ドローダウン・ポジション上限監視とアラート記録
  - monitoring_engine: 各 Monitor を統合してポーリング
  - monitoring_db: SQLite ベースの永続化（schema/migration を含む）
  - kill_switch: 条件により data/kill.flag を書き込むことで ExecutionEngine を停止
- ポートフォリオ構築（純粋関数）
  - 銘柄選定、重み計算（等金額 / スコア加重）
  - セクター制限、レジームに応じた乗数
  - ポジションサイズ計算（単元株丸め、リスクベース配分、aggregate cap）
- リサーチ（DuckDB を使用）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（OpenAI）連携（任意）
  - news_nlp: ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector: MA とマクロニュースの LLM 評価を合成して market_regime を決定
- ツール
  - paper_verification_report: ペーパートレード DB を集計して検証レポート生成

ユーティリティ：
- ロギング設定（Console + 日次ローテートファイル）
- プロセス優先度 / CPU affinity 設定ユーティリティ
- .env の自動ロード（プロジェクトルートを検出して .env / .env.local を読み込む）

---

## 必要条件（依存パッケージの例）

以下はコード内で使用されている主要パッケージの例です。実際の requirements.txt があればそちらを参照してください。

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を有効にする場合）

開発環境では仮想環境を使うことを推奨します。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして作業ディレクトリへ移動

2. 仮想環境の作成（例）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）:
   - pip install duckdb psutil openai PyYAML

   ※ 実プロジェクトでは requirements.txt を用意して `pip install -r requirements.txt` を推奨。

4. 初期環境ファイル (.env) を作成:
   - python -m kabusys.config_setup
     ウィザードに沿って必要な環境変数を入力します（J-Quants, kabuAPI パスワード等）。

5. 設定の検証:
   - python -m kabusys.validate_config
     必須環境変数や config/*.yaml の有無をチェックします。
     --strict を付けると警告も失敗扱いになります。

6. データディレクトリの作成（必要に応じて）:
   - data/（デフォルト DB 等がここに作成されます）
   - logs/（ログ出力先）

---

## 環境変数（主要なもの）

多くの設定は環境変数（または .env）で指定します。主なキーとデフォルト:

- JQUANTS_REFRESH_TOKEN: （必須）
- KABU_API_PASSWORD: （必須）
- KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading の場合、MockBroker を使用し paper_trading 用 DB に書き込み
- LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: 監視 DB（デフォルト "data/monitoring.db"）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト "data/paper_trading.db"）
- PAPER_FILL_MODE: paper_trading の約定挙動（"instant"|"partial"|"never"|"reject"; デフォルト "instant"）
- OPENAI_API_KEY: OpenAI を利用する場合に必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START: "1" にすると起動時に data/kill.flag を自動クリア（本番では 0 推奨）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" で .env の自動ロードを無効化

注意: プロジェクトは実行時にプロジェクトルートを探索して .env / .env.local を自動読み込みします（無効化可）。

---

## 起動・使い方（代表的コマンド）

- 環境変数を読み込んだ上で Monitoring を起動（ポーリング）:
  - KABUSYS_ENV=development python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を設定するとポーリング間隔を上書き可能（秒）

- Execution（発注エンジン）を起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合は MockBrokerClient を使用し paper_trading DB（分離）へ記録
  - 実行中は data/execution.pid が作成され、data/stop_requested.flag により停止要求を検出します

- .env の対話式セットアップ:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（ツール）:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- AI 関連（ライブラリ利用、例）:
  - DuckDB 接続を用意してニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

- ライブラリ関数の利用例（リサーチ）:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - calc_momentum(duckdb_conn, target_date)

ログ出力:
- デフォルトで console (stdout) と logs/<app_name>.log（日次ローテーション）が出力されます。

停止・Kill Switch:
- KillSwitch は条件が満たされたときに data/kill.flag を作成します。ExecutionEngine はこのファイルを検出して安全に停止します。
- 管理者が手動で停止したい場合は stop_requested.flag（run スクリプトが使用）や kill.flag を作成/削除します。

---

## ディレクトリ構成（主要ファイル・概要）

（リポジトリのルートを src/kabusys とした場合の主要構造）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定読み込み・Settings クラス
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py        — ルートロガーの設定（console + ファイル）
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ / 永続化 API
    - system_monitor.py       — システム / データ鮮度監視
    - trade_monitor.py        — (注文監視ロジック)
    - risk_monitor.py         — ドローダウン / ポジション制限監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - monitoring_engine.py    — 各 monitor を束ねるループ
    - alert_manager.py        — (アラート送信ロジック: LINE など)
  - execution/
    - execution_engine.py     — 発注エンジン（Engine）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・aggregate cap
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — momentum/volatility/value 等の計算
    - feature_exploration.py  — forward returns / IC / summary
  - ai/
    - news_nlp.py             — ニュースを LLM でスコアリングして ai_scores に書き込み
    - regime_detector.py      — MA + マクロニュース LL 評価によるレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール

その他:
- data/                      — DB・PID・フラグ等（実行時に使用）
  - monitoring.db (default)
  - paper_trading.db (paper 環境)
  - kill.flag, stop_requested.flag, execution.pid
- logs/                      — ログファイル出力先（デフォルト）

---

## 開発メモ・注意事項

- .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup にもその旨の注意が書かれています）。
- Paper Trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH または Settings.paper_sqlite_path を使用）。
- AI 機能 (news_nlp, regime_detector) は OpenAI API キーが必要です。API 呼び出しは失敗時にフォールバックする設計ですが、キー未設定では例外になる箇所があります（明示的にチェックしています）。
- ロギングは起動時に setup_logging を呼び出して統一的に行ってください。logs ディレクトリが作れない場合はファイルロギングが無効化されコンソールのみになります。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップします（警告出力）。
- run_monitoring のポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可。負の値や 0 は無効としてデフォルト（60秒）にフォールバックします。
- run_execution/run_monitoring は stop_requested.flag の存在を検出すると安全に終了します。kill.flag は ExecutionEngine 停止のために KillSwitch が書き込みます（clear も可能）。

---

必要があれば、この README をベースに以下の追加内容も作成できます：
- requirements.txt の推奨リスト
- 実行例（環境ごとの .env のテンプレート）
- 各モジュールの API リファレンス抜粋（関数・クラスの docstring まとめ）
- デプロイ/運用手順（systemd / Docker / Supervisor 用の例）

ご希望があればどれを追加するか指示してください。