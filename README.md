KabuSys
=======

日本株向けの自動売買・リサーチ基盤（軽量なプロダクション志向）。  
本リポジトリは以下の主要コンポーネントを含みます: 注文実行エンジン、監視サブシステム、ポートフォリオ構築、因子計算、AI（ニュース NLP / レジーム判定）および運用ユーティリティ群。

プロジェクト概要
---------------
KabuSys は日本株の自動売買ワークフローを想定したモジュール群です。  
主な設計方針は以下のとおりです。

- 実行（Execution）と監視（Monitoring）を分離。監視は Execution の安全停止（Kill Switch）を担保する。
- DuckDB / SQLite をデータストアとして利用（分析用に DuckDB、ログ/監視に SQLite）。
- Paper Trading 用に本番 DB と完全分離された専用 DB を用意（KABUSYS_ENV=paper_trading）。
- OpenAI を利用したニュースセンチメント / レジーム判定機能を提供（失敗時はフェイルセーフ）。
- 設定は .env で管理し、対話式ウィザード・検証ツールを備える。

主な機能一覧
-------------
- 実行エンジン（run_execution.py）
  - BrokerClientFactory 経由でブローカークライアントを生成
  - RiskManager / OrderManager / Reconciler を組み合わせて発注を行う
  - Paper Trading モードでは MockBrokerClient を使用し data/paper_trading.db に記録

- 監視（run_monitoring.py, monitoring/）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス生存、データ鮮度の監視
  - TradeMonitor: 発注ログの整合性・滞留注文・約定異常などの検出（モジュール内）
  - RiskMonitor: ドローダウン・ポジション上限の監視、dashboard の更新
  - KillSwitch: 条件を満たした場合に data/kill.flag を書き ExecutionEngine を停止させる
  - MonitoringEngine: 各モニタを定期実行しアラート通知（AlertManager 経由）

- ポートフォリオ構築（portfolio/）
  - 候補選定・重み計算（等金額/スコア重み）
  - セクター上限適用、レジーム乗数、ポジションサイズ計算（丸め・lot 対応）

- 研究 / 因子計算（research/）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily/raw_financials を参照）
  - 将来リターン・IC（スピアマン）・統計サマリー等のユーティリティ

- AI（ai/）
  - news_nlp: OpenAI を使ったニュースの銘柄別センチメント集計と ai_scores への書き込み
  - regime_detector: MA200 乖離とマクロニュースセンチメントを合成して市場レジーム判定を行い market_regime に書き込む

- ツール
  - config_setup.py: .env の対話式作成ウィザード
  - validate_config.py: 環境変数・config/*.yaml の静的検証
  - tools/paper_verification_report.py: Paper Trading 結果の検証レポート生成

セットアップ手順
----------------

1. 必要環境
   - Python >= 3.10（| 型注釈等の利用のため）
   - システム依存ライブラリ: duckdb, psutil, openai（AI 機能利用時）、PyYAML（設定ファイル検証のため、任意）

2. パッケージのインストール（例）
   - 仮想環境作成後:
     - pip install duckdb psutil openai
     - 任意で: pip install pyyaml

   （プロジェクトに requirements.txt が無い場合は上記を参照して必要パッケージを追加してください）

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 自動読み込み:
     - config.py はプロジェクトルートの .env と .env.local を自動的にロードします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

5. データディレクトリ
   - デフォルトのデータ/ログパス:
     - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可）
     - SQLite (監視): data/monitoring.db（SQLITE_PATH）
     - Paper Trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
     - ログ: logs/（LOG_DIR で変更可能）
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

使い方
------

基本的な起動手順（本番/開発向け）:

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper DB に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - エンジンは data/execution.pid を書きます。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path を使います（環境に関わらず本番の監視 DB を参照）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定できます（--db が優先）。

- .env 関連のポイント
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - KABUSYS_ENV: development | paper_trading | live
  - PAPER_FILL_MODE: instant | partial | never | reject（paper トレード時の約定挙動）
  - OpenAI を使う機能: 環境変数 OPENAI_API_KEY を設定してください（引数経由での指定も一部 API は可能）。

運用上の注意
-------------
- Kill Switch / Stop フラグ:
  - KillSwitch は監視ロジックから data/kill.flag を書き、ExecutionEngine に停止を要求します（Execution 側は kill.flag の検出を経て安全に停止する設計）。
  - 手動で停止したい場合は data/stop_requested.flag を作成すると run_execution / run_monitoring のループが終了します。

- ログ:
  - logs/<app_name>.log に日次ローテートで出力されます（30日保持）。出力先ディレクトリの作成に失敗した場合は標準出力のみになります。

- データ鮮度とルックアヘッド:
  - AI やレジーム判定は全てルックアヘッドバイアスを避ける設計（target_date より未来のデータを参照しない）です。

ディレクトリ構成（主要ファイル）
---------------------------------

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - config.py                    — 環境変数／設定読み込み（.env 自動ロード）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成
  - ai/
    - news_nlp.py                — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py         — 市場レジーム判定（OpenAI + MA200）
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 株数決定・資金配分・丸め
    - risk_adjustment.py         — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py         — 各種因子計算（DuckDB）
    - feature_exploration.py     — 将来リターン / IC / 統計サマリ
  - monitoring/
    - monitoring_db.py           — SQLite テーブル定義・永続化ユーティリティ
    - system_monitor.py          — システム状態・データ鮮度監視
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — フラグファイルによる停止シグナル
    - monitoring_engine.py       — 各 Monitor を束ねるループ
    - （trade_monitor.py, alert_manager.py 等の補助モジュール）
  - execution/
    - （Engine, OrderManager, RiskManager, BrokerFactory 等の実装）
  - utils/
    - logging_setup.py           — 共通ロギング設定
    - process_priority.py        — プロセス優先度 / CPU affinity 設定

付録：よく使うコマンド
--------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動:
  - python -m kabusys.run_execution

- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 拡張ポイント
-----------------------
- DuckDB / SQLite スキーマは将来的な拡張やマイグレーションに備えて冪等に作成される設計です（monitoring_db.init_monitoring_db）。
- AI モジュールは OpenAI SDK の呼び出し部分をテスト時に差し替え可能なように実装されています（テスト用モック挿入を想定）。

ライセンス／貢献
----------------
README に記載がない場合はリポジトリ内の LICENSE ファイルを参照してください。貢献やバグ報告はプルリクエスト / Issue を通じてお願いします。

以上。必要であれば各モジュールの詳細な API 仕様や運用手順（例: systemd / Supervisor 用のユニットファイル、バックアップ・DB 管理方針、アラートチャンネルの設定方法等）を別ドキュメントとして作成します。どの項目を深掘りしますか？