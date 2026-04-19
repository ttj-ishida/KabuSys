# KabuSys

日本株自動売買システムの一部モジュール群。  
このリポジトリは、注文実行エンジン、監視（モニタリング）、ポートフォリオ構築、ファクター計算、AI 補助のニュース解析などを含むコンポーネントを提供します。

> 注意: README はコードベースの主要点をまとめたものであり、実際の運用では各種 API キーや設定値を適切に管理してください。`.env` は絶対にリポジトリへコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買関連ライブラリ群です。主に以下の用途を想定しています。

- 注文実行エンジン（ExecutionEngine）とブローカークライアント（kabuステーション / モック）
- システム稼働監視（SystemMonitor / MonitoringEngine）
- リスク監視（ドローダウン・ポジション上限など）
- ポートフォリオ構築とポジションサイズ算出（等金額、スコア重み、リスクベース）
- リサーチ用ファクター計算（Momentum / Volatility / Value 等）
- AI を使ったニュースセンチメント評価（OpenAI）
- ペーパートレード検証レポート生成ツール

設計方針として、DuckDB を分析用に、SQLite を監視やペーパートレードの永続化用に使うなど、分析系と運用系 DB を分離しています。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートに基づく）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 起動前検証 CLI: python -m kabusys.validate_config
- 実行エンジン
  - run_execution: 実取引（live）、ペーパートレード（paper_trading）に対応
  - paper_trading 時は MockBrokerClient を使用し、ペーパートレード用 DB に記録
- 監視
  - run_monitoring: SystemMonitor をポーリングし system_status / risk_logs 等へ記録
  - Kill Switch: リスク条件で data/kill.flag を書き、実行エンジン停止を促す
  - 各種アラートフック（AlertManager 経由の通知を想定）
- ポートフォリオ構築
  - 候補選定、等金額/スコア重み、セクター制限、レジーム乗数
  - 単元株（lot）丸め、aggregate cap によるスケールダウン
- リサーチ
  - DuckDB を使ったファクター計算（momentum, volatility, value）
  - 特徴量探索（IC 計算、統計サマリー）
- AI（OpenAI）
  - ニュースを LLM でスコアリングして ai_scores へ保存
  - マクロニュース + ETF MA200 を組み合わせて市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発環境）

以下はローカルで動かすための基本手順例です。

1. Python 環境（3.10+ 推奨）を用意
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - 最低限必要なパッケージ:
     - duckdb, psutil, openai
   - 例:
     - pip install duckdb psutil openai
   - YAML の設定検証を使う場合は PyYAML を追加:
     - pip install PyYAML
   - 実運用向けに requirements.txt がある場合は pip install -r requirements.txt を利用してください（本リポジトリでは明示的な requirements.txt を含みません）。

3. プロジェクトルートに `.env` を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは `.env.example` 等を参考に手動で作成してください。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする: python -m kabusys.validate_config --strict

5. データディレクトリの作成（必要に応じて）
   - デフォルトでは `data/` に各種 DB / フラグ / pid ファイルを作成します。
   - 例: mkdir -p data logs

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用トークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development | paper_trading | live (デフォルト: development)
  - paper_trading: MockBrokerClient を使い `data/paper_trading.db` に記録（本番 DB と分離）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH — pid / kill フラグのパス（デフォルト data 以下）

（詳しいデフォルトや検証は `kabusys.config.Settings` を参照してください）

---

## 使い方（起動方法）

- 環境ファイルを用意
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 監視プロセスを起動
  - MONITOR_POLL_INTERVAL を変えたい場合は環境変数で上書き可能（秒）
  - 例:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - デフォルト: 60 秒間隔で SystemMonitor.check_once() を実行します。
  - 監視は常に本番用 sqlite_path を使って記録します（KABUSYS_ENV に依らない）。

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード専用 DB に記録されます。
  - 起動時に `data/kill.flag` が存在するとエンジンは起動をスキップします。
  - 実行中は pid ファイル（デフォルト data/execution.pid）を使います。停止は kill.flag を作成するか、正常に停止させてください。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能

