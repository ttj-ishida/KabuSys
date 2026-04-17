# KabuSys

日本株向けの自動売買システム（ライブラリ兼実行スクリプト群）の一部です。  
このリポジトリには、環境設定・監視・発注エンジン・ポートフォリオ構築・リサーチ・AI（ニュースのセンチメント評価）などの主要コンポーネントが含まれます。

---

## 概要

- DuckDB / SQLite をデータ層に使い、発注ロジックと監視を分離したアーキテクチャを採用しています。
- 本番（live）・ペーパートレード（paper_trading）・開発（development）の環境に対応。
- 監視（Monitoring）コンポーネントは独立して動作し、システム稼働率・注文状況・リスクをチェックして必要に応じて Kill Switch（停止フラグ）を書き込みます。
- ペーパートレード時は MockBroker を用いて本番 DB と分離し、専用の SQLite（data/paper_trading.db）へ記録します。
- OpenAI（gpt-4o-mini）を用いたニュースNLP・レジーム判定機能を含みます（API キーが必要）。

---

## 主な機能一覧

- 設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - Settings クラスで環境変数を型付きに取得
  - 対話式ウィザードで .env を作成する `kabusys.config_setup`
  - 設定検証 CLI `kabusys.validate_config`（--strict オプションあり）
- 実行
  - 発注エンジン起動スクリプト: `kabusys.run_execution`
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、専用 DB に記録
    - 停止はプロセス間フラグを用いて制御（data/stop_requested.flag / data/kill.flag）
  - 監視ループ起動スクリプト: `kabusys.run_monitoring`
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）で上書き可能
- 監視（Monitoring）
  - SystemMonitor: CPU・メモリ・ディスク・プロセスの生存確認、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格の異常検出
  - RiskMonitor: ドローダウンやポジション上限の監視、dashboard 更新
  - MonitoringDB: monitoring 用 SQLite のスキーマ管理（system_status / trade_logs / positions / risk_logs / dashboard）
  - KillSwitch / AlertManager（LINE通知）
- ポートフォリオ構築（純粋関数）
  - 候補選定、重み付け（等配分・スコア加重）、ポジションサイズ計算、セクターキャップ適用、レジーム乗数
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC（Spearman）計算、統計サマリー
- AI（OpenAI）
  - ニュースを集約して銘柄ごとにセンチメント評価（ai_scores テーブルへ書込）
  - マクロニュースと ETF の MA を使った市場レジーム判定（market_regime テーブルへ書込）
- ツール
  - Paper Trading の検証レポート生成スクリプト `kabusys.tools.paper_verification_report`

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンして作業ディレクトリへ移動します。

2. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストールしてください（requirements.txt がない場合は手動で）。
   - 必要な代表パッケージ:
     - duckdb
     - psutil
     - openai
     - requests
     - PyYAML（validate_config の YAML 検査を有効にする場合）
   - 例:
     - pip install duckdb psutil openai requests pyyaml

4. .env の準備
   - 対話式ウィザードを使って .env を生成:
     - python -m kabusys.config_setup
   - またはリポジトリの .env.example を参考に `./.env` を手動作成してください。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も含めて厳格に扱いたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - デフォルトの DB パスは data/ 以下にあります（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）。
   - 自動的に作られる部分もありますが、明示的に作成して権限を確認しておくと安全です。

---

## 主な環境変数（代表）
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading: mock broker を使用し、paper_trading 用 SQLite に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定動作（instant, partial, never, reject）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector など）で必要
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1"で有効。運用では注意）

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 発注エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading なら paper_trading 用 SQLite を使用／MockBroker を使う
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中に data/stop_requested.flag が作成されるとエンジンを停止する
    - 実行時に data/execution.pid（デフォルト）へ PID を書きます

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を指定可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に production 監視 DB（Settings.sqlite_path）を使います（環境に依らず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（ニューススコア・レジーム判定）
  - ニューススコア取得: kabusys.ai.score_news（スクリプトから呼ぶ / API キーが必要）
  - レジーム判定: kabusys.ai.regime_detector.score_regime（API キーが必要）
  - 注意: API キーが無い場合は例外になるか、内部でフェイルセーフ処理（0.0）となる箇所があります。

---

## 停止方法 / Kill Switch

- run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag を監視しています。
  - このファイルを作成すると、各ループは次回のチェックで安全に終了します。
  - 例: touch data/stop_requested.flag

- KillSwitch（自動監視による停止シグナル）は data/kill.flag を書き込みます。
  - ExecutionEngine は起動時に kill.flag の存在に注意し、kill.flag があれば起動しない運用が想定されます。
  - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動的にクリアする運用もできるため、設定運用に注意してください。

---

## 監視用 DB スキーマ（概要）

monitoring_db.init_monitoring_db により作成されるテーブル（冪等）:
- system_status: システム稼働データ（cpu/memory/disk/process_ok）
- trade_logs: 発注イベントログ（event_type, client_order_id, code, side, qty, price, filled_qty, latency_ms）
- positions: 保有ポジション（code, qty, avg_price, current_price, updated_at）
- risk_logs: リスク関連イベントログ（event_type, metric_name, metric_value, threshold, detail）
- dashboard: 集計（id=1 の単一行で管理）

※ マイグレーション処理で必要カラムが足りない場合は ALTER TABLE による追加を行います。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — Settings クラス、.env 自動ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ（テーブル作成 + MonitoringDB）
    - monitoring_engine.py   — 各モニタを束ねる
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常検出
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書込ロジック
    - alert_manager.py       — LINE 通知（プッシュ）
  - execution/                — 発注系（OrderManager / Engine / BrokerFactory 等）※実装は一部のみ提示
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数計算・単元丸め・キャップ
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value 等
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py            — ニュースを LLM でスコア化して ai_scores へ書込
    - regime_detector.py     — マクロ + ETF MA によるレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力

---

## 開発上の注意・運用メモ

- 環境依存
  - Settings は .env / .env.local / OS 環境変数の順で自動ロードされます（プロジェクトルート検出に .git または pyproject.toml を使用）。
  - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番運用時の注意点
  - KABUSYS_ENV=live の場合は設定により重大な警告が出ます。LINE 通知の設定や KILL_FLAG_CLEAR_ON_START の値を十分検討してください。
  - process priority や CPU affinity の設定は OS 権限やプラットフォームに依存します。権限不足の場合は警告が出て無視されます。
- AI (OpenAI)
  - OPENAI_API_KEY が必要です。API コールは失敗時に複数回リトライしますが、コスト・レイテンシ・帯域などを考慮して運用してください。
- DB の分離
  - 監視用 SQLite（SQLITE_PATH）とペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）は別ファイルにして本番データと分離しています（paper_trading モード）。

---

README は以上です。必要であれば以下を追加で用意できます。

- 例となる .env.example（テンプレート）
- systemd / supervisor 用のユニットファイル例（run_monitoring/run_execution の起動方法）
- requirements.txt（正確なバージョン指定）