# KabuSys

日本株向け自動売買システムのサンプル実装（ライブラリ + 実行スクリプト群）。

このリポジトリには、取引実行・監視（Monitoring）・ポートフォリオ構築・リサーチ・AI（ニュースセンチメント・レジーム判定）などの主要コンポーネントの実装が含まれます。設計は実運用を想定しており、SQLite / DuckDB による永続化、OpenAI への安全な呼び出し、監視アラート（LINE）やフェイルセーフ（kill.flag）などの機能を備えています。

以下はこのコードベースの概要と使い方です。

## 主な特徴（機能一覧）

- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper trading モード（環境変数 KABUSYS_ENV=paper_trading）によりモックブローカーで完全分離された DB に記録
  - 再起動時のリコンシリエーション（Reconciler）で送信済み注文・ポジションを突合

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格異常の検出
  - RiskMonitor: ドローダウン、ポジション上限監視、ダッシュボード更新
  - MonitoringEngine: 上記モニタを定期ポーリング、KillSwitch による停止シグナル（kill.flag）
  - 監視ログの永続化（SQLite）と Streamlit ダッシュボード

- ポートフォリオ構築
  - シグナルから候補選定、等重配分 / スコア加重、リスク調整（セクターキャップ、レジーム乗数）
  - 株数算出（単元丸め・aggregate cap）ロジック

- リサーチ（Research）
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ

- AI（OpenAI）
  - ニュース記事のセンチメントスコアリング（gpt-4o-mini を想定）
  - マクロニュース + ETF MA200 を合成した市場レジーム判定（bull/neutral/bear）
  - API 呼び出しはリトライ・クリッピング・フェイルセーフ実装

- ユーティリティ
  - 環境変数自動読み込み（.env / .env.local）、設定ラッパー Settings
  - プロセス優先度・CPU affinity 設定（クロスプラットフォーム psutil ベース）
  - 各種永続化テーブルの初期化・マイグレーション（monitoring_db.init_monitoring_db）

## セットアップ手順

1. Python 環境
   - Python 3.9+ を推奨
   - 仮想環境を作成・有効化して下さい（venv / pyenv 等）

2. 依存パッケージ（主要）
   - pip install を使って以下を導入します（プロジェクトに requirements.txt がある場合はそちらを利用してください）。
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   例:
   ```
   python -m pip install duckdb psutil requests openai streamlit
   ```

3. 環境変数 / .env
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な環境変数（最低限の例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...            （AI 機能を使う場合）
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60     （監視ポーリング秒数の上書き）
   - `.env.example` をベースに作成してください（プロジェクトルートが自動検出されます）。

4. データディレクトリ
   - デフォルトでは `data/` 以下に DB や PID/flag ファイルを作成します。必要なら作成してください（実行時に自動でディレクトリ作成される処理もあります）。

## 使い方（主要スクリプト）

### 監視ループ起動（Monitoring）
- スクリプト: src/kabusys/run_monitoring.py
- 概要: SystemMonitor を初期化してポーリングループを実行します。プロセス優先度を "high" に設定します。
- 既定のポーリング間隔は 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可能、正の整数）。
- 実行:
  ```
  python -m kabusys.run_monitoring
  ```
  または
  ```
  python src/kabusys/run_monitoring.py
  ```
- 注意:
  - Monitoring は KABUSYS_ENV に関わらず本番用の sqlite_path（Settings.sqlite_path）を使います。
  - run_monitoring は監視用 DB の初期化（テーブル作成）を行います。

### 実行エンジン起動（Execution）
- スクリプト: src/kabusys/run_execution.py
- 概要: ExecutionEngine を起動します。KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）へ記録します。
- 実行:
  ```
  python -m kabusys.run_execution
  ```
- 注意:
  - Execution 起動時にも pid ファイルが使われます（Settings.pid_file_path）。
  - run_execution は監視テーブルが存在することを保証するため init_monitoring_db を呼びます（冪等）。

### Streamlit ダッシュボード（監視データの可視化）
- ファイル: src/kabusys/monitoring/streamlit_dashboard.py
- 実行:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  `--` 以下は本スクリプトへの引数（`--db` で DB パス指定）。
- 読み取り専用で DB を開きます（URI に `?mode=ro` を付ける）。

