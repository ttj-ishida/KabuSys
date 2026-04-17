# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」のコアモジュール群です。戦略・ポートフォリオ構築、注文実行、監視、AI を使ったニュース評価やレジーム判定、研究用のファクター計算などを含みます。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要コマンド例）
- 環境変数 / 設定の重要点
- ディレクトリ構成（主要ファイル説明）
- 運用メモ / 停止方法

---

## プロジェクト概要

KabuSys は次の機能を持つモジュール化された自動売買プラットフォームのコア実装です。

- DuckDB / SQLite を使った時系列データ・メタデータの保存
- 戦略のためのファクター計算・特徴量探索（research）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 実行エンジン（ExecutionEngine）とブローカークライアント抽象化（paper_trading と live を分離）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）およびアラート / Kill Switch
- AI を使ったニュースセンチメント（OpenAI）と市場レジーム判定
- 運用支援スクリプト（環境設定ウィザード・設定検証・ペーパートレード検証レポート）

設計方針として、ルックアヘッドバイアス回避（日時参照を明示的に渡す）、フェイルセーフ（API失敗時の安全なフォールバック）、本番／ペーパートレードの分離が考慮されています。

---

## 主な機能一覧

- 環境設定ウィザード（対話式で .env を生成）
- 設定検証 CLI（必須環境変数や config/*.yaml のチェック）
- ExecutionEngine の起動（実際の注文または MockBroker を使用する paper_trading）
- Monitoring（システム稼働・注文滞留・リスク監視）と Kill Switch
- Portfolio モジュール：候補選定、重み計算、リスク制御、ポジションサイズ計算
- Research モジュール：モメンタム・ボラティリティ・バリュー等のファクター計算、IC 計算等
- AI モジュール：ニュース NLP（OpenAI）による銘柄スコアリング、マクロセンチメントを使ったレジーム判定
- 運用ツール：Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションの union 型演算子 `|` を使用）
- Git 等でソースをクローン済み

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（一例）
   - pip install duckdb psutil openai
   - PyYAML を用いた YAML 検証を行う場合: pip install pyyaml
   - （追加で使うライブラリ・バージョンはプロジェクト側で管理してください）

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動でルート（プロジェクトルート）に `.env` を作成
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - その他デフォルト値:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合は `--strict` を付ける

---

## 使い方

重要なエントリポイント（モジュール実行コマンド例）

- 環境設定ウィザード（.env を生成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（実行エンジン）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV によって動作モードが変わる
      - development: 発注なし（開発）
      - paper_trading: MockBrokerClient を使用し `data/paper_trading.db` に記録
      - live: 実際に発注
    - 実行中は PID ファイル（data/execution.pid）を作成
    - 停止は監視用の停止フラグ（data/stop_requested.flag）を作成すると検出して停止します

- Monitoring 起動（SystemMonitor の単純ループ）
  - python -m kabusys.run_monitoring
  - オプション: 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き（デフォルト 60 秒）
  - 監視は MonitoringDB（Settings.sqlite_path）を使い、KABUSYS_ENV に関係なく本番 sqlite_path を使用します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または指定 DB: --db path/to/db

- AI 機能（OpenAI）
  - 環境変数 OPENAI_API_KEY を設定するか、関数呼び出しで api_key を渡す
  - ニューススコアリング: kabusys.ai.score_news（DuckDB コネクションと target_date を渡す）
  - レジーム判定: kabusys.ai.regime_detector.score_regime

停止／Kill
- ExecutionEngine を強制停止させるには KillSwitch が利用する `data/kill.flag` を生成（KillSwitch の評価により実行エンジンを停止させる）
- 実行ループ（run_monitoring / run_execution）を外部から終了させるには `data/stop_requested.flag` を作成すると各ループが検出して終了します

ログレベル
- LOG_LEVEL 環境変数でログレベルを設定（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

## 環境変数 / 設定の重要点

主な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- データベース
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）

- AI
  - OPENAI_API_KEY（ニュース NLP / レジーム検出で使用）

- モニタリング / 運用
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60）
  - PID_FILE_PATH（ExecutionEngine で使用、デフォルト data/execution.pid）
  - KILL_FLAG_PATH（KillSwitch が書き込むフラグ、デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。1=クリア。production では 0 推奨）

- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）

自動 .env ロード
- プロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` と `.env.local` を自動読み込みします
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## ディレクトリ構成（主要ファイルの概要）

（src/kabusys 以下を想定）

- __init__.py
  - パッケージ宣言 / バージョン

- config.py
  - Settings クラス: 環境変数読み込み・整合性チェック
  - .env 自動ロードロジック

- config_setup.py
  - 対話式ウィザードで .env を生成 / 更新

- validate_config.py
  - 起動前チェック CLI（必須 env や config/*.yaml の検査）

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading での分離、PID 管理、stop flag 感知）

- run_monitoring.py
  - SystemMonitor の単純ポーリング起動スクリプト（MONITOR_POLL_INTERVAL で間隔調整）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など
  - 注文実行ロジック（外部ブローカーとのやり取りを抽象化）

- monitoring/
  - monitoring_db.py : SQLite 用永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py : システム状態・データ鮮度チェック
  - trade_monitor.py : 注文滞留・約定異常チェック
  - risk_monitor.py : ドローダウン・ポジション上限チェック
  - kill_switch.py : フラグファイルによる停止シグナル生成
  - monitoring_engine.py : 各 Monitor を束ねるエンジン
  - alert_manager.py : （アラート送信ロジック、LINE など。実装参照）

- ai/
  - news_nlp.py : News を OpenAI で評価して ai_scores を更新するロジック
  - regime_detector.py : ETF MA とマクロニュースを組み合わせたレジーム判定
  - AI 呼び出し部分はリトライ・JSON バリデーションなどを実装

- portfolio/
  - portfolio_builder.py : 候補選定・重み付け（等金額・スコア重み）
  - position_sizing.py : 発注株数計算（risk_based, equal, score）
  - risk_adjustment.py : セクターキャップ / レジーム乗数

- research/
  - factor_research.py : モメンタム / ボラティリティ / バリュー等の計算（DuckDB 経由）
  - feature_exploration.py : 将来リターン計算・IC・統計サマリー

- tools/
  - paper_verification_report.py : ペーパートレードの検証レポート生成 CLI

- utils/
  - process_priority.py : プラットフォーム差を吸収するプロセス優先度 / CPU affinity 設定ユーティリティ

その他
- data/ : デフォルトの DB / flag / pid ファイル置き場（存在しない場合は起動時に作成されることが多い）
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag

---

## 運用メモ

- 本番環境（KABUSYS_ENV=live）では特に LINE 通知や KILL_FLAG_CLEAR_ON_START の扱いに注意してください。validate_config は live 時に追加の警告を出します。
- Paper Trading は本番 SQLite と分離されます（Settings.paper_sqlite_path）。安全に動作確認が行えます。
- run_monitoring は MonitoringDB（sqlite）に書き込みますが、monitoring は KABUSYS_ENV に依らずデフォルトの sqlite_path（本番）を使う点に注意。
- OpenAI を使う機能は API 呼び出し失敗に備えたフォールバックが実装されています（例: macro_sentiment=0.0）。ただし API key は必須。
- process_priority.set_process_priority("high") が起動時に呼ばれます。権限がない環境では警告が出ますが処理は継続します。
- ローカルでのテスト時に自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

この README はコードベースの主要ポイントと運用フローをまとめたものです。詳細な設計（PortfolioConstruction.md、StrategyModel.md など）が別ドキュメントとして存在する想定のため、各モジュールの内部ロジックについては該当ファイルの docstring を参照してください。ご不明な点があれば具体的な操作や目的を教えてください。README の内容を補足・調整します。