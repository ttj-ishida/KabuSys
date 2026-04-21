# KabuSys

日本株の自動売買・リサーチ基盤（モジュール群）のリポジトリ。  
この README はソースコード（src/kabusys 配下）に基づいて、プロジェクト概要・機能一覧・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

> 注: 実行スクリプトや一部モジュールは外部サービス（kabuステーション API、J-Quants、OpenAI など）やネイティブ拡張（duckdb, psutil 等）に依存します。運用前に .env を適切に設定し、依存パッケージをインストールしてください。

## プロジェクト概要
KabuSys は日本株を対象とした自動売買システムの基盤ライブラリ群です。主な目的は以下です。

- 戦略（リサーチ）用のファクター計算・特徴量解析
- ポートフォリオ構築（候補選定・重み算出・ポジションサイジング）
- 実行エンジン（ExecutionEngine）と発注管理（OrderManager / RiskManager）
- 監視機能（System/Trade/Risk モニタ）と Kill Switch による安全停止
- Paper Trading の検証レポート生成
- ニュースの NLP による銘柄センチメント／市場レジーム判定（OpenAI 経由）
- ロギング/環境設定ユーティリティ

設計方針として、データベース（SQLite / DuckDB）を利用した分析・ログ永続化、外部 API 呼び出しでの失敗をフェイルセーフに扱うこと、ルックアヘッドバイアスを避ける実装が意識されています。

## 主な機能一覧
- 環境/設定管理
  - .env 読み込み（自動ロード）、Settings クラスによる環境変数 API
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行（Execution）
  - run_execution.py により ExecutionEngine を起動
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い本番 DB と完全分離（data/paper_trading.db）
  - Process 優先度設定、PID/停止フラグ管理
- 監視（Monitoring）
  - run_monitoring.py により SystemMonitor のポーリングを開始
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
  - MonitoringEngine: System/Trade/Risk モニタを束ね通知・Kill Switch 評価
  - KillSwitch: data/kill.flag による ExecutionEngine 停止シグナル
- リサーチ / ファクター
  - momentum / volatility / value 等のファクター計算（DuckDB を用いた SQL ベース実装）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- ポートフォリオ構築
  - 候補選定（score/ ranking）、等配分・スコア加重、リスク調整（セクター制限、レジーム乗数）
  - ポジションサイジング（単元株丸め、aggregate cap、risk-based 等）
- AI（OpenAI）連携
  - ニュース記事のセンチメント評価（kabusys.ai.news_nlp）
  - マクロニュースと ETF MA に基づく市場レジーム判定（kabusys.ai.regime_detector）
  - API 呼び出しはリトライ/バックオフやレスポンス検証を実装
- ユーティリティ
  - ロギング設定ユーティリティ（ログ回転・コンソール出力統一）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

## 必要条件（目安）
- Python 3.10 以上（ソースでの型記法により）
- SQLite（標準ライブラリ）
- 必要 Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証のため、任意）
- ネットワークアクセス: kabuステーション API / J-Quants / OpenAI（実行する機能に応じて）

（注）requirements.txt はこの README 生成時点で含まれていない想定のため、最低限上記を pip でインストールしてください。

例:
pip install duckdb psutil openai PyYAML

## セットアップ手順（ローカルでの基本フロー）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （必要に応じて他パッケージを追加）
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - または .env.example を参照して手動で作成
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - LOG_LEVEL（デフォルト INFO）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1）
   - 作成後、設定を検証: python -m kabusys.validate_config [--strict]
5. データディレクトリの作成
   - ログディレクトリや data ディレクトリが自動作成されることもありますが、事前に用意しておくことを推奨します:
     - mkdir -p data logs
6. DuckDB / SQLite の初期化
   - 多くのテーブルは実行時に自動で作成されます（init_monitoring_db が冪等で作成）。
   - 必要なら事前に価格データや財務データを DuckDB にロードしておく。

## 使い方（起動 / 管理）
- 監視（SystemMonitor）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが終了してプロセスを停止します（例: touch data/stop_requested.flag）
  - 監視は MonitoringDB（settings.sqlite_path）へログを書き込みます（監視は sqlite_path を本番パスで使用）
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
  - run_execution は PID ファイル（data/execution.pid）や stop flag を監視し、停止シグナルを受け取ると安全に停止します
- 設定ウィザード / 検証
  - .env 対話式作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH または --db で DB を指定
- AI（ニュース / レジーム判定）をプログラムから呼ぶ例
  - Python スクリプト内で:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
    - どちらも DuckDB 接続と target_date（date オブジェクト）を渡して実行します
  - API キーは OPENAI_API_KEY 環境変数または関数引数で渡す
- ログ
  - デフォルトで console と logs/<app_name>.log（日次ローテート、30日保存）に出力
  - ログディレクトリは LOG_DIR 環境変数で変更可能

### 停止手段（安全シャットダウン）
- 全体停止（監視 / 実行スクリプト共通）:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します
    - 例: mkdir -p data && touch data/stop_requested.flag
- ExecutionEngine 停止（Kill Switch）
  - KillSwitch が条件を満たすと data/kill.flag に理由を書き込み、ExecutionEngine に停止シグナルを与えます
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動で kill.flag をクリアします（本番では 0 を推奨）

## 主要ファイル / ディレクトリ構成
以下は src/kabusys 配下の主要なファイルと役割の簡易一覧です（コードベースから抜粋）。

- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン等）
  - config.py — 環境変数・Settings 管理、自動 .env 読み込みロジック
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 設定検証 CLI（必須変数や config/*.yaml の存在チェック）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 時は MockBroker）
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化（テーブル作成 / CRUD ヘルパ）
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス状態のチェック
  - trade_monitor.py — （Trade の監視ロジック）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書き込み・判定ロジック
  - monitoring_engine.py — 各モニタを束ねてポーリング・アラート発行
  - alert_manager.py — （アラート通知を外部に送る実装）
- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・単元丸め・aggregate cap
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - __init__.py — 公開 API
- src/kabusys/research/
  - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
  - __init__.py — 公開 API
- src/kabusys/ai/
  - news_nlp.py — raw_news を OpenAI に投げて銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector.py — ETF MA とマクロニュースの LLN 評価を合成して market_regime を決定
  - __init__.py — 公開 API
- src/kabusys/utils/
  - logging_setup.py — ログハンドラ設定（Stream + TimedRotatingFile）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成 CLI

（注）この README は実際のファイル構成を簡略化して記載しています。詳細は各モジュールの docstring を参照してください。

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）
- OPENAI_API_KEY — OpenAI API（AI 機能を使う場合）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — PaperTrading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR — ログディレクトリ（default: logs）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、default: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

## 開発・デバッグヒント
- 設定検証: python -m kabusys.validate_config（--strict で警告を失敗扱い）
- 対話式 .env 作成: python -m kabusys.config_setup
- 各モジュールのユニットテストでは外部 API 呼び出し（OpenAI / BrokerClient など）をモックすることを推奨
- DuckDB のクエリはローカルで直接検証できます（duckdb.Repl など）
- run_execution / run_monitoring は PID・フラグファイルを使ってプロセス管理するため、cron や systemd から起動する想定で安全停止が可能

## ライセンス / コントリビューション
この README ではライセンス情報や貢献ルールは含めていません。実際のリポジトリに LICENSE / CONTRIBUTING.md がある場合はそちらに従ってください。

---

追加で README に載せたい具体的なコマンド例、requirements.txt の推奨内容、あるいは各モジュールの API ドキュメント（関数シグネチャ・引数の説明）などがあれば教えてください。必要に応じて README を拡張して、導入手順や運用手順をより詳しく記述します。