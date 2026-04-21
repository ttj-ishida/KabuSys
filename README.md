KabuSys — 日本株自動売買システム
===========================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の骨組みを提供するプロジェクトです。  
主に次の責務を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）とブローカー抽象（実口座 / ペーパートレード切替）
- 監視（Monitoring）: システム稼働状況、注文ログ、リスク監視、Kill Switch
- ポートフォリオ構築（銘柄選定、重み計算、ポジションサイズ算出）
- リサーチ（ファクター計算、将来リターン、IC 計算など）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード・検証）
- 運用補助ツール（Paper Trading 検証レポート生成 など）

主要な設計方針
- 本番・ペーパートレードは環境変数で切り替え（KABUSYS_ENV）
- DB は DuckDB（分析） と SQLite（監視 / 発注履歴 / ペーパートレード）を使用
- ロギングは統一された setup_logging を利用し、日次ローテーションを行う
- OpenAI を用いる NLP 部分は API キーを環境変数で指定、失敗時はフェイルセーフ

機能一覧
--------
- 実行エンジン（run_execution.py）
  - ブローカークライアントを抽象化し、paper_trading 環境では MockBrokerClient を利用
  - OrderManager / RiskManager / Reconciler を組み合わせて注文実行
  - 停止フラグ（data/stop_requested.flag）による安全停止、pid ファイル管理
- 監視（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス稼働、データ鮮度チェック
  - TradeMonitor: 注文滞留や約定異常の検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager（通知機構）と連携（実装を差し替えて通知先を指定可能）
- ポートフォリオ構築（portfolio パッケージ）
  - 銘柄選定、等重/スコア重み、リスク調整（セクターキャップ・レジーム乗数）
  - ポジションサイズ算出（単元株丸め、コストバッファ、aggregate cap）
- リサーチ（research パッケージ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン・IC 計算・統計サマリ
  - DuckDB を用いた SQL ベースの高速計算
- AI（ai パッケージ）
  - news_nlp: OpenAI を用いたニュースセンチメント集計 → ai_scores へ保存
  - regime_detector: ETF 1321 の MA 乖離とマクロニュースセンチメントでレジーム判定
- ツール
  - config_setup: 対話的に .env を作成・更新
  - validate_config: 起動前の設定検証（.env と config/*.yaml）
  - tools/paper_verification_report.py: ペーパートレード結果の集計・レポート
- ユーティリティ
  - logging_setup: 統一ログ設定（stdout + 日次ファイルローテーション）
  - process_priority: プロセス優先度 / CPU affinity 設定

セットアップ手順
----------------

前提
- Python 3.10 以上（Union types / | を使用）
- SQLite（標準ライブラリ）、ファイルシステム書き込み権限

推奨パッケージ（代表例）
- duckdb
- psutil
- openai
- PyYAML（config 検証用に任意）
- （必要に応じて）その他ブローカー用クライアントの依存

1) 仮想環境作成（推奨）
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2) 必要パッケージをインストール
- 例（requirements.txt がある場合）
  - pip install -r requirements.txt
- 手動例:
  - pip install duckdb psutil openai PyYAML

3) リポジトリルートでディレクトリ作成（デフォルト）
- mkdir -p data logs

4) .env の作成
- 対話式ウィザード:
  - python -m kabusys.config_setup
- もしくは .env を直接作成（.env.example を参照して必要な環境変数を設定）

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — execution 環境（development | paper_trading | live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（paper_trading 環境時使用）
- OPENAI_API_KEY — AI モジュールで必須（score_news / score_regime）
- LOG_LEVEL, LOG_DIR など

5) 設定検証（任意だが推奨）
- python -m kabusys.validate_config
- 問題があれば指摘を修正。--strict を付けると警告も失敗扱い。

使い方
------

起動スクリプト（モジュール実行）
- 監視ループ（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL で間隔秒数を変更可（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 監視は常に本番の sqlite_path を参照（監視は本番 DB に対して行う設計）
  - 強制終了: Ctrl+C または data/stop_requested.flag をプロジェクトルートに作成

- 実行エンジン（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動せず終了
  - 実行停止は data/stop_requested.flag を置くか ExecutionEngine 側の stop をトリガ

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 範囲指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定:
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI 関連（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - 呼び出し例（Python から）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="sk-...")

ログと監査
- ログ出力先: 標準では logs/ ディレクトリにアプリ名別ログ（例: logs/execution.log）
- ログレベル: 環境変数 LOG_LEVEL または setup_logging の引数で設定
- 監視結果・トレードログ等は SQLite の monitoring DB（デフォルト data/monitoring.db）に保存

停止と Kill Switch
- KillSwitch はリスク閾値に達した場合 data/kill.flag を書き込み、ExecutionEngine に停止を促す
- Execution 側は pid ファイル（data/execution.pid）や stop_requested.flag を用いて安全停止を行う
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリア（本番では推奨しない）

ディレクトリ構成
----------------

リポジトリ（src/kabusys）主要構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話的ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - execution/                — 実行エンジン関連（broker, order_manager, risk_manager 等）
  - monitoring/               — SystemMonitor / TradeMonitor / RiskMonitor / DB 層 / kill switch
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
  - portfolio/                — 銘柄選定・重み・ポジションサイズ
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/                 — ファクター計算・特徴量探索
    - factor_research.py
    - feature_exploration.py
  - ai/                       — ニュース NLP・レジーム判定
    - news_nlp.py
    - regime_detector.py
  - tools/                    — 運用支援スクリプト（paper_verification_report.py）
  - utils/
    - logging_setup.py
    - process_priority.py

補足 / 運用上の注意
------------------
- 本プロジェクトは実際の発注処理を含むため、本番環境（KABUSYS_ENV=live）での使用時は十分な検証と運用ルールを設定してください。
- .env に機密情報を含むため、絶対に VCS にコミットしないでください。
- OpenAI や外部 API を使う機能は API 使用料が発生します。テスト時はモックして実行することを推奨します。
- validate_config と config_setup を使い、起動前に必ず設定をチェックしてください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で管理（例: 0.1.0）
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（存在する場合）。

問題報告 / 貢献
----------------
- バグ報告や機能改善の提案は issue を作成してください。PR は歓迎します。README に記載の規約やテストを追加していただけるとスムーズです。

以上。この README はコードベースの主要な使い方・設計意図をまとめたものです。必要があれば運用ガイド（起動サンプル、systemd / supervisor 用ユニット、Dockerfile 例など）も追記できます。どの情報を優先して追加しますか？