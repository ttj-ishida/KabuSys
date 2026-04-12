# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買プラットフォーム「KabuSys」の内部コンポーネント群を含みます。戦略・ポートフォリオ構築、発注実行、監視、リサーチ（DuckDB ベースのファクター計算）、およびニュース NLP を用いた AI スコアリングなどの機能を備えています。

以下は本コードベースの概要・機能・セットアップ・使い方・ディレクトリ構成のまとめです。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 実行方法（使い方）
- 主要環境変数（.env 例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の責務を持つコンポーネントで構成された自動売買基盤です。

- Execution Engine：ブローカーへの発注・注文管理、リスク管理、再同期（Reconciler）など
- Monitoring：システム稼働監視、注文滞留・価格異常監視、リスク（ドローダウン等）監視、LINE 通知、kill flag による安全停止
- Research：DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー 等）、特徴量解析（IC 等）
- Portfolio Construction：候補選定、重み付け、ポジションサイジング、セクター制限、レジーム乗数
- AI モジュール：OpenAI（gpt-4o-mini）を利用したニュースセンチメントスコアリング、マクロニュースを用いた市場レジーム判定
- ユーティリティ：プロセス優先度設定、.env 読み込み、DB マイグレーション等

このリポジトリは純粋関数的なモジュール（ポートフォリオ計算等）と、永続化・IO を行うコンポーネント（SQLite / DuckDB / ブローカークライアント）を含みます。

---

## 主な機能一覧

- 発注ワークフロー（OrderManager / OrderRepository / OrderRecord）
- ブローカー抽象化（BrokerClientFactory 等により本番 or モック切替）
- 起動時のリコンシリエーション（Reconciler）による自動復旧
- 監視機能：
  - SystemMonitor：CPU/メモリ/ディスク、プロセス存在確認、データ鮮度チェック
  - TradeMonitor：滞留注文検出／約定価格異常検出
  - RiskMonitor：ドローダウン監視、ポジション上限監視
  - KillSwitch / AlertManager：条件により kill.flag を書き実行エンジンを停止、LINE へ通知
  - MonitoringEngine：上記をまとめて定期ポーリング
  - streamlit ダッシュボード（読み取り専用）で監視状況を可視化
- Paper Trading サポート（KABUSYS_ENV=paper_trading で MockBroker を使用し data/paper_trading.db に記録）
- Paper Trading 検証レポート出力ツール（kabusys.tools.paper_verification_report）
- DuckDB を利用したファクター計算、将来リターン・IC・統計サマリ
- OpenAI を利用したニュースセンチメント & レジーム検出（フェイルセーフなリトライ・バリデーション実装）
- プロセス優先度設定（cross-platform、psutil 使用）

---

## セットアップ手順

1. システム要件
   - Python 3.9+
   - DuckDB（Python パッケージ）
   - SQLite（標準ライブラリ）
   - 必要 Python ライブラリ（例）
     - duckdb, psutil, requests, openai, streamlit （監視ダッシュボード利用時）
   - 例（pip）:
     ```
     pip install duckdb psutil requests openai streamlit
     ```

2. リポジトリルートの .env 読み込み
   - `kabusys.config` はプロジェクトルートを .git または pyproject.toml で検出し、以下の優先順で自動ロードします（デフォルト動作）。
     1. OS 環境変数（既に設定されているもの）
     2. .env.local（存在する場合、上書き）
     3. .env（未設定キーのみ）
   - 自動ロードを無効にする場合は環境変数を設定します:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. データディレクトリ
   - デフォルトの DB パス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - 必要に応じて `.env` でパスを上書きしてください。

4. DB 初期化
   - Monitoring 用テーブルは実行時に作成（init_monitoring_db を呼び出し）されます。明示的に実行する必要は通常ありません。

5. OpenAI
   - AI 機能を使用する場合は `OPENAI_API_KEY` を環境変数または関数引数で設定してください。

---

## 実行方法（使い方）

基本的な実行方法は Python モジュールとして起動します。

1. Execution Engine（本番 or Paper）
   - Paper Trading:
     ```
     export KABUSYS_ENV=paper_trading
     python -m kabusys.run_execution
     ```
     - Paper Trading は mock ブローカーを使い、データは data/paper_trading.db に記録されます。
     - `PAPER_FILL_MODE`（instant/partial/never/reject）で約定動作を指定できます（デフォルト: instant）。
   - 本番（live）:
     ```
     export KABUSYS_ENV=live
     python -m kabusys.run_execution
     ```

2. Monitoring（監視ループ）
   - デフォルト 60 秒間隔で監視ループを実行します。`MONITOR_POLL_INTERVAL` で上書き可能（正の整数のみ、有効でない値はデフォルトにフォールバック）。
     ```
     python -m kabusys.run_monitoring
     ```
   - MONITOR_POLL_INTERVAL の設定例:
     ```
     export MONITOR_POLL_INTERVAL=30  # 30秒間隔
     ```

