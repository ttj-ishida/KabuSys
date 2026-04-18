# KabuSys

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
このリポジトリには、発注/実行エンジン、監視（モニタリング）コンポーネント、ポートフォリオ構築／リスク調整ロジック、リサーチ用モジュール、AI を用いたニュース NLP / レジーム判定、そして運用支援ツール群が含まれます。

バージョン: 0.1.0

---

## 概要（Project overview）

主な責務と設計方針：

- 発注ロジック（ExecutionEngine）と監視（MonitoringEngine）を分離して実行できる。
- Paper Trading モードでは本番 DB と分離して専用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient により実際の発注を行わない。
- DuckDB を分析用データベース（prices_daily / raw_financials / raw_news 等）に使用。
- 監視データは SQLite（デフォルト: data/monitoring.db）に永続化。初期化・マイグレーションは `init_monitoring_db()` が行う。
- OpenAI API を用いたニュースセンチメント（news_nlp）やレジーム判定（regime_detector）を提供（APIキー必須）。
- 設定管理は `.env` と環境変数で行い、対話式ウィザードと検証 CLI を用意。

---

## 機能一覧（Features）

- Execution
  - ExecutionEngine（発注セッション実行。risk_manager / order_manager / reconciler 等と連携）
  - Paper Trading モード（本番 DB と完全分離）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・プロセス生存を監視しログに記録
  - TradeMonitor：滞留注文、約定異常などを検出（コード参照）
  - RiskMonitor：ドローダウンやポジション上限の監視、ダッシュボード更新・リスクログ出力
  - KillSwitch：しきい値超過時に `data/kill.flag` を書き込み ExecutionEngine を安全停止
  - MonitoringEngine：複数のモニタを束ねて定期ポーリング
- Portfolio（純粋関数）
  - 候補選定、等配分/スコア加重配分、位置サイズ計算（lot 単位丸め）
  - セクター上限適用、レジーム乗数計算
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - news_nlp: OpenAI を用いた銘柄ごとのニュースセンチメントの取得と ai_scores への書き込み
  - regime_detector: ETF 1321 の MA200 とマクロニュースの LLM 評価を合成してレジーム判定
