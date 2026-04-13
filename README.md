# KabuSys

日本株自動売買システムの実装（ライブラリ / 実行スクリプト群）

この README は、提供されているコードベース（src/kabusys/**）の概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームの一部実装です。  
主に以下の機能を備えています：

- 注文管理・実行エンジン（ExecutionEngine）とブローカークライアントの抽象化
- 監視（Monitoring）: システム状態、注文滞留、リスク（ドローダウンやポジション上限）を監視
- ポートフォリオ構築ロジック（銘柄選定、重み算出、ポジションサイジング）
- リサーチ：ファクター計算 / 特徴量解析（DuckDB を用いた過去価格データ解析）
- AI ユーティリティ：ニュース記事を LLM でスコアリングし、マーケットレジーム判定を行う
- 運用補助ツール：Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード
- 環境設定管理（.env 自動読み込み／Settings クラス）

設計方針として、DB（SQLite / DuckDB）への読み書きや外部 API 呼び出しは明示的に分離されており、テストや paper_trading の分離が考慮されています。

---

## 主な機能一覧

- 実行系
  - ExecutionEngine 起動（run_execution.py）
  - ブローカー抽象化 / MockBroker を用いた paper_trading モード
  - 再起動時のリコンシリエーション（Reconciler）

- 監視系
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス生存、株価データ鮮度
  - TradeMonitor: 滞留注文・約定価格異常チェック
  - RiskMonitor: ドローダウン・ポジション数監視、ダッシュボード更新
  - KillSwitch：危険時に flag ファイルを書いて ExecutionEngine を停止させる仕組み
  - AlertManager：LINE プッシュ通知（クールダウン付き）
  - Streamlit ダッシュボード（監視情報の可視化）

- ポートフォリオ構築（純粋関数群）
  - 候補選定、等配分 / スコア配分、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算

- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン / IC 計算 / 統計サマリ

- AI（OpenAI 使用）
  - ニュースを LLM でセンチメント分析し ai_scores テーブルへ保存
  - マクロニュースとETF MA を組み合わせた市場レジーム判定

- 運用ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - DB 初期化（監視用テーブル作成、マイグレーション対応）

---

## セットアップ手順（ローカル開発 / 小規模運用向け）

1. Python 環境作成（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate    # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール（最低限の例）
   ```
   pip install duckdb psutil openai requests streamlit
   ```
   - 実際の運用では追加のパッケージやバージョン固定（requirements.txt）を用意してください。

3. リポジトリルートに `.env`（および必要なら `.env.local`）を作成  
   主要な環境変数（例・デフォルト）は以下参照。`.env` サンプルは .env.example を参考に作成してください。

4. データディレクトリを作成
   ```
   mkdir -p data
   ```
   初回起動時に monitoring 用の SQLite テーブルは自動作成されます（init_monitoring_db を利用）。

5. （任意）KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと自動 .env 読み込みを無効化できます：
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 主な環境変数（Settings でのキーとデフォルト）

- 認証 / API
  - JQUANTS_REFRESH_TOKEN — 必須（J-Quants 用）
  - KABU_API_PASSWORD — 必須（kabuステーション 用）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
  - LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（任意）
  - LINE_USER_ID — LINE 通知先ユーザー ID（任意）

- 実行環境 / モード
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
    - paper_trading の場合、MockBrokerClient が使用され、SQLite DB は paper_trading 用に分離されます。

- データベース / ファイルパス
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — 監視用 SQLite デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用: data/paper_trading.db
  - PID_FILE_PATH — デフォルト: data/execution.pid
  - KILL_FLAG_PATH — デフォルト: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START — "1" なら起動時に kill.flag をクリア

- Paper trading / シミュレーション
  - PAPER_FILL_MODE — "instant" | "partial" | "never" | "reject"（デフォルト: instant）

- 監視/閾値
  - CPU_THRESHOLD_PCT — デフォルト 90.0
  - MEMORY_THRESHOLD_PCT — デフォルト 85.0
  - DISK_THRESHOLD_PCT — デフォルト 90.0

- ログ
  - LOG_LEVEL — "DEBUG" | "INFO" | ...（デフォルト: INFO）

自動 .env 読み込みの挙動：
- プロジェクトルートは __file__ の親階層から .git または pyproject.toml を探索して決定
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要コマンド例）

※ 以下はリポジトリのルート（src を含む）で実行することを想定しています。パッケージとしてインストールしている場合は `python -m kabusys.xxx` で動作します。

- 監視ループの起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルト 60 秒。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用する設計です。

- 実行エンジン（ExecutionEngine）起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し DB は PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）。

- Streamlit ベースの監視ダッシュボード起動
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成（コマンドラインツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI スコアリング / レジーム判定（プログラム API）
  - ニューススコア: `kabusys.ai.score_news(conn, target_date, api_key=None)` を呼ぶ
  - レジーム: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

（AI 系は OpenAI API キーが必要。API 呼び出しは再試行やフェイルセーフに配慮して実装されています）

---

## 監視に関する注意点

- MonitoringDB（monitoring_db.init_monitoring_db）は自動でテーブルを作成／簡易マイグレーション（カラム追加）します。実行前にデータディレクトリを用意してください。
- KillSwitch はデフォルトで `data/kill.flag` を書き、ExecutionEngine 側でこのファイルを検知して停止する運用を想定しています。
- AlertManager は LINE Push API を使った一方向通知を行います。token / user_id が未設定の場合は送信をスキップします（ログに記録）。

---

## ディレクトリ構成（該当ファイルの説明）

src/kabusys/
- __init__.py — パッケージの基本情報（__version__ 等）
- config.py — 環境変数/.env 読み込みと Settings クラス（アプリ設定）
- run_monitoring.py — SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL 対応）
- run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 向け分離対応）

サブパッケージ / モジュール
- ai/
  - news_nlp.py — ニュース記事を OpenAI でスコアリングし ai_scores に書き込む処理
  - regime_detector.py — ETF MA とマクロニュースを組み合わせた市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層（テーブル作成、CRUD ユーティリティ）
  - system_monitor.py — CPU/メモリ/Disk、プロセス PID、データ鮮度の監視
  - trade_monitor.py — 注文滞留／約定異常検出
  - risk_monitor.py — ドローダウン/ポジション上限監視、dashboard 更新
  - kill_switch.py — flag ファイル生成・管理
  - alert_manager.py — LINE 通知（クールダウン管理）
  - monitoring_engine.py — 各 Monitor の束ねとポーリング実行
  - streamlit_dashboard.py — Streamlit で監視情報可視化（起動コマンドあり）
- execution/
  - order_manager.py — 注文作成・送信・状態遷移管理（OrderState マシン）
  - reconciler.py — 起動時の注文・ポジションのリコンシリエーション
  - （他: broker_factory 等が存在する想定）
- portfolio/
  - portfolio_builder.py — 候補選定 / 重み算出
  - position_sizing.py — 株数決定・スケーリング・単元丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 用検証レポート出力 CLI
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（実際のリポジトリに含まれる他のモジュール/ファイル群に依存する機能があります。上記は主要箇所の抜粋です。）

---

## 運用上のヒント / FAQ

- ポーリング間隔を短くしすぎるとリソース消費や API レートに影響するため、MONITOR_POLL_INTERVAL は慎重に設定してください（最小値は 1 秒以上）。
- paper_trading モードは本番 DB とファイルを分離するため安全にシミュレーション可能です（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI 呼び出しはネットワークやレート制限で失敗する想定で実装されていますが、API キーは漏洩しないよう運用してください。
- .env 自動読み込みはプロジェクトルートの検出に依存します。CI 等で意図しない読み込みを避ける場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか明示的に環境変数を渡してください。

---

必要であれば、README に起動例（systemd unit / docker compose）やより詳細な環境変数説明（サンプル .env）、依存パッケージのバージョン指定（requirements.txt）を追加できます。追加希望があれば教えてください。