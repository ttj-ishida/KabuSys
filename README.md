# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ内ドキュメント（README）。  
この README ではプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買（Execution）とそれを支える監視・研究・ポートフォリオ構築ツール群を備えた Python ベースのシステムです。  
主な設計方針は以下の通りです。

- 発注ロジックと監視ロジックを分離（ExecutionEngine / MonitoringEngine）。
- Paper Trading と Live（本番）を環境変数で切り替え可能（DBは分離）。
- DuckDB を分析用に、SQLite を監視 / 履歴保存用に使用。
- OpenAI（gpt-4o-mini 等）を用いる NLP / レジーム判定モジュールを内包（APIキー必須）。
- ロギング・プロセス優先度設定・Kill Switch（フラグファイル）など運用機能を備える。

---

## 機能一覧

- Execution（発注エンジン）
  - Broker クライアント（実ブローカー or MockBroker：KABUSYS_ENV に依存）
  - RiskManager、OrderManager、Reconciler を組み合わせた ExecutionEngine
  - PID ファイル、停止フラグ監視による安全停止機能
- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス状態、データ鮮度監視
  - TradeMonitor / RiskMonitor：滞留注文・約定異常・ドローダウン・ポジション上限監視
  - KillSwitch：条件により data/kill.flag を書き込み Execution を停止
  - MonitoringDB（SQLite）：system_status / trade_logs / positions / risk_logs / dashboard テーブル
- 研究・分析
  - factor_research：モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - feature_exploration：将来リターン、IC（Information Coefficient）、統計サマリ
- ポートフォリオ構築
  - 候補選定、重み計算（等配分 / スコア配分）
  - セクター制限、レジーム乗数、ポジションサイズ計算（lot 単位丸め・aggregate cap）
- AI（OpenAI）連携
  - news_nlp：ニュース記事を LLM でセンチメント化して ai_scores に格納
  - regime_detector：ETF MA とマクロニュースセンチメントを合成して日次レジーム判定
- ツール群
  - config_setup：対話的 .env 作成ウィザード
  - validate_config：起動前チェック（環境変数 / config YAML / パス等）
  - paper_verification_report：Paper Trading の検証レポート生成

---

## 前提条件 / 依存関係

- Python 3.9+（ソースは型注釈を使用。3.8 でも動く場合あり）
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に YAML を検証する場合）
- SQLite は標準ライブラリで利用
- ネットワーク接続（OpenAI / ブローカー API 使用時）

インストール例（仮に requirements.txt がない場合）:
pip install duckdb psutil openai pyyaml

（実際の requirements.txt があればそれを使ってください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt  （無ければ個別に pip install duckdb psutil openai pyyaml）

4. 環境変数設定（.env）
   - 対話式ウィザード: python -m kabusys.config_setup
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須
     - KABUSYS_ENV を選択（development / paper_trading / live）
   - .env を手動で作る場合は .env.example を参考に設定してください

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 本番前に --strict を付けると警告も FAIL 扱いになります:
     - python -m kabusys.validate_config --strict

6. DB / ディレクトリの初期化
   - 必要に応じて `data/` や `logs/` ディレクトリを作成しますが、多くは起動時に自動生成されます。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合は MockBrokerClient を使用し、Paper DB（PAPER_TRADING_SQLITE_PATH）へ記録されます
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading 時の約定モード: instant|partial|never|reject、デフォルト: instant）
- SQLITE_PATH（監視 DB: デフォルト data/monitoring.db）
- DUCKDB_PATH（分析 DB: デフォルト data/kabusys.duckdb）
- OPENAI_API_KEY（AI モジュール使用時に必須）
- LOG_LEVEL（ログレベル: DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番起動時の kill.flag 自動クリア: 0/1）

---

## 使い方

以下は主要なエントリポイントの実行例（プロジェクトルートで実行）。

1. 環境ウィザード（.env の作成・更新）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

3. Execution（発注エンジン）を起動
   - python -m kabusys.run_execution
   - 動作開始前に data/stop_requested.flag が存在すると起動せず終了します
   - 起動時に PID ファイル（data/execution.pid）を作成します
   - KABUSYS_ENV=paper_trading の場合は paper DB（PAPER_TRADING_SQLITE_PATH）へ記録されます

4. Monitoring（監視）を起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
   - 監視は常に（環境にかかわらず）本番 sqlite_path を使用して監視テーブルを初期化します

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数を上書き可能）

6. AI モジュール（プログラムから呼び出す API）
   - kabusys.ai.score_news(conn, target_date, api_key=None)  # api_key 省略時は OPENAI_API_KEY を参照
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意・運用メモ
- 停止方法
  - run_execution/run_monitoring は data/stop_requested.flag を監視しています。ファイルを作成すると安全に停止させることができます。
  - Kill Switch は監視モジュールが条件を満たしたときに data/kill.flag を作成し、Execution に強制停止シグナルを送ります。
- Paper Trading は本番 DB と分離されています（デフォルト）。
- ログは `logs/<app_name>.log` に日次ローテーション保存されます。出力フォルダは LOG_DIR またはデフォルトの `logs/`。

---

## トラブルシューティング

- .env の自動読み込みが動作しない（テスト等）
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。
- ログファイルが作成されない
  - ログディレクトリの作成に失敗するとコンソール出力のみになります。パーミッション等を確認してください。
- OpenAI 呼び出しでエラーが出る
  - OPENAI_API_KEY の設定を確認し、ネットワーク接続とレート制限に注意してください。モジュールは一部のエラーに対してリトライを実装しています。

---

## ディレクトリ構成（主なファイル・モジュール）

（プロジェクトの src/kabusys 以下を中心に抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数・設定管理（.env 自動ロード・Settings クラス）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前チェック CLI

  - run_execution.py — ExecutionEngine 起動スクリプト（PID / stop flag 処理含む）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - utils/
    - logging_setup.py — ログの一元設定（Stream + TimedRotatingFileHandler）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

  - monitoring/
    - monitoring_db.py — SQLite のテーブル作成・永続化 API（MonitoringDB クラス）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — （滞留注文・約定異常監視、コードあり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — data/kill.flag の作成 / クリア
    - monitoring_engine.py — 各モニタを束ねるポーリングエンジン
    - alert_manager.py —（通知送信のラッパー：LINE など）（コード内参照）

  - execution/
    - broker_factory.py — ブローカークライアント生成（Mock/実ブローカー）
    - execution_engine.py — ExecutionEngine（セッション管理・発注ループ）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - position_sizing.py — 株数・上限・単元丸めロジック

  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ

  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄ごとのセンチメント化
    - regime_detector.py — ETF MA + マクロニュースで市場レジーム判定

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

- data/ （実行時に使用されるディレクトリ）
  - monitoring.db（デフォルトの監視 SQLite）
  - paper_trading.db（paper_trading 用）
  - kill.flag / stop_requested.flag / execution.pid などの運用フラグ・PID ファイル

- logs/ （デフォルトのログ出力先）
  - execution.log, monitoring.log, ... （日次ローテーション）

---

以上が本リポジトリの簡易 README です。実運用を行う前に必ず `python -m kabusys.config_setup` → `python -m kabusys.validate_config` を実行し、必要な環境変数（特に API トークン類）が設定されていることを確認してください。必要であれば README を元に運用手順（デーモン化 / systemd ユニット / コンテナ化）を追加で作成してください。