### Paper Trading 検証レポート生成
- スクリプト: src/kabusys/tools/paper_verification_report.py
- 概要: paper_trading DB のログを集計し検証レポートを標準出力に出すユーティリティ。
- 実行例:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB を明示する:
  ```
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

### AI 処理（ニューススコア / レジーム判定）
- 関数呼び出し: プログラム経由で `kabusys.ai.news_nlp.score_news`、`kabusys.ai.regime_detector.score_regime` を利用します。
- 注意:
  - 実行には OPENAI_API_KEY が必要（引数でも渡せます）。
  - API 呼び出しはリトライ・例外ハンドリングが組まれており、失敗時は安全側のフォールバックを行います（例: macro_sentiment=0.0）。

## 主要な設定ポイント（短いリファレンス）

- KABUSYS_ENV: development | paper_trading | live
  - paper_trading: ブローカー呼び出しはモックになり、DB は PAPER_TRADING_SQLITE_PATH を使用（デフォルト data/paper_trading.db）。
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（整数、デフォルト 60）。1 未満・不正値は無視されデフォルトが使われる。
- PID_FILE_PATH / KILL_FLAG_PATH: ExecutionEngine の起動/停止管理に使用。
- PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant|partial|never|reject）。
- DUCKDB_PATH / SQLITE_PATH: DuckDB と Monitoring SQLite のファイルパス（デフォルト: data/kabusys.duckdb, data/monitoring.db）。

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py
  - パッケージ情報（__version__ 等）
- config.py
  - 環境変数読み込み（.env 自動ロード）、Settings クラス（全設定をプロパティで提供）
- run_monitoring.py
  - SystemMonitor をポーリングで回す起動スクリプト
- run_execution.py
  - ExecutionEngine を起動するスクリプト（paper_trading モード対応）

サブパッケージ:
- ai/
  - news_nlp.py: ニュース記事を OpenAI に投げて銘柄別スコアを作るロジック
  - regime_detector.py: ETF MA200 とマクロニュースを合成して日次レジーム判定
- monitoring/
  - monitoring_db.py: monitoring 用 SQLite テーブル初期化 / 永続化ラッパー（MonitoringDB）
  - system_monitor.py: CPU/Mem/Disk・PID・データ鮮度監視
  - trade_monitor.py: 注文滞留・約定異常チェック
  - risk_monitor.py: ドローダウン / ポジション上限のチェック
  - kill_switch.py: kill.flag の生成・検査
  - alert_manager.py: LINE Push 通知（クールダウン管理）
  - monitoring_engine.py: 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード
- execution/
  - reconciler.py: 再起動時の注文/ポジションの突合（自動復旧）
  - order_manager.py: 注文の作成・送信・状態管理（OrderState Machine）
  - その他（broker_factory, order_repository など実装ファイルがある想定）
- portfolio/
  - portfolio_builder.py: 候補選定・重み算出（等重・スコア加重）
  - position_sizing.py: 株数算出、aggregate cap、lot-size 丸め
  - risk_adjustment.py: セクターキャップ、レジーム乗数
- research/
  - factor_research.py: momentum/volatility/value ファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリ等
- tools/
  - paper_verification_report.py: Paper Trading 検証レポート出力ツール
- utils/
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

## その他・運用上の注意

- DB 初期化: run_monitoring/run_execution は必要に応じて monitoring 用テーブルを初期化します（init_monitoring_db）。
- kill.flag: KillSwitch により `data/kill.flag` を作成すると ExecutionEngine に停止シグナルを送ります。起動時にクリアしたい場合は Settings.kill_flag_clear_on_start を参照する処理を追加してください（Settings に該当フラグあり）。
- 権限: プロセス優先度や CPU affinity の設定はシステム権限に依存します（psutil.AccessDenied をハンドリングして安全にスキップします）。
- ロギング: Settings.log_level による設定ができます（環境変数 LOG_LEVEL）。
- AI API 使用: OPENAI_API_KEY の扱いには注意（個人情報・課金）。運用ではレート管理・エラー時のフォールバックが必要です。

---

この README はコードベースの主要機能・起動方法・構成をまとめたものです。実運用や CI での利用にあたっては、追加で requirements.txt、デプロイスクリプト、systemd ユニットファイルやコンテナ化（Dockerfile）などを用意することを推奨します。必要であれば実際のデプロイ手順や systemd/containers 向けの設定例も作成します。