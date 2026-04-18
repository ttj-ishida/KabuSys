# KabuSys

日本株向け自動売買システム "KabuSys" のリポジトリ（簡易ドキュメント）です。  
この README はコードベースから抽出した使い方・セットアップ手順・ディレクトリ構成などをまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買（ExecutionEngine）と監視（Monitoring）／研究（Research）／ポートフォリオ構築（Portfolio）機能を備えたシステムです。  
主な設計要点：

- Execution（発注）と Monitoring（監視）は分離されたプロセスで動作
- Paper Trading（ペーパートレード）モードをサポートし、本番 DB と分離
- DuckDB を使ったデータ分析（prices_daily / raw_financials 等）
- OpenAI を利用したニュース NLP（sentiment）およびレジーム判定（オプション）
- ログはコンソール＋日次ローテートファイルで出力
- 設定は .env により管理。対話式ウィザード / 検証ツールあり

バージョン: 0.1.0（パッケージの __version__ より）

---

## 機能一覧

- 実行（Execution）
  - ExecutionEngine による注文発行（本番／ペーパートレードに対応）
  - BrokerClientFactory によるブローカークライアント切替（paper_trading では Mock を利用）
  - OrderManager / OrderRepository / RiskManager / Reconciler 等で注文管理・リスク管理を実装

- 監視（Monitoring）
  - SystemMonitor: CPU / Memory / Disk / プロセス生存チェック、データ鮮度チェック
  - TradeMonitor: 発注ログや滞留注文、約定異常などの検出（ログ永続化）
  - RiskMonitor: ドローダウン・ポジション上限等の監視とアラート記録
  - KillSwitch: 条件を満たした際に data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 上記モニタを束ねて定期実行

- ポートフォリオ構築（Portfolio）
  - 候補選定 / 等ウェイト・スコア重み配分 / ポジションサイズ計算（lot 単位丸め）
  - セクターキャップ・レジーム乗数適用等のリスク調整

- 研究（Research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC（情報係数）計算、統計サマリー等（DuckDB による計算）

- AI（任意）
  - news_nlp: OpenAI を使ったニュースセンチメントスコア算出（ai_scores テーブルへ登録）
  - regime_detector: MA200 とマクロニュースセンチメントを合成して市場レジームを判定、market_regime に書き込み

- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 環境変数 / config/*.yaml の事前検証 CLI
  - paper_verification_report: ペーパートレード DB から集計レポートを生成

- ユーティリティ
  - logging_setup: 統一的なロギング設定（stdout + 日次ローテーション）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10 以降を推奨（typing の | ユースから）
- SQLite を使用（標準ライブラリ）
- DuckDB、psutil、openai 等は外部依存

1. リポジトリをクローンし作業ディレクトリへ移動

   git clone <repo-url>
   cd <repo-root>

2. 仮想環境の作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール

   pip install duckdb psutil openai

   追加（任意・検証用）:
   - PyYAML（config/*.yaml を詳細検証したい場合）: pip install pyyaml

   （プロダクション用の requirements.txt がある場合はそれを使ってください）

4. 初期設定（.env の作成）
   - 対話式ウィザード:

     python -m kabusys.config_setup

     ウィザードは .env を生成します。J-Quants トークンや kabuステーション API パスワード等の入力が必要です。

   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

   - 代表的な環境変数:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - LOG_LEVEL
     - OPENAI_API_KEY（AI 機能を使う場合）

5. 設定検証（起動前チェック）

   python -m kabusys.validate_config
   # 警告も厳密に扱いたい場合:
   python -m kabusys.validate_config --strict

6. データディレクトリ / ログディレクトリ
   - ログ: デフォルトは logs/
   - データ: デフォルトは data/
   多くのモジュールは起動時にディレクトリを作成しますが、validate_config で事前に警告を確認してください。

---

## 使い方（主要コマンド・API）

CLI 起動スクリプト（モジュール実行）:

- ExecutionEngine（発注プロセスを起動）

  python -m kabusys.run_execution

  概要:
  - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し、データは data/paper_trading.db に保存されます。
  - プロセスは data/execution.pid を作成します。
  - data/stop_requested.flag が存在すると起動・ループを停止します。

- Monitoring（監視ループを起動）

  python -m kabusys.run_monitoring

  概要:
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可。デフォルト 60 秒。
  - 監視は実行環境にかかわらず本番（settings.sqlite_path）を参照して監視ログを記録します。
  - 停止は data/stop_requested.flag の検出で行います。

- 設定ウィザード

  python -m kabusys.config_setup

- 設定検証

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（ツール）

  python -m kabusys.tools.paper_verification_report
  # 期間を指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

主なライブラリ API（Python から直接利用する場合）:

- ポートフォリオ
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

- 研究（Research）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - これらは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、prices_daily / raw_financials を参照して計算します。

- AI（ニュース・レジーム）
  - from kabusys.ai import score_news
    - DuckDB 接続と target_date を渡してニュースセンチメントを ai_scores テーブルへ保存
    - OPENAI_API_KEY（または api_key 引数）が必要
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへ判定結果を保存

ログ設定ユーティリティ:

- from kabusys.utils.logging_setup import setup_logging
  - 起動スクリプトは内部で setup_logging(app_name="execution" | "monitoring") を呼び出して統一的なログ出力を行います。

プロセス優先度ユーティリティ:

- from kabusys.utils.process_priority import set_process_priority
  - 引数: "high" | "normal" | "low"

停止／Kill Switch 関連:

- KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）にフラグを書き込み ExecutionEngine に停止を促します。Monitoring が自動的に評価・書き込みします。

環境変数の一部（まとめ）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (例: data/kabusys.duckdb)
- SQLITE_PATH (例: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
- OPENAI_API_KEY (AI 機能で使用)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔秒、デフォルト 60)
- PAPER_FILL_MODE (paper_trading の約定モード: instant | partial | never | reject)

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要な Python モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト

  - execution/                — 発注ロジック（OrderManager 等: リポジトリに一部実装）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...（その他）

  - monitoring/
    - monitoring_db.py         — SQLite スキーマ・永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - ...（その他）

  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数・資金配分
    - risk_adjustment.py       — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py       — momentum / value / volatility ファクター計算
    - feature_exploration.py   — forward returns / IC / summary
    - __init__.py

  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）で ai_scores 更新
    - regime_detector.py       — レジーム判定（MA200 + マクロセンチメント）
    - __init__.py

  - data/                     — 既定のデータ格納先（実行時に作成される）
    - monitoring.db (SQLITE_PATH のデフォルト)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH のデフォルト)

  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成ツール

  - utils/
    - logging_setup.py         — ロギング設定ユーティリティ
    - process_priority.py      — プロセス優先度設定ユーティリティ
    - __init__.py

ログ出力:
- logs/<app_name>.log（デフォルト daily rotation, 30 日保持）

データファイル / フラグ:
- data/execution.pid
- data/stop_requested.flag
- data/kill.flag

---

## 注意事項 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）を使う場合は特に設定値（API トークン・LINE 通知等）を慎重に確認してください。validate_config に本番向けガードがあります。
- .env は機密情報を含むため Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。
- OpenAI 関連機能は API キーが必要で、API コストや呼び出し制限に注意して運用してください。失敗時は fail-safe（0.0 フォールバック）で継続する設計です。
- paper_trading モードは本番 DB と分離されます。実際の発注を行う `live` モードは十分な確認が取れてから運用してください。
- ログディレクトリの作成に失敗した場合、ログはコンソールのみとなります。起動時のログ出力や validate_config の警告を確認してください。

---

## サンプル .env（最小例）

以下は最小限の .env の例（実際の値はご自身のものに置き換えてください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

以上がこのコードベースの README 相当の概要です。必要であれば以下のような追加ドキュメントを作成できます：

- 各サブモジュール（execution, monitoring, ai, research）の詳細設計ドキュメント
- API リファレンス（関数・クラスの使用例）
- デプロイ手順（systemd / Docker / k8s 用の設定例）
- テスト運用手順（ユニットテスト・統合テストの実行方法）

どれを優先して作成しましょうか？