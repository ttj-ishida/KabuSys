# KabuSys

日本株向けの自動売買 / 研究プラットフォーム用ライブラリ兼実行スクリプト群。  
このリポジトリは、戦略研究（DuckDB を用いたファクター計算）、ポートフォリオ構築、発注実行、監視、AI（ニュース NLP / レジーム判定）、運用ユーティリティを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような機能を提供します。

- DuckDB を用いた時系列データ処理とファクター計算（research）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定、セクター制限など）
- 実行エンジン起動スクリプト（run_execution） — 本番 / ペーパートレードの分離
- 監視サービス（run_monitoring） — システム状態・注文・リスクを定期チェックし、Kill Switch を発動
- AI モジュール（OpenAI）を用いたニュースセンチメントと市場レジーム判定
- 設定ウィザード（config_setup）と設定検証 CLI（validate_config）
- Paper Trading の検証レポート生成ツール

設計方針の一部:
- DB は DuckDB（分析）と SQLite（監視・発注ログ）を使い分ける
- 本番とペーパートレードの DB は分離（PAPER_TRADING_SQLITE_PATH）
- 簡易なフェイルセーフ（API リトライ、ログ、Kill フラグ）を備える
- ルックアヘッドバイアス回避のため、内部で date.today() 等を安易に参照しない実装

---

## 機能一覧（主なモジュール）

- kabusys.config / settings
  - 環境変数の読み込み（.env, .env.local 自動ロード）・検証ユーティリティ
- kabusys.config_setup
  - 対話式ウィザードで .env を作成/更新
