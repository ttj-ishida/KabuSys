# KabuSys

日本株向け自動売買・リサーチ基盤の軽量ライブラリ群（README）。  
この README はリポジトリ内の主要モジュールと使い方をまとめたものです。

概要、機能、セットアップ、使い方、ディレクトリ構成を日本語で記載します。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチを目的としたモジュール群です。主な役割は以下の通りです。

- ExecutionEngine：発注・注文管理・リスク管理を統括する実行コンポーネント
- Monitoring：システム稼働状況・注文状況・リスク閾値を常時監視し、必要に応じて Kill Switch を発動
- Portfolio construction：銘柄選定、配分、ポジションサイジングの純粋関数群
- Research：DuckDB を利用したファクター計算や将来リターン・IC 分析
- AI 補助：ニュース記事の NLP（OpenAI）によるセンチメント評価や市場レジーム判定
- ユーティリティ：ログ設定、プロセス優先度設定、.env ウィザード、設定検証など

設計上の注意点：
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離され、data/paper_trading.db を使用します。
- 監視（monitoring）は環境にかかわらず本番の sqlite パス（Settings.sqlite_path）を参照する設計になっている箇所があります（コード内の取り扱いに注意してください）。
- OpenAI を利用する機能は環境変数 OPENAI_API_KEY を必要とします。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV による paper/live 動作切替）
  - run_monitoring.py — SystemMonitor をポーリングで実行（MONITOR_POLL_INTERVAL で間隔変更可）
- 設定管理・検証
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 環境変数・config/*.yaml の事前検証 CLI
- 監視・Kill Switch
  - monitoring/monitoring_db.py — 監視用 SQLite テーブル定義と永続化 API
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py
- Execution（発注）
  - execution/* — BrokerFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler 等
  - paper_trading モードでは MockBrokerClient を使用（完全に本番 DB から分離）
- Portfolio（銘柄選定・配分）
  - portfolio/portfolio_builder.py, position_sizing.py, risk_adjustment.py
- Research（DuckDB ベースのファクター計算）
  - research/factor_research.py, feature_exploration.py
- AI（OpenAI 利用）
  - ai/news_nlp.py — ニュース記事を集約して LLM に投げ、銘柄別スコアを ai_scores テーブルへ書込
  - ai/regime_detector.py — ETF の MA 乖離 + マクロニュースで市場レジーム判定
- ツール
  - tools/paper_verification_report.py — Paper Trading の検証レポート生成

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてワーキングディレクトリに移動
   - 例: git clone ... && cd <repo>

2. Python 環境（推奨: venv）を作成・有効化
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows (PowerShell): .venv\Scripts\Activate.ps1

3. 必要パッケージをインストール
   - 最低限必要なパッケージ（コード参照）:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（validate_config で YAML 検証を行う場合、任意）
   - 例:
     - pip install duckdb psutil openai
     - pip install pyyaml  # 任意

   ※ requirements.txt があれば `pip install -r requirements.txt` を推奨します（本リポジトリに無い場合は上記の個別インストール）

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で .env を作る場合、少なくとも以下は必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - デフォルトの DB / ファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 必要に応じてディレクトリを作成（多くのスクリプトは起動時に自動作成を試みます）

---

## 使い方

以下はよく使うコマンドの例です。

- .env 設定ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - 簡単に起動: python -m kabusys.run_execution
  - 実行フローメモ:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db にローカル記録
    - 起動直後に data/stop_requested.flag が存在する場合はエンジンを起動せず終了
    - 停止は data/stop_requested.flag の作成や ExecutionEngine.stop() を通じて行われます

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
    - デフォルトは 60 秒。0 以下の値は無効扱いで 60 秒にフォールバックされます。

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI バッチ処理（プログラム的に呼ぶ場合）
  - ai.score_news(conn, target_date, api_key=...)  # raw_news -> ai_scores
  - ai.regime_detector.score_regime(conn, target_date, api_key=...)  # market_regime 更新
  - OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY を使用

- Kill Switch / 停止関連
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリア動作があります（本番では推奨されません）

ログ設定:
- 共通のログ初期化は kabusys.utils.logging_setup.setup_logging(app_name="...") を通じて行われます
- ログは stdout と logs/<app_name>.log（日次ローテーション）に出力

注意点:
- OPENAI_API_KEY が未設定だと AI 関連機能は例外になるため、呼び出す際はキーの設定を確認してください
- validate_config により必須環境変数やパスの存在有無を起動前に検出できます

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- データベース / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)

- ログ・実行制御
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR
  - KILL_FLAG_CLEAR_ON_START (0/1)

- その他
  - OPENAI_API_KEY（OpenAI を利用する場合）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒。デフォルト 60）

---

## ディレクトリ構成

以下はパッケージルート（src/kabusys）配下の主要ファイルとサブパッケージの説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — Settings クラス（環境変数読み込み・デフォルト・検証）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM スコアリング / ai_scores 書込
    - regime_detector.py — 市場レジーム判定と market_regime 書込

  - monitoring/
    - monitoring_db.py — SQLite テーブル定義 + MonitoringDB wrapper
    - system_monitor.py — システム稼働・データ鮮度チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （コード内参照）注文系監視（詳細ファイルがリポジトリに存在）
    - kill_switch.py — kill.flag 書込・判定処理
    - monitoring_engine.py — 各 Monitor を束ねた実行ループ
    - alert_manager.py — （アラート送信処理、LINE 等）※実装に依存

  - execution/
    - execution_engine.py — ExecutionEngine 本体（run_session 等）
    - broker_factory.py — ブローカークライアント生成（実/モック切替）
    - order_manager.py / order_repository.py / risk_manager.py / reconciler.py など

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算・上限・丸めロジック
    - risk_adjustment.py — セクター上限・レジーム乗数

  - research/
    - factor_research.py — Momentum/Volatility/Value のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計要約

  - tools/
    - paper_verification_report.py — Paper Trading の Pass/Fail レポート

  - utils/
    - logging_setup.py — 統一ログ設定ユーティリティ
    - process_priority.py — プロセス優先度/CPU affinity 設定ユーティリティ

その他:
- data/ — デフォルトで使用されるデータ・DB・フラグファイル（リポジトリに含まれていない場合は起動時に作成されることが多い）
- logs/ — ログ出力先（logging_setup が作成）

---

## 開発上の注意 / トラブルシューティング

- DuckDB, psutil, openai の未インストールに注意。import エラーが出る場合、pip でインストールしてください。
- validate_config は PyYAML があれば config/*.yaml の中身もパースして検証します。未インストールでも実行は可能ですが YAML 検証はスキップされます。
- OpenAI を使う処理は API のレートリミットやネットワークエラーを考慮してリトライ実装がありますが、API キーの設定は必須です（例外が発生します）。
- run_execution/run_monitoring はプロセス優先度を "high" にセットしようとします。権限やプラットフォームにより設定に失敗してもログに WARN が出てスキップされます。
- Kill Switch / stop flag 周りは運用上の重要機能です。KILL_FLAG_CLEAR_ON_START を本番で 1 にするのは危険です（自動クリアされると手動で止めたはずのプロセスが再起動してしまう可能性あり）。

---

この README はコード内の docstring / コメントに基づいて作成しました。実際に運用する場合は各モジュール（execution, monitoring, ai）の詳細仕様・設定ファイル（config/*.yaml）・依存する Broker 実装や外部サービスの設定を合わせてご確認ください。必要であればこの README を基にさらに詳細な運用手順やデプロイ手順を作成できます。