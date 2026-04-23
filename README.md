# KabuSys — README

このリポジトリは日本株向けの自動売買・研究・監視フレームワーク「KabuSys」のソースコードです。  
以下はコードベース（src/kabusys 以下）をもとに作成した README です。

注意: 実行には外部パッケージ（例: duckdb, psutil, openai など）が必要です。環境に合わせて依存関係をインストールしてください。

---

## プロジェクト概要

KabuSys は、日本株の自動売買（Execution）・監視（Monitoring）・リサーチ（Research）・ポートフォリオ構築（Portfolio）・AI（ニュースセンチメントやレジーム判定）等の機能を備えたモジュール群です。  
設計方針として、次を重視しています。

- 本番 / ペーパートレードを環境変数で切替可能（KABUSYS_ENV）
- DuckDB / SQLite を使った履歴・分析データ管理
- モジュールは純粋関数（副作用少）と DB 層の分離
- OpenAI を使ったニュース解析はオプション（APIキー必須）
- 監視・Kill Switch による安全停止機構

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 主な機能一覧

- Execution
  - ExecutionEngine を起動して発注フローを実行（実際発注 / モック発注の切替）
  - RiskManager・OrderManager・Reconciler 等のコンポーネントを含む
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - kill.flag による ExecutionEngine 停止（Kill Switch）
  - 監視ログの永続化（SQLite）
- Portfolio
  - 候補選定、重み算出、ポジションサイズ計算、セクター制限、レジーム乗数等
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン・IC 等の計算ユーティリティ
- AI
  - ニュースの LLM（OpenAI）によるセンチメント集約（ai/news_nlp.py）
  - マクロニュース + ETF MA200 から市場レジームを判定（ai/regime_detector.py）
- Tools
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- 設定ユーティリティ
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 起動前の設定検証 CLI（validate_config.py）
- Logging & Process utilities
  - 統一的な logging セットアップ（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - プロジェクトに requirements.txt があれば:
     - pip install -r requirements.txt
   - 最低限必要となる主な依存例:
     - pip install duckdb psutil openai
   - 開発時に YAML 検証を行う場合:
     - pip install PyYAML

4. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を作成（.env.example を参考に）。

5. 設定の検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ
   - デフォルトでは `data/` 配下に DB ファイルが作られます（必要に応じて .env でパス変更）。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境 (development | paper_trading | live) — デフォルト: development
  - paper_trading 時は MockBrokerClient を使い、Paper 用 SQLite に記録される
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 関連機能で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定（任意）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: execution 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）

---

## 使い方（実行例）

- 環境変数を設定（例: Unix シェル）
  - export KABUSYS_ENV=development
  - export JQUANTS_REFRESH_TOKEN=...
  - export KABU_API_PASSWORD=...
  - export OPENAI_API_KEY=...

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）

  特記事項:
  - run_monitoring は常に "本番 sqlite_path" を使って監視データを記録します（環境に依らず monitoring DB を使用）。
  - stop リクエストはプロジェクトルートの data/stop_requested.flag（存在検知）で行われます。

- Execution（発注エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合は Paper 用 DB（PAPER_TRADING_SQLITE_PATH）を使い、MockBroker を利用します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - エンジンは data/execution.pid を PID ファイルとして扱います。

- 設定ウィザード
  - python -m kabusys.config_setup
  - 対話で .env を生成・更新します

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH（無指定時 data/paper_trading.db）

- AI 関連（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

  いずれも OpenAI API キーが必要です（引数または環境変数 OPENAI_API_KEY）。

---

## ログ

- logging_setup.py により、ルートロガーは以下を設定します:
  - コンソール stdout（StreamHandler）
  - 日次ローテーションされるファイルハンドラ（logs/<app_name>.log、30日保持）
- 既定のログディレクトリ: logs/
- ログレベルは引数・環境変数 LOG_LEVEL で上書き可能

---

## Kill Switch / 停止制御

- KillSwitch により data/kill.flag（既定）を作成すると ExecutionEngine に停止命令を送れます。
- run_monitoring / MonitoringEngine は各種チェック（ドローダウン・ポジション上限等）で Kill Switch を発動できます。
- run_execution/run_monitoring は data/stop_requested.flag の存在で起動中ループを停止します。
- Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリアします（本番では 0 推奨）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定読み込みロジック
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - ai/
    - news_nlp.py            — ニュースの LLM センチメント集約
    - regime_detector.py     — 市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py      — 監視用 SQLite スキーマ & 永続化層
    - system_monitor.py     — システム状態・データ鮮度のチェック
    - trade_monitor.py      — (取引監視ロジック: 省略ファイルあり)
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag の書き込み/評価
    - monitoring_engine.py  — 複数 Monitor を束ねるエンジン
    - alert_manager.py      — (アラート送信ロジック: 省略ファイルあり)
  - execution/
    - execution_engine.py   — 実行エンジン（EngineConfig, run_session 等）
    - broker_factory.py     — ブローカークライアント生成（Mock/実装分岐）
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - data/
    - pipeline.py           — データパイプライン補助関数（例: get_last_price_date）
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

（注）上記は主要ファイルの抜粋です。実装の詳細は各ファイルの docstring / コメントを参照してください。

---

## 開発・運用上の注意

- 本番運用（KABUSYS_ENV=live）の場合は設定に十分注意してください。validate_config は live 向けの追加チェックを行います。
- OpenAI を利用する処理は API コストとレート制限の影響を受けます。APIキーは厳重に管理してください。
- DB マイグレーションは簡易的な ALTER TABLE を含みます。バックアップを取った上で実行してください。
- process_priority の設定や CPU affinity は権限や OS に依存します。権限不足時は警告のみで続行されます。
- .env は決して VCS にコミットしないでください（config_setup も注釈あり）。

---

## サンプル実行フロー（開発向け）

1. 仮想環境作成・依存インストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config でチェック
4. duckdb / sqlite の初期化は起動スクリプト（run_execution / run_monitoring）で自動的に行われる
5. 並行して監視プロセスを起動:
   - python -m kabusys.run_monitoring
6. Execution を起動:
   - python -m kabusys.run_execution

---

必要であれば、各モジュール（ExecutionEngine, MonitoringEngine, AI スコアリング等）のより詳細な使い方・API ドキュメントやテストのサンプルを別途作成します。どの部分を詳しく知りたいか教えてください。