# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株向けの自動売買フレームワーク KabuSys の一部です。  
監視（Monitoring）、発注エンジン（Execution）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントを含み、ローカル開発、ペーパートレード、本番（live）での運用を想定した設計になっています。

---

## プロジェクト概要

- 目的: 株式自動売買のロジック群（シグナル、ポジションサイジング、リスク管理）と、実行・監視・運用ツールを提供する。
- 設計方針:
  - データ分析は DuckDB（分析用 DB）を利用、運用ログ/監視は SQLite（monitoring.db）へ永続化。
  - 環境ごとに挙動を切り替え（development / paper_trading / live）。
  - .env ベースの設定管理（.env / .env.local、自動ロードあり。無効化可）。
  - OpenAI を利用したニュース NLP / レジーム判定機能を実装（必要時 API キー要）。
  - フェイルセーフ設計（API失敗時はフォールバック、kill switch による安全停止）。

---

## 主な機能一覧

- 環境設定・検証
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）: 必須環境変数・YAML の有無・パス妥当性などをチェック

- 実行エンジン
  - ExecutionEngine をスレッドで起動（kabusys.run_execution）
  - 環境が `paper_trading` の場合は MockBroker を使用し、ペーパートレード DB（data/paper_trading.db）へ記録
  - 起動時にプロセス優先度を調整

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine と監視起動スクリプト（kabusys.run_monitoring）
  - system_status / trade_logs / risk_logs / positions / dashboard を管理する SQLite ベースの監視 DB 初期化（monitoring_db）
  - KillSwitch によるフラグファイル書き込みで ExecutionEngine を安全停止

- ポートフォリオ構築（純粋関数）
  - 候補選定、等分配 / スコア加重配分、セクター制限、レジーム乗数、ポジションサイズ計算（lot 単位丸め）など

- リサーチ
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（スピアマンランク相関）計算、特徴量サマリー

- AI（OpenAI）
  - ニュース記事を LLM で評価して ai_scores に書き込む（kabusys.ai.news_nlp）
  - マクロニュースと ETF MA200 を使った市場レジーム判定（kabusys.ai.regime_detector）
  - 両機能とも OpenAI API（gpt-4o-mini 等）を利用。リトライ・バックオフやレスポンス検証を実装

- ツール
  - Paper Trading の検証レポート生成（kabusys.tools.paper_verification_report）

- ユーティリティ
  - プロセス優先度 / CPU affinity 設定（psutil ベース）
  - .env パーサ / 自動ロードロジック（config.py）
  - 設定読み書きウィザード（config_setup.py）

---

## 必要な環境変数（主なもの）

（kabusys.validate_config で未設定項目を検出できます。）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意（が推奨）:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — DEBUG/INFO/...
  - OPENAI_API_KEY — AI モジュールを使う場合必須
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）

設定自動ロード:
- プロジェクトルートに .env / .env.local があれば自動で読み込みます（OS 環境変数を優先）。
- 自動ロードを無効にするには環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要な挙動:
- KABUSYS_ENV=paper_trading の場合、Broker は Mock を使い paper_trading DB に記録（本番 DB と分離）。
- モニタリングは KABUSYS_ENV にかかわらず production 用 sqlite_path を使用する（monitoring は本番 DB を参照する設計）。

---

## セットアップ手順

1. Python と依存パッケージをインストール
   - 推奨: 仮想環境を作成してから実行
   - 依存例:
     - duckdb
     - psutil
     - openai (AI機能を使う場合)
     - PyYAML（config YAML 読み込み/検証を行いたい場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

2. プロジェクトルートへ移動し .env を作成
   - 推奨: 対話式ウィザードを使用
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考にして .env を作成

3. 設定を検証
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合:
     - python -m kabusys.validate_config --strict

4. データディレクトリ作成
   - デフォルトの DB / pid / flag の格納先は data/
   - 例:
     - mkdir -p data

5. 必要なら DuckDB / SQLite の初期データを用意（prices_daily / raw_financials / raw_news 等のデータは分析/AI モジュールで使用）

---

## 使い方（主要コマンド）

- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（発注エンジン）
  - python -m kabusys.run_execution
  - 特記事項:
    - 起動前に data/stop_requested.flag が存在する場合エンジンは起動しません
    - 停止は data/stop_requested.flag を作成することで行います（run_execution は定期的に存在をチェック）
    - ExecutionEngine は起動時に Settings.pid_file_path（デフォルト data/execution.pid）へ PID を書きます

- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60）
  - 停止はプロジェクトルート data/stop_requested.flag を作成するとループが終了します

- Paper Trading 検証レポート（標準出力へ出力）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数で指定も可）

- AI / リサーチ機能の呼び出し（Python API）
  - ニューススコア算出:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)
  - ファクター計算:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

- 開発用の個別実行（MonitoringEngine を単発実行してテストなど）
  - 組み立てたモニターを使って run_once() を呼ぶことで 1 回だけチェックできます（ユニットテストでの利用に便利）

---

## 停止・Kill Switch の扱い

- ExecutionEngine 停止フロー:
  - KillSwitch は RiskMonitor 等の判定結果に基づき data/kill.flag を書き込みます。ExecutionEngine はこのファイルを検出して安全に停止できます。
  - KillSwitch は既存ファイルがあれば上書きせず冪等的に動作します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると kill.flag を自動クリアする挙動になります（本番では 0 推奨）。

- 手動停止:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが停止します（run_execution は起動前にもチェックします）。

---

## 主要な設定項目（.env の例）

例 (.env):
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxxx
KILL_FLAG_CLEAR_ON_START=0
PAPER_FILL_MODE=instant

注意: .env は絶対にコミットしないでください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 単純ポーリング起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度・CPU affinity ヘルパ
  - monitoring/
    - monitoring_db.py       — SQLite 用監視 DB 初期化と永続化 API
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各モニターを束ねる実行ループ
    - alert_manager.py       — （アラート送信管理: ファイル途中）
  - execution/                — 発注周り（ファクトリ、エンジン、リポジトリ等）※一部ファイルはこの抜粋に含まれません
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 経由で銘柄ごとにスコア）
    - regime_detector.py     — マクロ + MA によるレジーム判定（OpenAI オプション）
    - __init__.py
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - data/ (runtime)
    - execution.pid
    - kill.flag
    - stop_requested.flag
    - monitoring.db / paper_trading.db / kabusys.duckdb など（デフォルトパス）

---

## 注意事項・運用上のポイント

- 本番運用（KABUSYS_ENV=live）時は特に注意:
  - LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を確認する。
  - KILL_FLAG_CLEAR_ON_START は本番で 0 を推奨（誤って Kill Switch を自動解除しない）。
  - validate_config で警告や欠損を事前に確認すること。

- AI モジュール:
  - OpenAI API キー（OPENAI_API_KEY）が必要。API 呼び出しにはコストがかかります。
  - レスポンス検証やリトライが入っていますが、API を多用する処理は運用負荷に注意してください。

- DB/ファイルの分離:
  - paper_trading 環境は本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。

---

必要であれば README の英語版や各モジュール（ExecutionEngine、OrderRepository、AlertManager など）の詳細なドキュメントも作成します。どの部分を深掘りしたいか教えてください。