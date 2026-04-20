KabuSys — 日本株自動売買システム
================================

この README はリポジトリ内のソースコードを元に作成した簡易ドキュメントです。  
本プロジェクトは日本株の自動売買（Execution）とそれを支える監視（Monitoring）、研究／ポートフォリオ構築、AI（ニュース NLP／レジーム判定）機能を備えたモジュール群で構成されています。

プロジェクト概要
----------------
KabuSys は以下の主要コンポーネントを含む自動売買基盤です。

- ExecutionEngine: 発注・リスク制御・注文管理を行うエンジン（本番 / ペーパートレード対応）
- Monitoring: システム状態、注文ログ、リスク監視、Kill Switch（停止フラグ）などの監視機能
- Portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制限などのポートフォリオ構築ロジック
- Research: DuckDB 上でファクター計算や特徴量探索を行う研究用モジュール
- AI: ニュースのセンチメント解析（OpenAI）や市場レジーム判定
- ユーティリティ: ロギング設定、プロセス優先度設定、設定管理（.env の読み書き）など
- ツール: Paper Trading の検証レポート生成スクリプトなど

主な機能一覧
-------------
- 実行/発注エンジン（ExecutionEngine）
  - 本番 / ペーパートレードを分離（ペーパー時は MockBrokerClient を利用）
  - リスク管理（最大ポジション比率、利用率、ドローダウン検出等）
  - 注文レポジトリ・マネージャ・再調整（Reconciler）等の構成
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセスの存否、データ鮮度チェック
  - TradeMonitor: 注文の滞留（stale）や異常約定の検出
  - RiskMonitor: ドローダウン監視、ポジション上限チェック、ダッシュボード更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止させる
  - MonitoringDB: SQLite に監視ログ（system_status, trade_logs, risk_logs, positions, dashboard）を永続化
- ポートフォリオ構築
  - 候補選定（スコア降順）、等重/スコア加重配分、リスクベース配分、単元株丸め、セクターキャップ、レジーム乗数
- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI）
  - news_nlp: raw_news をまとめて LLM に渡し、銘柄ごとの sentiment / ai_score を生成して ai_scores テーブルに書き込む
  - regime_detector: ETF(1321) の MA とマクロ記事センチメントを合成して market_regime を判定
- ツール
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL 判定とレポート出力
- 設定とヘルパー
  - config_setup: 対話式に .env を生成・更新
  - validate_config: .env や config/*.yaml の妥当性チェック
  - logging_setup: 統一的なロギング設定（console + 日次ローテートファイル）
  - process_priority: プロセス優先度や CPU affinity 設定

セットアップ手順
----------------
1. Python 環境を用意
   - Python 3.9+ を推奨
   - 仮想環境を作成してアクティベートするのが望ましい
     - 例: python -m venv .venv && source .venv/bin/activate

2. 依存パッケージのインストール（主に使用するライブラリ）
   - pip install duckdb psutil openai
   - オプション / 推奨:
     - PyYAML（config/*.yaml の検証に使用）: pip install pyyaml
   - 実際の requirements.txt が無い場合は上記を個別にインストールしてください。

3. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - 主要な環境変数（抜粋）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパー用）
     - LOG_LEVEL: INFO（デフォルト）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - PAPER_FILL_MODE（ペーパートレードの約定挙動）: instant | partial | never | reject（デフォルト: instant）
   - .env は決してリポジトリにコミットしないでください。

4. DB とディレクトリ
   - duckdb / sqlite のファイルは指定されたパスに作られます（logs/ や data/ ディレクトリは自動作成されることが多い）。
   - ログは既定で logs/<app_name>.log に出力されます（LOG_DIR 環境変数で変更可）。

使い方（主要コマンド）
--------------------
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag があれば起動せず終了します。
    - 実行時に data/stop_requested.flag が作成されるとエンジンが停止します。
    - Execution 用の PID ファイルは data/execution.pid（設定で変更可）に保存されます。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 振る舞い:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト: 60）
      - 0 以下または不正値は 60 秒へフォールバック
    - 監視は常に本番用の sqlite_path を使って監視テーブルを書き込みます（KABUSYS_ENV に依存しない）
    - Monitoring は設定された pid_file を参照してプロセス監視などを行います
    - 停止は data/stop_requested.flag の作成で行えます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / 研究モジュールの利用（Python API）
  - OpenAI を使う機能を呼ぶ前に OPENAI_API_KEY を設定してください
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - 研究関数例:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - calc_momentum(duckdb_conn, date(2026, 4, 1))

- ログ・監視
  - ログは stdout と logs/<app_name>.log（日時ローテーション）に出力されます
  - LOG_DIR 環境変数でログディレクトリを上書き可能

停止・Kill スイッチ
-------------------
- ExecutionEngine の停止トリガー:
  - KillSwitch が条件を満たすと data/kill.flag を書き込みます（ExecutionEngine 側で kill.flag の存在を検知して停止する設計）。
  - KillSwitch の評価条件は主にドローダウン（DRAWDOWN_ALERT）やポジション上限（POSITION_LIMIT）です。
- 手動停止:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して終了します。

環境変数（主なもの）
--------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパー用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（ペーパートレード約定モード: instant/partial/never/reject、デフォルト: instant）
- OPENAI_API_KEY（AI を使う場合）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（ログ出力先）
- MONITOR_POLL_INTERVAL（monitor のポーリング秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（本番で誤設定は危険: 0 推奨）

ディレクトリ構成（主要ファイル）
------------------------------
以下はリポジトリ内の主要モジュールと簡単な説明です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - config_setup.py — .env 作成用対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py — ロギング設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成と永続化 API
    - monitoring_engine.py — 複数モニタを束ねるエンジン
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文関連の監視: 別ファイル参照）※本一覧では割愛
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py —（アラート送信管理: 別モジュール）
  - execution/ （発注系コンポーネント群）
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・上限処理・単元丸め
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — ETF MA とマクロセンチメント合成によるレジーム判定

注意事項 / 運用上のポイント
-------------------------
- .env は機密情報を含むため絶対に Git 等にコミットしないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を強く推奨します。
- OpenAI API 利用には API キーと利用料金が発生します。API 呼び出しはレート制限やエラーに対するリトライ機構がありますが、運用ポリシーを検討してください。
- ペーパートレードは本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- ログディレクトリ作成に失敗するとファイルハンドラはスキップされ、標準出力のみのログになります（警告が出ます）。

開発者向けヒント
-----------------
- モジュールはできるだけ副作用を避ける設計（例: AI / 研究モジュールは DuckDB 接続を受け取る）になっています。ユニットテストでは外部依存（OpenAI など）をモックしてください。
- validate_config を使うと起動前に環境設定や config ファイルの基本的な問題を検出できます。
- Monitoring / Execution の停止は data/stop_requested.flag（プロセスループの早期停止）および data/kill.flag（KillSwitch による停止命令）で制御します。

---
この README はソースコード中の docstring とコメントに基づいて作成しています。実運用や詳細な API 仕様は該当モジュール（各 .py）内のドキュメントをご参照ください。必要であれば、特定モジュールのより詳しい README や使用例を追加で作成します。