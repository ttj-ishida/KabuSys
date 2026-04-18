# KabuSys

日本株自動売買システム KabuSys のコードベース README（日本語）

このリポジトリは、シンプルな自動売買エンジン・モニタリング・リサーチ・AI 補助モジュールを含むプロジェクトです。  
以下はコードベースの概要、機能、セットアップ手順、使い方、およびディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤を想定したモジュール群です。主な役割は次のとおりです。

- 実行エンジン（ExecutionEngine）を起動して注文管理・約定処理を行う（本番 / ペーパートレードをサポート）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）でシステム状態や注文状況を定期的にチェックし、必要に応じて Kill Switch を発動
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）に関する純粋関数群
- DuckDB / SQLite ベースのデータアクセス（価格データ・財務・ログ等）
- AI 補助（OpenAI を使ったニュースセンチメントや市場レジーム判定）
- 開発支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート 等）
- ログ設定・プロセス優先度設定などのユーティリティ

設計方針として、本番口座や発注 API への直接的な参照を局所化し、ペーパートレード時には本番 DB と完全分離できるようになっています。

---

## 主な機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートにある .env / .env.local）
  - 設定ウィザード（python -m kabusys.config_setup）で .env を対話的に生成
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行・監視ランタイム
  - run_execution.py: ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading では MockBrokerClient を使用し、paper DB（data/paper_trading.db）に記録
    - プロセス優先度設定、PID ファイル管理、停止フラグ監視
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視結果を SQLite（monitoring.db）へ永続化

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度
  - TradeMonitor: 発注ログや滞留注文・約定異常検出（コードベースに含まれる想定）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新・リスクログ記録
  - KillSwitch: しきい値超過時に data/kill.flag を書き込み ExecutionEngine 停止信号を発行
  - MonitoringEngine: 各 Monitor を束ねてポーリングし、アラートや Kill Switch を処理

- ポートフォリオ構築
  - 候補選定（スコア順ソート）
  - 等金額配分 / スコア加重配分
  - セクター集中抑制（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes） — 単元株丸め・利用可能現金に応じたスケーリング等を実装

- リサーチ / ファクター計算
  - momentum / volatility / value 等のファクター計算（DuckDB を用いた SQL ベース）
  - forward returns / IC（Information Coefficient） / 統計サマリ

- AI（OpenAI）連携
  - news_nlp.score_news: ニュースを LLM（gpt-4o-mini 等）で評価し ai_scores に書き込み
  - regime_detector.score_regime: ETF の MA とマクロニュースのセンチメントを合成して市場レジーム判定

- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成（稼働率、注文成功率、レイテンシ等）

- 汎用ユーティリティ
  - ロギング設定（logs/<app>.log に日次ローテーション）
  - プロセス優先度 / CPU affinity 設定
  - MonitoringDB（SQLite）テーブル定義・マイグレーションユーティリティ

---

## セットアップ手順（ローカル開発向け）

前提:
- Python >= 3.10（PEP 604 の型記法などを使用）
- SQLite は標準ライブラリに含まれます

1. リポジトリをチェックアウト
   - git clone ...; cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低依存例:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - pyyaml (設定 YAML の検証に任意で使用)
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt が用意されている場合はそれを使用してください。

4. ディレクトリ作成（ログ / データ）
   - mkdir -p data logs

5. 環境変数 (.env) を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または .env.example を参照して手動作成

6. 設定検証（起動前の必須チェック）
   - python -m kabusys.validate_config
   - --strict オプションで警告を厳格に扱えます

環境変数で特に重要なもの:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- OPENAI_API_KEY: AI 機能を使う場合に必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、paper_trading 時に使用）
- LOG_LEVEL（例: INFO / DEBUG）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔を秒で上書き可能）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env の自動ロードを無効化可能（テスト用）

---

## 使い方

以下は代表的な起動・運用手順です。

1. 設定を作成・確認
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. 監視プロセスの起動（単独）
   - python -m kabusys.run_monitoring
   - ポーリング間隔を変更する場合:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

   監視はデフォルトで data/monitoring.db（設定により変更可）へ結果を記録します。

