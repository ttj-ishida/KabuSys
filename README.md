# KabuSys

日本株自動売買システムのパッケージ（ドキュメント版 README）。  
このリポジトリは戦略・発注・監視・リサーチ・AI 補助（ニュース NLP / レジーム判定）などを含むモジュール群を提供します。

以下はコードベース（src/kabusys）から作成した README です。

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動スクリプト・ツール）
- 環境変数一覧（主要）
- ファイル・ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買システムのコアライブラリ群です。
- 戦略（ファクター計算・特徴量解析）、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視システム（Monitoring）、および AI を用いたニュースセンチメントや市場レジーム判定などを含みます。
- データ永続化は主に DuckDB（時系列・リサーチ用）と SQLite（監視・発注ログ用）を利用します。
- モジュールはテスト可能な純粋関数と、起動用スクリプトによって構成されています。

主な機能
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカーファクトリ（実運用 / ペーパートレードの切替）
  - 注文管理 / リスク管理 / 照合（reconciler）機能
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使用し、paper_trading DB に記録して本番 DB と分離
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine（ポーリング）
  - Kill Switch（しきい値超過で data/kill.flag を作成し ExecutionEngine に停止指示）
  - 監視結果の永続化（SQLite: monitoring.db）
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - DuckDB を使った高速集計
- Portfolio construction
  - 候補選定、重み付け、ポジションサイズ計算、セクター上限適用、レジーム乗数
- AI 補助
  - ニュース NLP（OpenAI による銘柄別センチメントスコアリング）
  - 市場レジーム判定（ETF MA とマクロセンチメントの組合せ）
- ユーティリティ
  - ログ設定ユーティリティ（統一的な Stream + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - .env ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）
- ツール
  - paper_verification_report.py: ペーパートレード DB を解析して検証レポート出力

セットアップ手順（ローカル開発向け）
1. Python 環境
   - 推奨: Python 3.10 以上
   - 仮想環境を作成して有効化することを推奨します。

2. 依存パッケージ（例）
   - duckdb
   - psutil
   - openai
   - PyYAML （config 検証で利用）
   - その他プロジェクトで必要なライブラリがあれば requirements.txt を参照（存在する場合）。
   - 例:
     pip install duckdb psutil openai PyYAML

3. .env の初期作成（対話式ウィザード）
   - 実行:
     python -m kabusys.config_setup
   - 必須値（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 本番稼働時は KABUSYS_ENV を適切に設定（development / paper_trading / live）

4. 設定検証
   - 実行:
     python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

5. データディレクトリ
   - デフォルトで data/ 以下に DB や pid/flag などを置きます。必要なら .env でパスを変更してください。
   - ログは logs/ に出力されます（ログディレクトリは環境変数 LOG_DIR で変更可能）。

使い方（起動スクリプト・ツール）
- 実行スクリプト一覧（いずれも package をモジュールとして実行できます）

1) ExecutionEngine を起動（発注エンジン）
   - 実行:
     python -m kabusys.run_execution
   - 特記事項:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録します。
     - 起動時、data/stop_requested.flag が存在する場合は起動せず終了します。
     - 起動中に stop flag が書き込まれるとエンジンを停止します。
     - 実行中は data/execution.pid（デフォルト）に PID を出力することを想定しています。

2) Monitoring を起動（ポーリング監視）
   - 実行:
     python -m kabusys.run_monitoring
   - 環境変数:
     - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。
   - 特記事項:
     - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（デフォルト data/monitoring.db）を使用します（監視は一貫した DB に記録するため）。
     - 停止は data/stop_requested.flag を作成することで行います（スクリプトはこのフラグを監視して終了します）。

3) 設定ウィザード
   - 実行:
     python -m kabusys.config_setup

4) 設定検証
   - 実行:
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict

5) Paper Trading 検証レポート
   - 実行:
     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルトの DB: PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db

6) AI / リサーチ機能（ライブラリとして利用）
   - ニューススコアリング:
     from kabusys.ai.news_nlp import score_news
     score_news(duckdb_conn, target_date, api_key="...")

   - レジーム判定:
     from kabusys.ai.regime_detector import score_regime
     score_regime(duckdb_conn, target_date, api_key="...")

   - Research（ファクター等）:
     from kabusys.research import calc_momentum, calc_volatility, calc_value

環境変数（主要）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- DB / ファイルパス
  - DUCKDB_PATH: DuckDB データファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: 実行エンジン PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）

- ログ / 実行挙動
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
  - MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
  - OPENAI_API_KEY: OpenAI 呼び出し用 API キー（ai モジュールで使用）

- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

ファイル・ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理（自動 .env ロード含む）
  - config_setup.py               — .env ウィザード（対話式）
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（テーブル作成 / CRUD ラッパー）
    - system_monitor.py           — システム状態監視
    - trade_monitor.py            — （TradeMonitor 実装ファイル）
    - risk_monitor.py             — ドローダウン / ポジション上限監視
    - monitoring_engine.py        — 各 Monitor を束ねるエンジン
    - kill_switch.py              — kill.flag 書き込みロジック
    - alert_manager.py            — 通知管理（LINE 等） ※実装参照
  - execution/
    - execution_engine.py         — ExecutionEngine 本体（発注セッション管理）
    - broker_factory.py           — ブローカークライアント生成
    - order_manager.py            — 注文管理
    - order_repository.py         — 注文永続化（SQLite 等）
    - reconciler.py               — 注文照合
    - risk_manager.py             — 発注前リスク制御
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み付け
    - position_sizing.py          — 株数計算・スケーリング
    - risk_adjustment.py          — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py          — ファクター計算（momentum, volatility, value）
    - feature_exploration.py      — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py          — レジーム判定（MA + マクロセンチメント）
  - data/ (実行時に作成されることが多い)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper trading モード)
    - stop_requested.flag / kill.flag / execution.pid などの制御ファイル
  - logs/（デフォルトログディレクトリ）

運用上の注意
- 本番環境（KABUSYS_ENV=live）では特に .env の管理（機密情報の保護）と kill flag の取り扱いに注意してください。
- validate_config で基本的な設定ミスは事前に検出できます。--strict オプションを利用すると警告も失敗扱いになります。
- Monitoring は監視データを SQLite に書きます。監視は常に本番用の sqlite_path を使用する設計になっています（環境に依らず一貫した監視 DB を使うため）。
- OpenAI API を利用する機能は API キーの管理・コストに注意してください。API エラー時はフォールバックロジックが組み込まれていますが、期待する精度を得るためにモニタリングが必要です。

拡張ポイント（将来の改善候補）
- 銘柄ごとの lot_size や手数料モデルの外部化（stocks マスタ化）
- より詳細な監視アラートハンドラ（Slack / PagerDuty など）
- 単体テスト・統合テストの整備（CI 連携）
- ドキュメント化（各モジュールの API 仕様書）

ライセンス / 貢献
- 本リポジトリに LICENSE ファイルがあればそちらを参照してください。貢献はプルリクエストを歓迎します。

--- 
以上。必要であれば、README にサンプル .env テンプレートや具体的なコマンド（systemd/circus/pm2 用の起動例、コンテナ化手順など）を追記できます。どの情報を追加しますか？