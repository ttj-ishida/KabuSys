# KabuSys

日本株向けの自動売買システム向けユーティリティ群およびライブラリ群（リサーチ・ポートフォリオ構築・監視・実行補助など）。  
このリポジトリはコア関数群をモジュール化しており、ExecutionEngine / Monitoring などのランタイムスクリプト、AI を使ったニュースセンチメントやレジーム判定、ポートフォリオ構築ロジック等を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件
- セットアップ手順
- 環境変数 / .env の説明（主なもの）
- 実行方法（コマンド例）
- 監視・停止の仕組み（kill flag 等）
- ディレクトリ構成（主要ファイルの説明）
- 備考 / 注意点

---

## プロジェクト概要

KabuSys は以下の役割を分離したモジュール群を提供します。

- データ分析 / ファクター計算（DuckDB を想定）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
- Execution エンジン起動補助（本番 / ペーパートレード分離）
- 監視（システム状態、注文滞留、ドローダウン監視、アラート送信）
- AI（OpenAI を用いたニュースセンチメント、レジーム判定）
- CLI ユーティリティ（.env ウィザード、設定検証、レポート出力）

設計方針の一部：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV により切替）
- ルックアヘッドバイアスを防ぐため日付参照に注意（target_date を引数で与える）
- フェイルセーフ：AI 呼び出しや外部 API 失敗時は安全にフォールバックする

---

## 主な機能一覧

- 環境設定ウィザード（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
- Execution 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の際は MockBroker を使用し、専用 DB に記録
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - 定期ポーリングで system/trade/risk の監視を実行
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き
- 監視永続化（SQLite 用の monitoring_db）
- AlertManager（LINE Push 通知、クールダウン管理）
- KillSwitch（ドローダウン等で kill.flag を書き Execution 停止）
- Paper Trading 検証レポート出力ツール（kabusys.tools.paper_verification_report）
- AI モジュール
  - kabusys.ai.score_news: ニュースを LLM で評価し ai_scores に書き込む
  - kabusys.ai.regime_detector: マクロ + ETF MA200 による市場レジーム判定
- Research（ファクター計算、将来リターン、IC 計算等）
- Portfolio（候補選定、重み付け、ポジションサイズ算出、セクター制限）

---

## 必要条件

- Python 3.10+
- 推奨パッケージ（機能に応じて必要）:
  - duckdb
  - psutil
  - openai
  - requests
  - PyYAML（設定 YAML 検証時）
- OS: Linux / macOS / Windows（process priority の挙動はプラットフォーム依存、権限により設定失敗する場合あり）

実際のインストールはプロジェクト側の requirements.txt があればそれを使ってください。無ければ最低限上記パッケージを入れてください。

---

## セットアップ手順

1. リポジトリをクローン（または展開）しプロジェクトルートに移動
2. 仮想環境を作成・有効化（例: python -m venv .venv）
3. パッケージをインストール
   - 例:
     pip install duckdb psutil openai requests PyYAML
4. 環境変数設定（.env を作成）
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - もしくは .env を手動作成（下記「環境変数」参照）
5. 設定検証:
   python -m kabusys.validate_config
   - 警告を厳密に扱う場合は --strict を付ける
6. DB・data ディレクトリを作成（必要に応じて）
   - デフォルト DB パス: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db
   - run_monitoring/run_execution 実行時に自動的にファイルが作られることがあります（親ディレクトリがない場合警告）

---

## 環境変数 / .env（主なもの）

自動読み込み:
- プロジェクトルートに .git または pyproject.toml があれば、起動時に .env（次に .env.local）からロードされます。OS 環境変数は上書きされません（.env.local は override=True だが protected により OS 環境変数は保護）。

主要変数とデフォルト:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- KABU_API_BASE_URL: http://localhost:18080/kabusapi
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0 | 1（本番では 0 推奨）
- OPENAI_API_KEY: OpenAI を使う機能で必要（ai.score_news / score_regime）

サンプル .env（部分）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...
PAPER_FILL_MODE=instant
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

注意:
- .env は絶対に公開リポジトリにコミットしないこと（config_setup.py のヘッダにも明示）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化できます（テスト用途）。

---

## 実行方法（主要コマンド）

- 環境設定ウィザード（.env 作成 / 更新）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution エンジン起動（スクリプト起動）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録して本番 DB とは分離します。
  - 実行開始前に data/stop_requested.flag が存在する場合は起動しません（停止理由があるため）。
  - 実行中は data/execution.pid に PID を書く想定（設定で上書き可能）。

- Monitoring 起動（ポーリングループ）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は Settings.sqlite_path（本番 DB）を常に使用します（KABUSYS_ENV に依存しない）。
  - stop 条件として data/stop_requested.flag の存在を監視します。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを指定可能（省略時は PAPER_TRADING_SQLITE_PATH もしくは data/paper_trading.db）

- AI 機能（プログラム内呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.score_regime(conn, target_date, api_key=None)
  - これらは duckdb 接続を渡して使用します。api_key を None にすると環境変数 OPENAI_API_KEY が使われます。

---

