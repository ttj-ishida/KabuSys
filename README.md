# KabuSys

日本株自動売買システムの参照実装ライブラリ / 実行スクリプト群です。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・レポート・AI 支援モジュールなどを含んだ統合的なシステムを想定しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 市場データ（DuckDB）を用いたファクター算出・リサーチ機能
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ決定）
- 発注実行エンジン（本番 / ペーパートレード分離）
- 監視（システム稼働・注文状況・リスク監視）と Kill Switch
- AI（OpenAI）を用いたニュースセンチメント解析・レジーム判定
- ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度）

設計上の特徴：

- DuckDB / SQLite をデータ永続化に使用（分析用に DuckDB、監視/注文は SQLite）
- Paper Trading は本番 DB と完全に分離（専用 SQLite）
- OpenAI を使った NLP 機能は API キーが必須（失敗時はフォールバックして安全に続行する設計）
- .env による環境設定をサポート（自動読み込み機能あり）

---

## 主な機能一覧

- 実行（Execution）
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により MockBroker を利用可）
  - ペーパートレード時は `data/paper_trading.db` にデータを記録

- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
  - MonitoringDB（SQLite）へ system_status / trade_logs / positions / risk_logs / dashboard を永続化
  - Kill Switch（条件により data/kill.flag を書き込み、 ExecutionEngine を停止）

- ポートフォリオ構築
  - 候補選定、等配分・スコア加重配分、ポジションサイズ計算、セクター上限・レジーム乗数等

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ等

- AI 機能
  - news_nlp: ニュース記事をまとめて OpenAI に投げ、銘柄ごとのセンチメント（ai_scores）を生成
  - regime_detector: ETF の MA 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定

- ユーティリティ
  - config_setup.py: .env 対話式ウィザード（初期設定）
  - validate_config.py: .env や config/*.yaml の簡易検証 CLI
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成

---

## セットアップ手順（ローカル）

前提: Python 3.9+ を想定（duckdb, psutil, openai, などを利用）。実際の requirements.txt がある場合はそれを利用してください。

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt が無い場合は最低限以下をインストールしてください:
     - pip install duckdb psutil openai

4. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI を使う機能を利用する場合に必須
   - デフォルトの保存先: プロジェクトルートの `.env`

5. DB/ディレクトリの準備
   - デフォルトの DuckDB/SQLite パス（.env 未設定時）:
     - data/kabusys.duckdb
     - data/monitoring.db
   - 必要に応じてデータ格納ディレクトリを作成（多くのスクリプトが自動作成します）

6. ログディレクトリ
   - デフォルト: logs/
   - ログ設定は kabusys.utils.logging_setup.setup_logging で統一されます

注意:
- Paper Trading の場合は KABUSYS_ENV=paper_trading を設定すると、execution はペーパートレード用 DB を使い、MockBrokerClient を利用します。

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境
  - development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants）
- KABU_API_PASSWORD: 必須（kabuステーション）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: monitoring 用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視関連設定

---

## 使い方（コマンド例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（例: export MONITOR_POLL_INTERVAL=30）

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB に記録されます。
  - 起動時に data/stop_requested.flag が存在するとエンジンは起動しません。
  - 実行中は data/execution.pid に PID が書かれます（設定により変更可）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY が必要（引数で渡すことも可）

ログ出力:
- 既定では stdout（コンソール）と logs/<app_name>.log（日次ローテーション）へ出力されます。

停止 / Kill Switch:
- KillSwitch はリスク条件（ドローダウン、ポジション上限など）で `data/kill.flag` を作成します。
- ExecutionEngine は起動時に kill.flag を確認し、存在すれば起動しません。Kill flag は手動で削除するか設定により自動クリア可能。

---

## よくある操作例

- モニタとエンジンを同一マシンで起動する（開発）
  - .env を作成（config_setup）
  - python -m kabusys.run_execution をバックグラウンドで起動
  - python -m kabusys.run_monitoring を別プロセスで起動

- ペーパートレードで安全に試す
  - KABUSYS_ENV=paper_trading を .env に設定または環境変数で指定
  - run_execution は data/paper_trading.db を使う（本番 DB と分離）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主なファイル/モジュール（抜粋）です。

- kabusys/
  - __init__.py
  - config.py
  - config_setup.py          — .env 対話式作成ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュースを OpenAI でスコアリング
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ・アクセス層
    - system_monitor.py      — システム稼働・データ鮮度監視
    - trade_monitor.py       — （注文監視ロジック）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — Kill Switch 実装（flag 書き込み）
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （通知送信ロジック: LINE など）
  - execution/
    - execution_engine.py    — 発注エンジン本体（EngineConfig, run_session など）
    - broker_factory.py      — Broker クライアント生成（Mock / 実ブローカ）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定、重み計算
    - position_sizing.py     — 株数計算、スケールダウンロジック
    - risk_adjustment.py     — セクター制限、レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - utils/
    - logging_setup.py       — 統一的なログ設定（stdout + 日次ファイル）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - data/                    — デフォルト DB / flag / pid を置くディレクトリ（実行時に作成される）

（上記は抜粋です。各モジュール内に詳細なドキュメント文字列が含まれています。）

---

## 開発者向けノート / 注意点

- 環境変数の自動読み込み:
  - プロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。
  - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等で、起動時に必要カラムが無ければ ALTER TABLE で追加します。

- OpenAI 呼び出し:
  - API エラーやレート制限はリトライ実装がありますが、API キー漏えいに注意してください。
  - OpenAI を利用する機能はテストでモック可能（モジュール内部の呼び出し関数を差し替えられる設計）。

- ログ:
  - logs/<app_name>.log に日次でローテートして出力（30日保持）
  - ログディレクトリ作成に失敗した場合はコンソール出力のみになります

---

## サポート / 拡張案

- Broker クライアントの追加（実ブローカ API 実装）
- 銘柄ごとの lot_size をマスタ管理する拡張
- より高度なリスク管理ポリシー（トレーリングストップ、分散制約）
- AI モデルの変更 / プロンプト最適化 / 誤動作検知の強化

---

必要であれば、README にサンプル .env のテンプレートや、systemd / サービス定義例、CI 用の簡易テスト手順なども追加します。どの情報を詳細化したいか教えてください。