3. streamlit 監視ダッシュボード（読み取り専用）
   - Monitoring DB を読み取り専用で開き GUI を表示します:
     ```
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
     ```

4. Paper Trading 検証レポート
   - コマンドラインツールでレポートを生成:
     ```
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     ```
   - デフォルト DB: `data/paper_trading.db`。`--db` オプションまたは `PAPER_TRADING_SQLITE_PATH` 環境変数で指定できます。

5. AI モジュール利用例（Python REPL）
   - ニューススコアリング:
     ```python
     import duckdb
     from datetime import date
     from kabusys.ai.news_nlp import score_news

     conn = duckdb.connect("data/kabusys.duckdb")
     n = score_news(conn, target_date=date(2026, 4, 1), api_key="sk-...")
     print("scored:", n)
     ```
   - レジーム判定:
     ```python
     from kabusys.ai.regime_detector import score_regime
     score_regime(conn, target_date=date(2026, 4, 1), api_key="sk-...")
     ```

6. 設定ファイル（.env）読み込みの注意
   - `kabusys.config.Settings` は多数の設定を環境変数経由で提供します。未設定の必須変数は ValueError を投げます（例えば JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など）。

---

## 主要環境変数（.env 例）

以下は主な環境変数とその説明（必要に応じて .env に記載）:

- KABUSYS_ENV: execution 環境。allowed: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須: 使う場合）
- KABU_API_PASSWORD: kabu API パスワード（必須: 本番連携時）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（AlertManager）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: Monitoring SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時のフィルモード（instant | partial | never | reject）
- PID_FILE_PATH: ExecutionEngine PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill flag ファイル（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（"1" でクリア）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: しきい値（%）

簡単な .env の例:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
PAPER_FILL_MODE=instant
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

---

## 注意点 / 動作上の設計方針（抜粋）

- Paper Trading は本番 DB と完全分離します（専用の SQLite を使用）。
- .env の自動ロードはプロジェクトルート (.git または pyproject.toml) を基準に行われます。ルートが見つからないと自動ロードはスキップされます。
- AI 呼び出しはリトライやレスポンスバリデーションを行い、失敗時はフェイルセーフ（デフォルト値）で継続します。
- Monitoring は kill.flag を書くことで ExecutionEngine に停止を指示します（冪等な書き込み）。
- Process priority 設定（set_process_priority）は起動直後に呼ばれます。psutil の権限により設定できない場合はログに警告を出します。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主なファイル・モジュール概要です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / .env の読み込みと Settings
  - run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV による切替）
  - run_monitoring.py — SystemMonitor 単独ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算・スケールダウンロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメントの取得・ai_scores 書込み
    - regime_detector.py — マクロ + MA200 から市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite の監視用永続化層（テーブル作成 / CRUD）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE 通知ラッパー
    - monitoring_engine.py — 各モニタを束ねるポーリングループ
    - streamlit_dashboard.py — streamlit ベースの簡易ダッシュボード（読み取り専用）
  - execution/
    - order_manager.py — 発注フロー / 2相永続化 / 同期ロジック
    - reconciler.py — 起動時の注文・ポジション再同期
    - (その他ブローカー抽象・Repository・Engine 実装が存在)
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - research/__init__.py, monitoring/__init__.py, ai/__init__.py, portfolio/__init__.py — エクスポート整理

（注）上記は主要モジュールのみ抜粋しています。詳細は各モジュールの docstring を参照してください。

---

## よくある質問 / トラブルシューティング

- Monitoring のポーリング間隔を変更したい：
  - 環境変数 `MONITOR_POLL_INTERVAL` に正の整数を設定してください。不正な値は警告が出てデフォルト 60 秒に戻ります。
- Paper Trading の DB を別位置にしたい：
  - `PAPER_TRADING_SQLITE_PATH` を .env に設定してください。
- kill.flag が残っていて Engine が起動できない：
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動的にクリアできます。手動で削除するなら data/kill.flag を削除してください。
- OpenAI API のエラーでスコアリングが止まる：
  - 実装はエラー時にフェイルセーフ（スコア 0.0 など）で継続する設計です。API キーやネットワーク、レート制限を確認してください。

---

README はここまでです。必要であれば以下について追記できます：
- 詳しい .env.example（有効なキー一覧）
- ExecutionEngine の詳しい起動引数・ログの取り扱い
- ブローカー実装の切替方法（Mock vs Live）
- 開発用の Docker / CI 設定（現状含まれていないため追加可能）

追加で欲しい情報があれば教えてください。