# KabuSys

日本株向けの自動売買システムのコアライブラリおよび起動スクリプト群です。  
本リポジトリは発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、研究用ファンクション群、AIベースのニュースセンチメント評価などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を提供します。

- ExecutionEngine（発注・注文管理・リスク管理）起動スクリプト
- Monitoring（システム・トレード・リスク監視）および Kill Switch
- Paper Trading（ペーパートレード）モード（本番 DB と分離）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- リサーチ（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI モジュール（ニュースのセンチメント評価、マーケットレジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード・検証ツール）
- Tools（ペーパートレード検証レポート生成スクリプト等）

設計方針として、データベース（DuckDB/SQLite）を用いた分析と、外部 API 呼び出し（kabuステーション、J-Quants、OpenAI 等）を分離し、フェイルセーフを重視しています。

---

## 主な機能一覧

- execution
  - ExecutionEngine 起動（run_execution.py）
  - Broker クライアントの抽象化と Paper Trading 対応
  - OrderManager、OrderRepository、RiskManager、Reconciler 等のコンポーネント
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス／データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常などの検出（モジュール参照）
  - RiskMonitor: ドローダウン検出・ポジション上限監視
  - KillSwitch: Kill Flag によるエンジン停止シグナル
  - MonitoringEngine: 監視ループの統合
  - SQLite ベースの永続化（monitoring_db）
- research / portfolio
  - ファクター計算（momentum, volatility, value）
  - forward returns、IC（Spearman rank）計算
  - ポートフォリオ候補選定、等重／スコア重み、ポジションサイズ算出
  - セクターキャップ、レジーム乗数の適用
- ai
  - news_nlp: OpenAI を使った銘柄別ニュースセンチメント集計と ai_scores への書き込み
  - regime_detector: ETF MA とマクロセンチメントを合成して日次レジーム判定
- utils
  - logging_setup: コンソール + 日次ローテートログ設定
  - process_priority: プロセス優先度と CPU affinity 設定ユーティリティ
- tools
  - paper_verification_report: ペーパートレード DB を集計し検証レポートを出力

---

## 動作要件（推奨）