- AI 系（OpenAI）機能
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI_API_KEY が必要。API 呼び出しは堅牢化（リトライ、フォールバック）されていますが課金・レート制限に注意してください。

- ログ
  - 全スクリプトは共通の logging 設定を利用します（kabusys.utils.logging_setup.setup_logging）。
  - ログは stdout と日次ローテートのファイル（logs/<app_name>.log）へ出力します。ログディレクトリ作成に失敗した場合はファイル出力はスキップされコンソールのみになります。

---

## 実運用上の注意点

- 本番（KABUSYS_ENV=live）では特に LINE 通知や kill flag 周りの設定を確認してください。
- .env に API キーやパスワードを平文で保存する場合は権限管理に注意してください。
- ペーパートレード DB は本番用 DB と分離されています（デフォルト: data/paper_trading.db）。
- run_monitoring は監視ログを書き続けます。停止したい場合はプロセスを終了するか、プロジェクトルートの data/stop_requested.flag を作成してください（run_monitoring と run_execution の双方が stop flag を参照します）。
- run_execution 起動前に kill flag が既に存在すると起動をスキップします。必要であれば `KILL_FLAG_CLEAR_ON_START=1` を使って自動クリアできますが、本番では推奨されません（安全策）。

---

## 主要なディレクトリ構成

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py         — 共通ログ設定
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB 層
    - system_monitor.py        — システム状態監視
    - trade_monitor.py         — 発注 / 約定監視（存在するファイルに依存）
    - risk_monitor.py          — ドローダウン・ポジション監視
    - kill_switch.py           — kill.flag 書き込みロジック
    - monitoring_engine.py     — 各モニタを束ねるエンジン
    - alert_manager.py         — （通知用インタフェース想定）
  - execution/
    - execution_engine.py      — ExecutionEngine（注文発行ループ）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py     — 候補選定 / 重み計算
    - position_sizing.py       — 株数算出 / スケール調整
    - risk_adjustment.py       — セクター制限 / レジーム乗数
  - research/
    - factor_research.py      — momentum / volatility / value
    - feature_exploration.py  — forward returns / IC / summary
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — マクロ + ETF MA200 によるレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

（上記に加えて、data/ や logs/ ディレクトリを運用環境で作成します）

---

## よく使うコマンドまとめ

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パス指定も可能

- 開発時のモジュール呼び出し例（Python REPL）
  - from kabusys.research import calc_momentum
  - calc_momentum(conn, date(2026, 4, 10))

---

## トラブルシューティング / ヒント

- ログファイルが出力されないとき:
  - LOG_DIR のディレクトリ作成に失敗している可能性があります。権限やパスを確認してください。失敗時はコンソール出力のみになります。
- OpenAI 呼び出しで失敗が多いとき:
  - OPENAI_API_KEY の設定を確認。レート制限や一時的なネットワーク障害に対しては内部でリトライが入りますが、長時間失敗する場合は API キーやネットワーク、課金状況を確認してください。
- ペーパートレードと本番 DB の混同に注意:
  - paper_trading モードでは `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用します。設定を誤ると本番 DB に記録される可能性があります。

---

## 開発・拡張のポイント

- DuckDB を分析用に使うため、research モジュールは SQL と Python の組合せで効率よく計算を行います。
- AI 関連は OpenAI のレスポンスを厳密にバリデーションし、部分失敗時にも DB の既存データを消さないようにしています（冪等性を意識）。
- 設定の自動ロードはプロジェクトルート（.git / pyproject.toml）を基準に行うため、配布後も CWD に依らず正しく動作します。

---

この README はコードベースの主要な使い方と構成をまとめたものです。追加で「デプロイ手順」「systemd ユニット例」「運用チェックリスト」などが必要であれば、それに合わせてドキュメントを追記できます。必要な内容を教えてください。