## 監視・停止の仕組み（Kill Switch 等）

- KillSwitch:
  - 特定のリスク条件（ドローダウン超過、ポジション数超過など）を満たすと data/kill.flag に理由を書き込みます。ExecutionEngine はこのフラグを検出して停止します。
  - KillSwitch.clear() でフラグを削除できます（設定 KILL_FLAG_CLEAR_ON_START に基づく自動クリアの有無に注意）。

- stop フラグ:
  - run_execution/run_monitoring は両方ともプロジェクトの data/stop_requested.flag を監視し、存在する場合は安全にループを終了します（運用停止時に利用）。

- PID ファイル:
  - Execution 起動時に PID ファイルを書き、監視プロセスはその PID を確認してプロセス生存チェックを行います。stale PID を検出した場合はローカルファイルを除去してログに記録します。

---

## DB / マイグレーション

- 監視用 SQLite（monitoring_db.init_monitoring_db）:
  - 起動時に必要なテーブル・インデックスを冪等に作成します。
  - 既存 DB に不足カラム（peak_value, latency_ms 等）がある場合は ALTER TABLE で追加する簡易マイグレーション処理を行います。

- DuckDB:
  - 分析 / ファクター計算用。paths やテーブルはコード内の SQL から参照されます（prices_daily, raw_financials, raw_news 等）。

---

## ディレクトリ構成（主要ファイルの説明）

（src/kabusys 内を想定）

- __init__.py
  - パッケージ定義、バージョン

- config.py
  - Settings クラス。環境変数読み込み・検証・パス解決等を行う。
  - 自動 .env ロードロジックあり（プロジェクトルートを基準に .env / .env.local を読み込み）。

- config_setup.py
  - .env を対話的に生成・更新するウィザード。

- validate_config.py
  - 起動前に環境変数や config/*.yaml の存在・整合性をチェックする CLI。

- run_execution.py
  - ExecutionEngine 起動スクリプト。paper_trading 時は DB を分離。
  - Broker クライアント生成、OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の実行ループ。

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可能）。
  - 監視は本番 sqlite_path を使用。

- monitoring/
  - monitoring_db.py: SQLite に対する読み書き、init（テーブル作成）、MonitoringDB クラス
  - system_monitor.py: CPU/MEM/DISK 監視、データ鮮度チェック、PID チェック
  - trade_monitor.py: 注文滞留・約定異常検出
  - risk_monitor.py: ダウンド/ポジション上限監視、dashboard 更新
  - monitoring_engine.py: 各 Monitor を束ねるループ実行（テスト用 run_once あり）
  - alert_manager.py: LINE への push 通知（クールダウン管理）
  - kill_switch.py: kill.flag 書き込みロジック

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算（等金額・スコア加重）
  - position_sizing.py: 発注株数計算（risk_based / equal / score）
  - risk_adjustment.py: セクター上限・レジーム乗数
  - __init__.py: API エクスポート

- research/
  - factor_research.py: モメンタム/ボラティリティ/バリュー ファクター計算（DuckDB SQL）
  - feature_exploration.py: 将来リターン/IC/統計サマリ
  - __init__.py: 便利関数エクスポート（zscore_normalize など）

- ai/
  - news_nlp.py: ニュースを OpenAI でスコアリングし ai_scores テーブルへ書き込み（バッチ処理、リトライ、検証）
  - regime_detector.py: ETF MA + マクロセンチメントを合成して market_regime へ書き込み
  - __init__.py: 公開 API（score_news 等）

- utils/
  - process_priority.py: psutil を使ったプロセス優先度 / CPU affinity 設定ユーティリティ

- tools/
  - paper_verification_report.py: ペーパートレード DB を解析して検証レポートを表示
  - __init__.py

（上記以外にも execution 関連・data 関連モジュールが存在しますが、本 README は主要ユーティリティを中心に記載しています）

---

## 運用上の注意 / トラブルシューティング

- process priority / cpu affinity の設定には権限が必要な場合があります。権限エラーが出ても処理は継続されるように設計されています（ログ警告）。
- OpenAI API 呼び出しは外部依存のため失敗（429, network, timeout, 5xx）に対してリトライを行い、それでも失敗した場合は安全なフォールバックを行います（スコア 0 等）。
- .env にプレースホルダが残っていると validate_config で警告が出ます。必須項目は必ず設定してください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=1 の設定は危険です（kill flag を自動クリアしてしまうため）。デフォルトは 0 を推奨します。
- monitoring は「監視」ロジックであり、kill.flag を書き込むことで Execution を停止させる仕組みを持ちます。kill.flag の取り扱いは運用ルールを明確にしてください。

---

## よく使うコマンドまとめ

- .env 作成 / 更新
  python -m kabusys.config_setup

- 設定チェック
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動
  python -m kabusys.run_execution

- Monitoring 起動
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Paper Trading レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの主要機能と実行手順をまとめたものです。詳細な実装ドキュメント（StrategyModel.md、PortfolioConstruction.md など）や運用手順がある場合はそちらも参照してください。質問や追記したい箇所があれば教えてください。