- Python 3.10+
- 必須 Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
- 任意 / 機能により必要
  - PyYAML（config/*.yaml の検証時）
- OS: Linux / macOS / Windows（大部分はクロスプラットフォームで動作。ただし process priority や CPU affinity は OS に依存）

必要なパッケージはプロジェクト側で requirements.txt があればそちらを使ってください。なければ手動で pip インストールしてください。例:

pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローンして作業環境を用意します。

   git clone <repo-url>
   cd <repo>

2. 仮想環境の作成（任意だが推奨）

   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール

   pip install -r requirements.txt
   # requirements.txt がない場合:
   pip install duckdb psutil openai pyyaml

4. 環境変数設定 (.env) — 対話式ウィザード

   python -m kabusys.config_setup

   ウィザードは .env を作成・更新します。少なくとも以下の必須変数を設定してください:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   その他:
   - KABUSYS_ENV (development | paper_trading | live)
   - OPENAI_API_KEY (AI 機能を使う場合)
   - DUCKDB_PATH / SQLITE_PATH など（デフォルトで data/*.db を使用）

5. 設定の検証

   python -m kabusys.validate_config
   --strict オプションをつけると警告もエラー扱いになります。

6. 初回実行前の注意
   - data ディレクトリ、logs ディレクトリは自動作成されますが、権限等で失敗する場合があります。
   - Paper Trading は本番データベースと分離され、デフォルトでは data/paper_trading.db を使用します。

---

## 重要な環境変数（代表）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 動作制御
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading モード時）
  - PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject）
  - OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1）

---

## 使い方（代表的なコマンド）

- ExecutionEngine を起動（本番/ペーパートレードは KABUSYS_ENV で制御）

  python -m kabusys.run_execution

  メモ:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します。
  - 実行中は data/execution.pid が PID ファイルとして使われます。
  - 停止は監視側の Kill Switch（data/kill.flag）により指示できます。

- Monitoring を起動（定期ポーリング）

  python -m kabusys.run_monitoring

  オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番の sqlite_path を使用します（環境にかかわらず）。

- Kill Switch（Execution 停止）を手動で発動するには:

  echo "reason" > data/kill.flag

  - KillSwitch はリスク閾値（ドローダウン等）を満たすと自動で data/kill.flag を書き込みます。
  - run_execution は起動時のクリア設定（KILL_FLAG_CLEAR_ON_START）に応じて kill.flag を削除することがあります。

- 停止フラグ（ランナーが停止するためのフラグ）

  - run_monitoring / run_execution は data/stop_requested.flag を監視して、存在するとループを終了します。
  - これを使うと優雅にプロセスを停止できます。

- Paper Trading 検証レポート

  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を明示
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- 設定ファイル検証（起動前チェック）

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

---

## ライブラリ API（簡易）

プロジェクトはモジュールとしても使用できます。代表的な関数・モジュール:

- kabusys.portfolio
  - select_candidates(...)
  - calc_equal_weights(...)
  - calc_score_weights(...)
  - calc_position_sizes(...)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date)
  - calc_ic(...)
  - factor_summary(...)

- kabusys.ai
  - score_news(conn, target_date, api_key=None)
  - score_regime(conn, target_date, api_key=None) (regime_detector モジュール)

- kabusys.monitoring
  - MonitoringDB: DB 操作ラッパー（log_system_status / log_trade_event / upsert_dashboard 等）
  - MonitoringEngine: 統合監視ループ（テスト用 run_once あり）
  - KillSwitch, RiskMonitor, SystemMonitor, TradeMonitor

- utils
  - setup_logging(app_name, log_dir, level)
  - set_process_priority(level), set_cpu_affinity(n)

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / .env ロード・Settings クラス
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前の設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor のポーリングループ起動スクリプト

サブパッケージ（主要ファイル）
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI 呼び出しと ai_scores への書込み）
  - regime_detector.py      — レジーム判定
- monitoring/
  - monitoring_db.py        — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py       — システム監視（CPU/メモリ/ディスク/データ鮮度/プロセス）
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag 書込みユーティリティ
  - monitoring_engine.py    — 各 Monitor を束ねるランナー
  - alert_manager.py        — （アラート送信管理: 実装参照）
  - trade_monitor.py        — （注文監視ロジック: 実装参照）
- portfolio/
  - portfolio_builder.py    — 候補選定 / 重み計算
  - position_sizing.py      — 株数決定ロジック
  - risk_adjustment.py      — セクターキャップ・レジーム乗数
- research/
  - factor_research.py      — ファクター計算（momentum/volatility/value）
  - feature_exploration.py  — forward returns / IC / summary
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py        — ロギング初期化ユーティリティ
  - process_priority.py     — プロセス優先度・CPU affinity
  - その他ユーティリティ

プロジェクトルート（外部）
- data/                     — デフォルト DB / PID / フラグ保存場所
- logs/                     — デフォルトログ保存先
- config/                   — config YAML（system_config.yaml 等。validate_config で参照）

---

## 運用上の注意点 / トラブルシューティング

- DB マイグレーションは monitoring_db.init_monitoring_db が冪等に実行します。実行時にテーブル・カラムを自動作成します。
- run_monitoring は Settings.env にかかわらず監視用 sqlite_path（本番）を使用します。Paper Trading データは paper_sqlite_path に分離されます。
- OpenAI を用いる機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必要です。無い場合は ValueError を送出する箇所があります。AI 呼び出しはリトライロジックを備えていますが、API 利用制限や料金に注意してください。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗するとコンソール出力のみになります。
- Kill Switch / stop flag の取り扱いには注意してください。特に本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 1 にするのは危険です（自動クリアしないことを推奨）。

---

## 参考コマンドまとめ

- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

この README は現状のコードベース（主要モジュール）に基づいて作成しています。個々の設定や Broker 実装、運用手順は導入環境に合わせて調整してください。必要であれば、導入手順の自動化（systemd ユニット、Docker コンテナ化、CI/CD スクリプト等）についても別途ドキュメント化できます。