- ツール
  - 設定ウィザード: `.env` を対話式で作成する `python -m kabusys.config_setup`
  - 設定検証: `.env` / config/*.yaml を起動前にチェックする `python -m kabusys.validate_config`
  - Paper Trading 検証レポート生成: `python -m kabusys.tools.paper_verification_report`

---

## 前提 / 必要パッケージ

（プロジェクトに requirements.txt があることを想定してください。例）

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の構文検証を行う場合）
- その他標準ライブラリのみで動作する箇所も多いです。

インストール例:
- pip install -r requirements.txt
- もしくは最低限:
  - pip install duckdb psutil

※ openai / PyYAML は利用機能に応じて導入してください。

---

## セットアップ手順（Setup）

1. レポジトリをクローンしてワークツリーへ移動
   - git clone ...
   - cd <repo_root>

2. Python 仮想環境を準備（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は主要パッケージのみ個別インストール）

4. 環境変数設定（.env）
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - またはテンプレートを編集して手動作成（下記は主なキー）:

     必須:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_kabu_password_here

     任意 / 運用:
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - LINE_CHANNEL_ACCESS_TOKEN=
     - LINE_USER_ID=
     - OPENAI_API_KEY=（AI 機能を使う場合）

   - .env は Git にコミットしないでください（config_setup も警告します）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリの作成
   - デフォルトの DB / pid / flag 保存先は ./data、ログは ./logs
   - 必要に応じて手動で作成されますが、起動スクリプトが自動作成する場合もあります。

---

## 使い方（Usage）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（実運用 / paper_trading を自動切替）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は mock broker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録。
    - 停止するにはプロセス外から `data/stop_requested.flag` を作成すると安全停止手順が走ります。
    - 実行時に PID ファイル（data/execution.pid）を出力します。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
  - 挙動:
    - sqlite（settings.sqlite_path）および duckdb へ接続し SystemMonitor を定期実行
    - stop_requested.flag を検出すると終了します
    - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存しない）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定することも可能（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH か data/paper_trading.db）

- AI モジュール（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（env OPENAI_API_KEY または引数で指定）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)

- ログ
  - logs/<app_name>.log に日次ローテーション（30日保持）
  - setup_logging() はコンソール stdout とファイル両方に出力。LOG_DIR 環境変数で変更可。

---

## 運用上の注意（Operational notes）

- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- KABUSYS_ENV の有効値:
  - development / paper_trading / live
- Paper Trading を使用する場合、DB は完全に分離されます（data/paper_trading.db）。
- Kill Switch:
  - RiskMonitor 等がしきい値を超えると `data/kill.flag` が書き込まれ、ExecutionEngine はこれを検出して停止します。
  - KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。
- MONITOR_POLL_INTERVAL に不適切な値（0 や負数）を与えるとデフォルト 60 秒にフォールバックします。
- プロセス優先度設定（set_process_priority）は psutil を利用し、OS によって挙動が異なるため管理者権限が必要な場合があります。失敗しても警告で継続します。

---

## ディレクトリ構成（Directory structure）

リポジトリ内の主要ファイルを抜粋した構成例:

- src/
  - kabusys/
    - __init__.py
    - run_execution.py                 # ExecutionEngine 起動スクリプト
    - run_monitoring.py                # SystemMonitor ポーリングループ起動スクリプト
    - config.py                        # 環境変数 / Settings 管理
    - config_setup.py                  # .env 対話式ウィザード
    - validate_config.py               # 設定検証 CLI
    - tools/
      - __init__.py
      - paper_verification_report.py   # Paper Trading 検証レポート
    - ai/
      - __init__.py
      - news_nlp.py                    # ニュース NLP（OpenAI）
      - regime_detector.py             # レジーム判定（OpenAI）
    - monitoring/
      - monitoring_db.py               # SQLite テーブル初期化 / 永続化層
      - system_monitor.py
      - trade_monitor.py               # （存在参照あり）
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py               # （存在参照あり）
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - execution/                        # 発注関連（実装ファイル群: Engine, BrokerFactory 等）
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - data/                             # 実行時生成される（例: monitoring.db, paper_trading.db, kill.flag, execution.pid）

> 注: 上記の一部ファイル（例: trade_monitor, alert_manager, execution/* の完全実装）はこの抜粋に含まれていない可能性があります。実際のファイル一覧はリポジトリルートでご確認ください。

---

## よくある操作（Examples）

- 起動前に設定を作成して検証する:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 監視をバックグラウンドで開始（例）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring &

- 実際のエンジンを起動（Paper / Live 切替は .env の KABUSYS_ENV で制御）:
  - python -m kabusys.run_execution

- Paper Trading のレポートを生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## トラブルシューティング

- DB が見つからないエラー:
  - デフォルトパス (data/*.db) が存在するか、環境変数（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を確認してください。
- OpenAI 関連のエラー:
  - OPENAI_API_KEY が設定されているか確認。API のレート制限やネットワーク障害は自動リトライロジックがあるが、完全停止や欠損に注意。
- ログファイルが作成されない:
  - logs/ ディレクトリに書き込み権限があるか確認。書き込みに失敗するとコンソール出力のみで継続します（警告が出ます）。
- プロセス優先度の設定に失敗:
  - OS や実行ユーザの権限による。警告でスキップされます。

---

## 開発者向けメモ

- 設定ファイルの自動ロード順: OS 環境 > .env.local > .env。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- monitoring_db.init_monitoring_db() は冪等（既存テーブルや後方互換のマイグレーションを行う）。
- AI モジュールはレスポンスのバリデーション・クリッピング・部分成功時の DB 保護（既存スコアの保護）に注意した実装になっています。
- リサーチモジュールは DuckDB にある prices_daily / raw_financials を参照する設計です（外部 API に依存しない）。

---

必要があれば、README にサンプル .env の完全テンプレートや、主要な CLI の出力例（サンプルログ）、あるいは開発向けの contributing / tests セクションも追加できます。どの情報を追加しますか？