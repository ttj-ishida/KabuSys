# KabuSys

日本株自動売買システムのサブセット実装（ライブラリ／実行スクリプト群）。  
このリポジトリは、戦略計算・ポートフォリオ建設・発注エンジン・監視・AI支援（ニュースNLP・レジーム判定）などを含みます。

以下はこのコードベースの概要、機能、セットアップ、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要
- 目的：日本株の自動売買を行うためのモジュール群（戦略・ポートフォリオ構築・注文処理・監視・分析）。
- 設計方針：
  - モジュールは「ビジネスロジック」と「永続化/外部API呼び出し」を分離。
  - DuckDB を用いた調査・ファクター計算、SQLite を用いた監視・ログ永続化。
  - 本番／ペーパートレードの分離（環境変数 `KABUSYS_ENV` による）。
  - 外部API（kabuステーション、J-Quants、OpenAI）は設定で切り替え可能／モック化可能。
  - ログ・プロセス優先度・Kill Switch 機構あり。

---

## 主な機能一覧
- 実行・監視
  - run_execution: ExecutionEngine を起動し発注処理を実行（KABUSYS_ENV により paper_trading モードあり）。
  - run_monitoring: SystemMonitor をポーリングしてシステム状態を監視（ポーリング間隔は `MONITOR_POLL_INTERVAL` で制御）。
- 環境設定・検証
  - config_setup: .env を対話式に生成・更新するウィザード。
  - validate_config: .env と config/*.yaml の事前検証 CLI（`--strict` オプションあり）。
- 監視（monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine：監視ポーリング、Kill Switch 判定、アラート発行連携。
  - monitoring_db: SQLite に監視ログ・注文ログ・ポジション等を永続化する層。
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等ウェイト／スコア重み、セクター上限適用、ポジションサイズ計算（ロット丸め・aggregate cap）。
- リサーチ（research パッケージ）
  - ファクター計算（モメンタム/ボラティリティ/バリュー）、将来リターン計算、IC 計算、統計サマリー。
- AI（ai パッケージ）
  - news_nlp: ニュース記事を OpenAI に投げて銘柄ごとのセンチメントを ai_scores に保存。
  - regime_detector: ETF MA とマクロニュースを使った日次レジーム判定（market_regime テーブルへ保存）。
- ツール
  - tools.paper_verification_report: ペーパートレード DB を集計して検証レポートを生成（稼働率・成功率・レイテンシ等）。
- ユーティリティ
  - logging_setup: stdout + 日次ローテートファイルログの統一設定。
  - process_priority: プラットフォーム差分を吸収したプロセス優先度/CPU affinity 設定。
  - config: .env の自動読み込み・Settings クラスで環境変数をラップ。

---

## 前提 / 必要環境
- Python 3.10 以上（型記法や union 型を利用）。
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - pyyaml（config YAML 検証用、必須ではない）
- インストール例:
  - pip install duckdb psutil openai pyyaml

※ requirements.txt が無い場合は上記を個別にインストールしてください。

---

## セットアップ手順（ローカル起動想定）
1. リポジトリをクローン／チェックアウト。
2. Python 仮想環境を作成・有効化。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）:
   - pip install duckdb psutil openai pyyaml
4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参照して手動作成
   - 自動読み込み: `kabusys.config` はプロジェクトルートに `.env` / `.env.local` を自動ロードします（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` でスキップ可能）。
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 問題がある場合は `.env` を修正。`--strict` は警告も失敗扱いにします。
6. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / PID / フラグファイル等は `data/` 配下に作られます。多くは起動時に自動作成されますが、権限等に注意してください。

---

## 主要環境変数（代表）
- KABUSYS_ENV: execution モードを切り替え（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定動作（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）

---

## 使い方（コマンド例）
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 注意: `KABUSYS_ENV=paper_trading` のとき、MockBrokerClient を使用し `data/paper_trading.db` に記録します（本番 DB と分離）。
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は（コード注釈の通り）環境にかかわらず本番用の `SQLITE_PATH` を参照します。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None) などの関数を利用（DuckDB 接続を渡す）。
  - OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` を使用。

停止方法・フラグ
- `data/stop_requested.flag` を作成すると、run_monitoring/run_execution のループが検知して安全に終了します（スクリプト内で参照している停止フラグ）。
- Kill Switch（監視から ExecutionEngine 停止指示）:
  - `KillSwitch` は `data/kill.flag` を書き込み、ExecutionEngine に停止を促します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では `0` 推奨）。

ログ
- ログは stdout に出力されるほか、デフォルトで `logs/<app_name>.log` に日次ローテーションで保存されます。ログディレクトリは `LOG_DIR` 環境変数または `logs/`。

---

## 主要モジュール説明（ファイル抜粋）
- src/kabusys/config.py
  - 環境変数 / .env の自動読み込みロジックと Settings クラスを提供。
- src/kabusys/config_setup.py
  - .env の対話式作成スクリプト。
- src/kabusys/validate_config.py
  - 起動前チェック CLI (.env / config/*.yaml / パス検証 等)。
- src/kabusys/run_execution.py
  - ExecutionEngine の起動スクリプト。paper_trading モードでは専用 DB を使用。
- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で制御）。
- src/kabusys/monitoring/*
  - monitoring_db.py: SQLite スキーマ定義・ラッパ。ログ書き込み・upsert 等。
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py / kill_switch.py / alert_manager (連携用)
- src/kabusys/portfolio/*
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py：候補選定・重み付け・サイズ計算・セクター上限等。
- src/kabusys/research/*
  - factor_research.py, feature_exploration.py：ファクター計算・IC・統計サマリー。
- src/kabusys/ai/*
  - news_nlp.py, regime_detector.py：OpenAI を用いたニュースセンチメント・レジーム判定ロジック（API キー必須）。
- src/kabusys/utils/*
  - logging_setup.py: 共通ログ設定。process_priority.py: プラットフォームに依存しない優先度設定。

ディレクトリ（抜粋）
- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - ai/
  - monitoring/
  - portfolio/
  - research/
  - tools/
  - utils/
  - monitoring_db.py
  - ...（上記に含まれる各ファイル）

---

## 注意事項 / 運用メモ
- 本番運用時は `KABUSYS_ENV=live` を設定。validate_config の警告・注意点に従って環境を十分に確認してください（LINE 通知設定や Kill Switch 設定等）。
- ai モジュールを使用するには OpenAI API の利用料金・レート制限に注意してください（リトライ・バックオフ機構あり）。
- run_monitoring は監視用 SQLite（SQLITE_PATH）を使用します。監視は「本番用 SQLite」を参照する（run_monitoring の実装注釈参照）。
- データベース・ファイルの権限・バックアップは運用で整備してください。
- テスト時は自動読み込みを無効化できます: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

もし README に含めたい追加のコマンド例、環境変数の詳細説明（すべての設定キー一覧）、あるいはデプロイ手順（systemd / supervisor での起動例）が必要であれば、その内容を教えてください。必要に応じて追記します。