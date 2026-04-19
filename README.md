KabuSys — 日本株自動売買システム
=================================

このリポジトリは、日本株向けの自動売買システム（KabuSys）の主要コンポーネント群を含みます。  
本 README はコードベース（src/kabusys 以下）を対象に、概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
----------------
KabuSys は、シグナル生成 → ポートフォリオ構成 → 発注（Execution） → 監視（Monitoring） → レポート／リサーチまでを含む一連の自動売買基盤のプロジェクトです。主要な方針として次を採ります：

- 本番／ペーパートレードの分離（paper_trading 環境では MockBroker を利用し DB も分離）
- DuckDB を分析用 DB、SQLite を監視／トランザクションログ用に使用
- AI（OpenAI）を用いたニュース NLP / レジーム判定をオプションで実行可能
- ログは一元化（コンソール + 日次ローテーションファイル）
- モニタリングと Kill Switch による自動停止・アラート機構

主な機能一覧
------------
- 実行関連
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの切替（本番 / Mock）
  - 注文管理（OrderManager / OrderRepository）
  - リスク管理（RiskManager / Reconciler）

- 監視関連
  - SystemMonitor: CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - TradeMonitor: 発注・約定ログの監視（滞留注文・異常約定など）
  - RiskMonitor: ドローダウン・保有数上限監視
  - KillSwitch: 条件に応じた停止フラグ書き込み（data/kill.flag）
  - MonitoringEngine: 各監視をまとめて定期実行
  - 監視ログ永続化: monitoring_db.py（SQLite 用テーブル定義・操作ラッパ）

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等金額 / スコア加重配分（calc_equal_weights, calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ適用、レジーム乗数（apply_sector_cap, calc_regime_multiplier）

- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン、IC（Information Coefficient）、統計サマリー等の解析ユーティリティ

- AI（オプション）
  - ニュースを LLM（OpenAI）でセンチメント評価し ai_scores に格納（news_nlp）
  - マクロニュース + MA 指標で市場レジーム判定（regime_detector）

- 運用ユーティリティ
  - .env 設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
  - ログ設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）

セットアップ手順
----------------

1. Python 環境準備
   - Python 3.9+ を推奨
   - 仮想環境を作成・有効化（例: python -m venv .venv; source .venv/bin/activate）

2. 依存パッケージのインストール（代表例）
   - duckdb
   - psutil
   - openai
   - PyYAML（config ファイル検証オプション用）
   例:
     pip install duckdb psutil openai PyYAML

   （本リポジトリに requirements.txt がない場合は上記をインストールしてください）

3. プロジェクトルートに data/ と logs/ ディレクトリを作成（多くは自動作成されますが、権限設定の確認を推奨）
   - mkdir -p data logs

4. .env の作成
   - 対話式ウィザードで作成する：
     python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成
   - 重要な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（例: INFO）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

使い方（実行例）
----------------

- ExecutionEngine を起動（デフォルトはローカル / development）
  - 本番モードで起動する場合は .env の KABUSYS_ENV を live に設定してから起動してください
  - ペーパートレード（MockBroker）を使う例:
      KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 通常（環境変数で設定済み）:
      python -m kabusys.run_execution

  特記事項:
  - run_execution は data/stop_requested.flag を監視し、存在しれば Engine を停止します。
  - ペーパートレード時は専用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込み、本番 DB と分離します。
  - 起動時に process priority を "high" に設定します（set_process_priority）。

- Monitoring を起動
    python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path（Settings.sqlite_path）を使用します（監視は本番 DB を対象にするため）。
  - 外部停止（手動）: data/stop_requested.flag を作成すると監視ループは終了します。

- Kill Switch（自動停止）の概要
  - RiskMonitor 等が条件を満たすと KillSwitch が data/kill.flag に理由を書き込みます。
  - ExecutionEngine は kill.flag の存在を察知して停止を行います（起動オプション KILL_FLAG_CLEAR_ON_START=1 に注意 — 本番では 0 推奨）。

- Paper Trading 検証レポート
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルパスを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- 設定検証（起動前）
    python -m kabusys.validate_config [--strict]

主要環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" 有効、0 デフォルト）

ログ
----
- logging_setup.setup_logging を通じて全コンポーネントで統一的にログ出力します。
- 出力先:
  - コンソール（stdout）
  - ファイル: logs/<app_name>.log（日次ローテーション、30日分保持）
- LOG_LEVEL は環境変数または setup_logging 引数で制御可能

ディレクトリ構成（src/kabusys ベース）
------------------------------------

下記は主要モジュールと役割の一覧（実際のソースは src/kabusys 以下にあります）。

- src/kabusys/
  - __init__.py                — パッケージ初期化、バージョン定義
  - config.py                  — Settings（環境変数・.env 自動ロード・検証ヘルパ）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前の設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py       — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py         — SQLite 監視テーブルの定義と DB ラッパ
    - system_monitor.py        — システム / データ鮮度監視
    - trade_monitor.py         — (参照) 注文ログ監視（ファイルに未掲の実装参照用）
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みユーティリティ
    - monitoring_engine.py     — 各 Monitor を束ねる実行エンジン
    - alert_manager.py         — (参照) アラート通知管理（LINE 等）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数算出（リスク制限・単元丸め）
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - research/
    - factor_research.py       — ファクター計算（momentum, volatility, value）
    - feature_exploration.py   — 将来リターン、IC、統計サマリー
  - utils/
    - logging_setup.py         — ロギング初期化ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/                 — ExecutionEngine / OrderManager / RiskManager 等（実行断片）
  - data/                      — データパイプライン / DuckDB 接続等（参照実装）

注意事項 / 運用上のポイント
-------------------------
- monitoring はデフォルトで production の sqlite_path（Settings.sqlite_path）を使います。監視は本番 DB を参照する想定です。
- run_execution は KABUSYS_ENV=paper_trading の場合、MockBroker + 専用 DB（PAPER_TRADING_SQLITE_PATH）を使い、本番 DB と完全に分離します。
- Kill Switch と手動停止:
  - 自動的に Kill Switch をトリガするのは RiskMonitor 等（monitoring 側）
  - 手動停止は data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して終了します
  - run_execution は起動時に data/execution.pid を使用（PID ファイル）
- OpenAI を使う機能は API キーが必要。API 呼び出しはリトライ・バックオフを備え、失敗時はフェイルセーフ（スコアを 0 にする等）で動作します。
- .env の自動ロード:
  - デフォルトでプロジェクトルートの .env と .env.local を読み込み（OS 環境変数を保護）
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

開発／拡張のヒント
------------------
- DuckDB は分析向けテーブル（prices_daily, raw_financials, raw_news など）を参照する想定です。データ投入パイプラインは別モジュール（kabusys.data.pipeline 等）で実装します。
- AI 周りはテストや開発のために _call_openai_api をモック可能に設計してあります（unittest.mock.patch 等）。
- ロギングは一元化されているため、アプリ名（execution / monitoring / monitoring など）を渡してログファイル分離が可能です。

ライセンス・貢献
----------------
本 README にライセンス情報は含めていません。実際の公開／配布時は LICENSE ファイルを追加してください。貢献は Pull Request を通じて受け付けてください。

補足（よく使うコマンドまとめ）
-------------------------
- .env を生成: python -m kabusys.config_setup
- 設定検証:  python -m kabusys.validate_config [--strict]
- Execution 起動:  python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- 開発用に環境変数指定例:
    KABUSYS_ENV=paper_trading MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

---

不明点や README に追加してほしい情報（例: サンプル .env、依存関係の明細、DB スキーマの詳細、実行フロー図など）があれば教えてください。必要に応じて追記・調整します。