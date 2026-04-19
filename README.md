# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買・リサーチ・監視用ユーティリティ群をまとめたモジュール群です。  
以下はコードベースの主要機能と使い方をまとめた README です。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件（依存関係）
- セットアップ手順
- 環境変数（.env）の例
- 主要スクリプトの使い方
- 運用上の注意点
- ディレクトリ構成（抜粋）

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- 銘柄選定 / ポートフォリオ構築（複数の配分アルゴリズム）
- 発注実行エンジン（本番 / ペーパートレード切替）
- リスク監視（ドローダウン、ポジション上限等）
- システム監視（プロセス生存、CPU/メモリ/ディスク、データ鮮度）
- ニュース NLP を用いた銘柄スコアリング & レジーム判定（OpenAI 利用）
- 研究用ファクター計算（DuckDB 経由）
- 運用ツール（設定ウィザード、設定検証、紙トレード検証レポート等）

設計方針として、DB 経由の永続化や外部 API 呼び出しの取り扱いは明確に分離されており、ペーパートレード時は本番 DB と分離されるようになっています。

---

## 機能一覧（主なモジュール）

- config.py / config_setup.py / validate_config.py
  - .env の自動読み込み、設定ウィザード、起動前の設定検証
- execution/
  - ExecutionEngine（発注エンジン）、OrderManager、RiskManager、Reconciler、BrokerFactory（本番・モック切替）
- monitoring/
  - SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, MonitoringDB
  - run_monitoring.py：ポーリングループで監視を継続
- portfolio/
  - 銘柄候補選定、重み算出、ポジションサイズ計算、セクター制約やレジーム乗数適用
- research/
  - ファクター計算（momentum / volatility / value）、特徴量探索（IC, forward returns 等）
- ai/
  - news_nlp（ニュースの LLM センチメントスコアリング）、regime_detector（市場レジーム判定）
- utils/
  - ロギング設定（stdout + 日次ローテーション）、プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py（ペーパートレード検証レポート生成）

---

## 前提条件（依存関係）

推奨 Python バージョン: 3.10+

主な外部パッケージ（機能に応じて必要）
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証を行う場合、任意）

インストール例（仮）:
```
pip install duckdb psutil openai pyyaml
```

（requirements.txt は付属していないため、必要に応じて上記をインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン / checkout
2. 仮想環境を作成して依存をインストール
3. .env を作成
   - 対話式ウィザードを使うのが簡単です（下記を参照）
4. 設定検証を実行して問題がないか確認
5. 必要な DB（data ディレクトリ）やログディレクトリを確認

主要コマンド例:

- 環境設定ウィザード（.env の作成/更新）
```
python -m kabusys.config_setup
```

- 設定検証（起動前チェック）
```
python -m kabusys.validate_config
# 警告も FAIL 扱いにする場合:
python -m kabusys.validate_config --strict
```

- 監視ループ起動
```
python -m kabusys.run_monitoring
```

- 実行エンジン起動（本番/ペーパーは KABUSYS_ENV で切替）
```
python -m kabusys.run_execution
```

- ペーパートレード検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```

---

## 環境変数（主なもの）

自動ロード:
- プロジェクトルートに .env / .env.local が存在すれば自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要なオプション:
- KABUSYS_ENV: 実行モード ("development", "paper_trading", "live")
  - paper_trading 時は MockBrokerClient を使用し DB は data/paper_trading.db を使います
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（"DEBUG","INFO","WARNING","ERROR","CRITICAL"）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API を使う機能で必要
- PAPER_FILL_MODE: ペーパートレードでの約定モード ("instant" | "partial" | "never" | "reject")
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

例（.env の一部）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx
PAPER_FILL_MODE=instant
```

注意: .env は絶対に Git にコミットしないでください（config_setup も同様に警告します）。

---

## 主要スクリプト / 実行方法の詳細

- python -m kabusys.config_setup
  - 対話式に .env を生成・更新します。既存の .env を読み込み、Enter で既存値を再利用できます。