3. 実行エンジンの起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading を環境変数に設定するとペーパートレードモードで起動し、専用の paper DB（PAPER_TRADING_SQLITE_PATH）に記録されます。

4. 停止方法
   - ExecutionEngine と Monitoring の両方が data/stop_requested.flag を監視しています（run_execution/run_monitoring 内で使用）。このファイルを作成すると監視ループとエンジンが停止します。
     - 例: touch data/stop_requested.flag
   - Kill Switch（自動停止）:
     - RiskMonitor / KillSwitch がしきい値を満たすと data/kill.flag を書き込み、ExecutionEngine 停止を誘発します。
   - 実行開始時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

5. ペーパートレード検証レポートの生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB パスは data/paper_trading.db。--db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で変更可。

6. AI モジュールの利用（プログラムから）
   - 例（ニューススコアリング）:
     - from openai import OpenAI
     - import duckdb, datetime
     - conn = duckdb.connect("data/kabusys.duckdb")
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date=datetime.date(2026,4,1), api_key="YOUR_KEY")
   - OpenAI API キーは OPENAI_API_KEY 環境変数または関数引数で渡します。

7. ログ
   - ログは logs/<app_name>.log に日次ローテーションで出力されます（app_name 例: execution, monitoring）。ログディレクトリは LOG_DIR 環境変数で上書き可能。

---

## 主要ファイル & ディレクトリ構成

（src/kabusys 以下を示します。プロジェクトルートは src/ を含む構成を想定）

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py
    - 環境変数・.env 自動ロード・Settings クラス（アプリ設定）
  - config_setup.py
    - 対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config.py
    - .env と config/*.yaml の検証 CLI（python -m kabusys.validate_config）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で制御）
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル初期化・MonitoringDB ラッパー（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
      - CPU/メモリ/ディスク/データ鮮度/プロセス生存チェック
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - kill_switch.py
      - data/kill.flag を書き込むロジック
    - monitoring_engine.py
      - 各 Monitor を束ねてポーリング・アラート連携
    - trade_monitor.py (存在は想定されるがここでは省略)
    - alert_manager.py (通知周り、省略)
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      - 実際の注文処理・リポジトリ・ブローカ抽象化（コードベースの別ファイル群）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
      - ニュースを LLM でセンチメント評価して ai_scores に書き込む
    - regime_detector.py
      - ETF MA とマクロニュースを合成して市場レジーム判定
  - tools/
    - paper_verification_report.py
      - ペーパートレードのパフォーマンス / 運用品質検証レポートを生成
  - utils/
    - logging_setup.py
      - 標準化されたログ設定（コンソール + 日次ファイルローテーション）
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定ユーティリティ

- データ・ログ
  - data/ (実行時に使用するファイル群)
    - monitoring.db（SQLite、監視ログ）
    - paper_trading.db（ペーパートレード記録）
    - kill.flag, stop_requested.flag, execution.pid 等の制御ファイル
  - logs/
    - execution.log, monitoring.log 等（TimedRotatingFileHandler による日次ローテーション）

---

## 注意事項 / 運用上のヒント

- 本番（KABUSYS_ENV=live）の場合は設定内容（特に API キーや LINE 通知設定）を必ず確認してください。validate_config は live 時に追加警告を出します。
- kill.flag / stop_requested.flag / execution.pid の扱いに注意。KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（自動クリアされるため Kill Switch 保護が解除される可能性があります）。
- OpenAI 等外部 API 呼び出しは失敗時にフェイルセーフ化している箇所が多いですが、API コスト・レイテンシの影響を考慮して運用してください。
- DuckDB/SQLite のパス設定は環境変数で変更できます。分析用 DB（DuckDB）と監視/履歴用 DB（SQLite）は役割を分離しておくと扱いやすいです。
- Python の互換性: 型注釈や | での Union 表記が使われているため Python 3.10 以上を推奨します。

---

## 参考コマンドまとめ

- 仮想環境作成
  - python -m venv .venv
  - source .venv/bin/activate

- 依存インストール
  - pip install duckdb psutil openai pyyaml

- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

必要に応じて README に記載する具体的な起動例や environment file（.env.example）・requirements.txt を追加できます。望む出力形式（英語版、より詳細な API ドキュメント、CLI 引数一覧など）があれば指示ください。