- kabusys.validate_config
  - 起動前に .env や config/*.yaml の整合性をチェック
- kabusys.run_execution
  - ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBrokerClient／専用 DB を使用）
- kabusys.run_monitoring
  - SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔上書き可）
- kabusys.monitoring.*
  - system_monitor, trade_monitor, risk_monitor, monitoring_db, monitoring_engine, kill_switch, alert_manager など
- kabusys.portfolio.*
  - 銘柄選定、重み計算、ポジションサイズ計算、セクター上限、レジーム乗数
- kabusys.research.*
  - calc_momentum, calc_volatility, calc_value（DuckDB を使ったファクター計算）
  - feature_exploration: 将来リターン、IC、統計サマリー等
- kabusys.ai.*
  - news_nlp: OpenAI を用いたニュースセンチメント（ai_scores へ保存）
  - regime_detector: MA とマクロニュースで日次レジーム判定
- kabusys.tools.paper_verification_report
  - ペーパートレード DB から期間レポートを生成（稼働率・成功率・レイテンシ等）

---

## 前提 / 必要環境

- Python 3.10+
  - （コードに 3.10 の構文（X | Y typing）を使用）
- 推奨パッケージ（pip インストール）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証をする場合に任意）
- 任意:
  - J-Quants 等の外部 API トークン（運用時）
  - kabuステーション の API パスワード（リアル発注時）

例:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順（初期設定）

1. リポジトリをクローン / 配置
2. Python 仮想環境を作成して依存パッケージをインストール
3. ディレクトリ作成（ログ/DB 等。多くのスクリプトは起動時に自動作成しますが、明示的に作ることを推奨）
   - data/
   - logs/
4. 対話式ウィザードで .env を作成
```
python -m kabusys.config_setup
```
  - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - KABUSYS_ENV: development / paper_trading / live
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）や DUCKDB_PATH, SQLITE_PATH 等を指定可能
5. 設定検証（推奨）
```
python -m kabusys.validate_config
# 警告も失敗扱いにする場合:
python -m kabusys.validate_config --strict
```
6. （OpenAI を使う機能を使う場合）環境変数に OPENAI_API_KEY を設定

---

## 主な環境変数（主なもの）

- KABUSYS_ENV (development | paper_trading | live) — 実行環境
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで必要）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…、デフォルト INFO）
- LOG_DIR — ログ出力先（デフォルト logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml 基準）にある `.env` / `.env.local` を自動読み込みします。
- テストや特殊ケースでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

---

## 使い方（起動コマンドなど）

- 設定ウィザード
```
python -m kabusys.config_setup
```

- 設定検証
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- ExecutionEngine（実行エンジン）を起動
```
python -m kabusys.run_execution
```
- 動作:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に同ファイルが作られるとエンジン停止を試みます。
  - 実行時に data/execution.pid に PID を書きます（pid_file の設定参照）。

- Monitoring（システム監視）を起動
```
python -m kabusys.run_monitoring
# ポーリング間隔を環境変数で上書き
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- 動作:
  - デフォルト 60 秒ごとに SystemMonitor.check_once() を実行します。
  - 停止条件: data/stop_requested.flag の存在でループ終了。

- Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する例
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
- 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）など。基準値を満たしているか PASS/FAIL を表示します。

- AI スコアリング（ニュース NLP）
  - プログラム API: kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定して利用します。
  - DuckDB 接続（ai モジュールは DuckDB の raw_news / news_symbols / ai_scores テーブルを参照/更新します）

- レジーム判定
  - プログラム API: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB の prices_daily, raw_news, market_regime を使用し、結果を market_regime テーブルへ書き込みます。

- 監視 Kill Switch
  - Kill 条件を満たした場合、KillSwitch が data/kill.flag を書き込みます。ExecutionEngine 側でこのフラグを検知して停止する運用を想定しています。
  - kill.flag のパスは Settings.kill_flag_path で設定可能。clear() メソッドで削除可能です。

---

## ライブラリ API（抜粋）

- ポートフォリオ
  - select_candidates(buy_signals, max_positions=10)
  - calc_equal_weights(candidates)
  - calc_score_weights(candidates)
  - calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices, …)

- 研究（research）
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons)
  - calc_ic(factor_records, forward_records, factor_col, return_col)
  - factor_summary(records, columns)

- AI
  - score_news(conn, target_date, api_key=None)
  - score_regime(conn, target_date, api_key=None)  (kabusys.ai.regime_detector)

- 監視 / DB
  - monitoring_db.init_monitoring_db(sqlite_conn)
  - MonitoringDB クラス: log_system_status / log_trade_event / upsert_position / log_risk_event / upsert_dashboard / get_dashboard

- ユーティリティ
  - setup_logging(app_name="execution") — 統一的なログ初期化（console + 日次ローテーションファイル）
  - set_process_priority("high"|"normal"|"low"), set_cpu_affinity(n)

---

## 運用上の注意

- KABUSYS_ENV が `live` の場合は設定ミスが重大になるため validate_config の実行・確認を厳重に行ってください。
- .env ファイルは絶対にリポジトリへコミットしないでください（config_setup も README 内に注意書きを含めています）。
- OpenAI 呼び出しはコストがかかります。API キーの管理・レート制限に注意してください。
- run_execution/run_monitoring はデーモン化（systemd / supervisor / nohup）して運用することを想定しています。ログは logs/ に出力されます。
- 停止フラグ: data/stop_requested.flag を作成すると monitoring/execution のスクリプトが検知して終了します。Kill Switch は data/kill.flag を用います。

---

## ディレクトリ構成（主要ファイル抜粋）

プロジェクトの主要なソース配置は次の通りです（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (想定)
  - execution/
    - execution_engine.py (想定)
    - broker_factory.py (想定)
    - order_manager.py (想定)
    - order_repository.py (想定)
    - reconciler.py (想定)
    - risk_manager.py (想定)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（実ファイルは src/kabusys 以下にあります。上記はこの README に含まれる主要モジュールの一覧です。）

---

## よくある質問

Q: ペーパートレードのデータはどこに保存されますか？  
A: KABUSYS_ENV=paper_trading の場合、Settings.paper_sqlite_path（デフォルト data/paper_trading.db）に保存され、本番 SQLite（SQLITE_PATH）とは分離されます。

Q: ログはどこに出ますか？  
A: デフォルトは logs/ に app 名ごとのログファイル（例: logs/execution.log）を日次ローテーションで保存します。コンソールへも出力されます。

Q: 監視ループの間隔を変更したい  
A: 環境変数 MONITOR_POLL_INTERVAL（秒）で上書きできます（整数、1 以上）。不正値はデフォルト 60 秒にフォールバックします。

---

必要であれば、導入手順の詳細（systemd ユニット例、Dockerfile、CI 設定、テストの書き方など）を追加で作成します。どの部分を優先して詳しく書きたいか教えてください。