- python -m kabusys.validate_config [--strict]
  - .env や config/*.yaml の存在や基本的な正当性をチェックします。PyYAML が無い場合は YAML 検証はスキップされます。
  - --strict をつけると警告も失敗として扱い exit(1) で終了します。

- python -m kabusys.run_execution
  - ExecutionEngine を起動します。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient と data/paper_trading.db に記録され、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動を停止します。
  - エンジンはスレッドで実行され、stop_requested.flag を検出すると停止します。
  - 実行中は data/execution.pid（デフォルト）に PID を書く設計になっています。

- python -m kabusys.run_monitoring
  - SystemMonitor のポーリングループを起動します（MONITOR_POLL_INTERVAL で間隔を上書き可能、デフォルト 60 秒）。
  - 監視は環境にかかわらず本番 sqlite_path を使用してログを記録します。
  - data/stop_requested.flag を検出するとループを終了します。

- python -m kabusys.tools.paper_verification_report
  - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH もしくはデフォルト data/paper_trading.db）を解析し、稼働率・約定率・レイテンシなどのレポートを出力します。

---

## 運用上の注意

- kill.flag / stop_requested.flag
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（KillSwitch は条件に応じて kill.flag を生成）。
  - 管理者が手動で停止を要求する場合は data/stop_requested.flag を作成すると run_monitoring や run_execution のループが早期終了します。

- ログ
  - ログは stdout（コンソール）と日次ローテートされるファイル（logs/<app_name>.log）に出力されます。
  - ログディレクトリの作成に失敗した場合はファイル出力をスキップしてコンソールのみになります。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等にテーブル/カラムを作成し、既存 DB に対する簡単なマイグレーション（カラム追加）を行います。

- OpenAI / API の利用
  - OpenAI を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。API 呼び出しはリトライ/バックオフが組まれており、失敗時はフェイルセーフ（スコア 0 等）で継続します。

---

## ディレクトリ構成（抜粋）

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ config_setup.py
   ├─ validate_config.py
   ├─ run_execution.py
   ├─ run_monitoring.py
   ├─ utils/
   │   ├─ __init__.py
   │   ├─ logging_setup.py
   │   └─ process_priority.py
   ├─ monitoring/
   │   ├─ monitoring_db.py
   │   ├─ monitoring_engine.py
   │   ├─ system_monitor.py
   │   ├─ trade_monitor.py            # (存在するファイル: 監視関連)
   │   ├─ risk_monitor.py
   │   ├─ kill_switch.py
   │   └─ alert_manager.py            # (アラート送信管理)
   ├─ execution/
   │   ├─ execution_engine.py
   │   ├─ order_manager.py
   │   ├─ order_repository.py
   │   ├─ broker_factory.py
   │   └─ reconciler.py
   ├─ portfolio/
   │   ├─ portfolio_builder.py
   │   ├─ position_sizing.py
   │   └─ risk_adjustment.py
   ├─ research/
   │   ├─ factor_research.py
   │   └─ feature_exploration.py
   ├─ ai/
   │   ├─ news_nlp.py
   │   └─ regime_detector.py
   └─ tools/
       └─ paper_verification_report.py
```

（実際のファイル一覧はリポジトリ全体を参照してください）

---

## トラブルシューティング（よくある質問）

- .env が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか確認。自動ロードはプロジェクトルート（.git or pyproject.toml を探索）を基準に行います。

- run_monitoring がすぐ停止する
  - data/stop_requested.flag が存在している可能性があります。停止フラグを削除して再起動してください。

- OpenAI API 呼び出しで失敗が多い
  - OPENAI_API_KEY を正しく設定しているか、レート制限やネットワークの問題を確認してください。ライブラリ側で指数バックオフが行われますが、キーの権限や残高も確認してください。

- ペーパートレードと本番の DB を明確に分けたい
  - KABUSYS_ENV=paper_trading に設定すると Execution では paper_sqlite_path（デフォルト data/paper_trading.db）が使用されます。必ず .env で設定してください。

---

必要であれば、この README をベースに「デプロイ手順」「運用手順書」「監視ランブック」などの詳細ドキュメントを作成できます。どの部分をさらに詳しく出力するか指定してください。