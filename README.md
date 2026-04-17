# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ + 実行スクリプト群）。

概要、主要機能、セットアップ方法、使い方（起動コマンド例）およびプロジェクトのディレクトリ構成をまとめた README です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わる以下の機能を含む Python パッケージです。

- シグナル生成 / ポートフォリオ構築 / ポジションサイズ計算（pure function）
- 発注エンジン（ExecutionEngine） — 実際のブローカー呼び出しまたはペーパートレードの切替
- 監視（Monitoring） — システム状態、注文滞留、リスク（ドローダウン・ポジション上限）を定期チェック
- AI 補助機能 — ニュースの NLP スコアリング、マクロセンチメントを元にした市場レジーム判定（OpenAI）
- レポート / ツール — ペーパートレードの検証レポート生成
- ユーティリティ — 設定読み込み、.env ウィザード、設定検証、プロセス優先度設定 など

設計方針の一部：
- 研究・分析用関数は DB に依存せず pure function にする（テスト容易性）。
- ルックアヘッドバイアス回避のため、date.today()/datetime.now() の扱いに注意した実装。
- 本番とペーパートレードのデータは分離（paper_trading の場合は専用 SQLite を使用）。

---

## 機能一覧

- 環境設定・管理
  - .env の対話式作成/更新（kabusys.config_setup）
  - 起動前の設定検証（kabusys.validate_config）

- 実行系
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による paper/live 切替）
    - paper_trading なら MockBroker を使用し、data/paper_trading.db に記録（本番 DB と完全分離）
    - 停止フラグ（data/stop_requested.flag）で安全に停止
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL を環境変数で指定可）

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視・アラート
  - KillSwitch: 条件に応じた kill.flag 発行（ExecutionEngine 停止トリガ）
  - MonitoringDB: SQLite を用いた永続化（system_status, trade_logs, positions, risk_logs, dashboard）

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等金額 / スコア加重配分（calc_equal_weights, calc_score_weights）
  - セクター上限適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes）

- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ等

- AI（OpenAI）
  - news_nlp.score_news: raw_news を LLM でセンチメント付与、ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）MA とマクロニュース LLM を組み合わせて市場レジーム判定

- ツール
  - tools.paper_verification_report: ペーパートレード DB を解析して検証レポート生成

---

## セットアップ手順

1. Python 環境を準備（推奨: Python 3.10+）
   - 仮想環境を作成して有効化する例：
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - 主な依存パッケージ（環境によって一部は任意）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (config YAML 検証を行う場合)
   - 例:
     - pip install duckdb psutil openai PyYAML

   > 注意: プロジェクトには requirements.txt が同梱されていないため、プロジェクト利用に必要なパッケージは上記を参考に適宜インストールしてください。

3. プロジェクトルートに .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env を手動で用意（.env.example が参照用に存在する想定）

4. 設定検証（必須変数が揃っているか確認）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1) になります

5. data ディレクトリ作成（スクリプトが自動作成する場合もありますが事前準備推奨）
   - mkdir -p data

---

## 環境変数（主なもの）

（Settings クラス / validate_config を参照した主要な環境変数）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード: instant | partial | never | reject（デフォルト: instant）
- OPENAI_API_KEY — OpenAI を使う場合に必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…、デフォルト INFO）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1、デフォルト 0）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
- PID_FILE_PATH — ExecutionEngine の pid ファイルパス（デフォルト data/execution.pid）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

自動 .env 読み込み:
- プロジェクトルートにある `.env` / `.env.local` は自動読み込みされる（OS 環境変数が優先）。
- 自動読み込みを無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（起動コマンド例）

- .env ウィザード（対話式）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動:
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します。
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
    - プロセス優先度を high に設定します。
    - 実行中に停止させたい場合は kill.flag（Settings.kill_flag_path）を作成するか stop_requested.flag を作成してください。

- Monitoring 起動（定期ポーリング）:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL で秒間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - run_monitoring は監視 DB（sqlite_path）に接続します。monitoring は環境に関わらず本番 sqlite_path を使用します。

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- ライブラリとしての利用（例）
  - ポートフォリオ関数を呼び出す:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

---

## 停止・Kill スイッチ

- ExecutionEngine の停止方法:
  - data/stop_requested.flag（run_execution, run_monitoring が参照）を作成するとループを終了します
  - KillSwitch は条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込み、ExecutionEngine 起動中に検知すると安全に停止します
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）

---

## よくあるトラブルと注意点

- OpenAI 関連
  - news_nlp.score_news / regime_detector.score_regime は OPENAI_API_KEY が必要。未設定だと例外になります。
  - API 呼び出しはリトライやフェイルセーフ（失敗時はスコア 0 など）を組み込んでいますが、API 利用回数やコストに注意してください。

- DuckDB / SQLite
  - DuckDB は prices_daily / raw_financials 等のテーブルを参照します。リサーチ関数は DuckDB 接続を受け取る形になっています。
  - monitoring / order 系は SQLite を永続化に使用します。paper_trading 環境は専用 SQLite を使用して本番 DB と分離します。

- 依存パッケージ
  - PyYAML がインストールされていない場合、validate_config の YAML 検証はスキップされます（警告出力）。
  - psutil によるプロセス優先度設定や CPU affinity は権限依存で失敗することがあります（警告ログ）。

- 自動 .env ロード
  - プロジェクトルートは .git または pyproject.toml を基準に自動判定します。パッケージ配布後や別レイアウトでは自動読み込みがスキップされる場合があります。

---

## ディレクトリ構成（抜粋）

（主要なモジュールとスクリプトを示します。実際のリポジトリには追加ファイルがあります）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 定義、自動 .env ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）によるスコア付与
    - regime_detector.py     — マーケットレジーム判定（MA + マクロニュース）
    - __init__.py

  - monitoring/
    - monitoring_db.py       — SQLite スキーマ・永続化層
    - system_monitor.py      — CPU/メモリ/データ鮮度/プロセス監視
    - trade_monitor.py       — 注文滞留・約定異常チェック
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （未掲示: アラート送信ロジック）

  - execution/
    - (order_repository, execution_engine, etc.)  — 発注ロジック一式（概要コード参照）

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - monitoring/
    - (上記参照)

  - tools/
    - paper_verification_report.py
    - __init__.py

  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

---

## 開発者向けメモ

- DB スキーマ変更は monitoring_db.init_monitoring_db で冪等に実行されます。必要に応じてマイグレーションロジックを追加してください。
- AI 呼び出しのテストはモジュール内の _call_openai_api をモックする設計になっています（unittest.mock.patch 等で差し替え）。
- 研究系関数は DuckDB 接続を受け取り SQL を実行します。テスト用に DuckDB にテストデータをロードして利用してください。
- ロギングは標準 logging を使用。LOG_LEVEL 環境変数で調整できます。

---

この README はコードベースの主要部分をカバーしていますが、各モジュールには詳細な docstring が含まれています。実装や拡張を行う際は該当ファイル内のコメント・注釈を参照してください。問題や追加のドキュメントが必要であれば教えてください。