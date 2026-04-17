# KabuSys

日本株向け自動売買システムの一部（ライブラリ / 実行スクリプト / ツール群）です。  
このリポジトリには、監視・実行・ポートフォリオ構築・調査・AI 補助モジュール等の実装が含まれます。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つコンポーネント群で構成されます。

- ExecutionEngine（発注ロジック / ブローカークライアント統合）
- Monitoring（システム状態・注文状態・リスク監視、Kill Switch）
- Portfolio Construction（銘柄選定・重み付け・ポジションサイズ計算）
- Research（ファクター計算・特徴量探索）
- AI 支援（ニュースを LLM でスコアリング、レジーム判定）
- ユーティリティ（プロセス優先度設定、.env ウィザード、設定検証、レポート生成）

主要な実行スクリプト:
- run_execution.py — ExecutionEngine を起動
- run_monitoring.py — SystemMonitor のポーリングループを起動
- tools/paper_verification_report.py — ペーパートレード検証レポート生成

---

## 機能一覧

- 環境設定ウィザード（.env の対話式生成 / 更新）
- 設定検証 CLI（.env と config/*.yaml の検査）
- 実行エンジン起動（本番 / ペーパートレード切替、専用 DB）
- 監視エンジン（CPU / メモリ / ディスク / プロセス状態 / データ鮮度）
- トレード監視（滞留注文、約定異常）
- リスク監視（ドローダウン検出、ポジション上限）
- Kill Switch（リスクトリガで Execution を停止するフラグファイル）
- LINE 通知（AlertManager、トークン未設定ならログ出力のみ）
- AI モジュール（ニュースのセンチメントスコアリング、マクロによるレジーム判定、OpenAI 利用）
- Research（momentum / volatility / value ファクター、IC 計算、統計サマリー）
- Portfolio（候補選定、重み付け、ポジションサイズ計算、セクターキャップ適用）
- monitoring DB（SQLite ベースのログ & ダッシュボードストア）
- 各種ユーティリティ（プロセス優先度 / CPU affinity 設定）

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.10+）

2. 必要パッケージをインストール（代表的な依存）:
   - duckdb
   - psutil
   - openai
   - requests
   - PyYAML（validate_config の YAML 検証に使用）
   - （標準ライブラリ: sqlite3 は同梱）

   例:
   ```
   pip install duckdb psutil openai requests pyyaml
   ```

   ※ 実プロジェクトでは requirements.txt / poetry 等で管理してください。

3. プロジェクトルートに .env を作成
   - 自動読み込みを使う場合（デフォルト）: config_setup で生成できます（下記参照）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. .env の最低必須項目
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - その他（必要に応じて）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI モジュール利用時）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）

   簡易サンプル (.env 内に保存する形式):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   ```

---

## 使い方

以下は一般的な操作フローとコマンド例です。

1. .env を対話式で作成
   ```
   python -m kabusys.config_setup
   ```
   - 対話形式で環境変数を設定し、.env を生成します。

2. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も失敗扱い
   ```

3. 監視プロセスを起動
   - run_monitoring は SystemMonitor のポーリングループを起動します。
   - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60 秒）。
   - 停止はプロジェクトルート/data/stop_requested.flag を作成するか Ctrl+C。
   ```
   python -m kabusys.run_monitoring
   ```
   注意:
   - run_monitoring は Settings に従い「本番」sqlite_path を使って監視データを書き込みます（KABUSYS_ENV に依存せず本番 DB を使用する設計です）。

4. 実行エンジンを起動（実際の発注 / ペーパートレード）
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録します（settings.is_paper により切替）。
   - 停止フラグ: data/stop_requested.flag を作成すると Engine が停止します。
   ```
   python -m kabusys.run_execution
   ```

5. ペーパートレード検証レポート生成
   - Paper Trading の SQLite を指定してレポートを出力できます。
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # または
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   ```

6. AI モジュール（ニューススコア / レジーム判定）
   - OpenAI API キーが必要です（環境変数 OPENAI_API_KEY か api_key 引数）。
   - ニューススコアリング:
     - kabusys.ai.score_news を呼び出すか、上位モジュールから利用してください。
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
   - これらは外部 API（OpenAI）を利用するため、API 制約・料金を考慮してください。

環境変数のうち特に重要なもの
- KABUSYS_ENV: execution のモード（development / paper_trading / live）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH: DB ファイルパス
- OPENAI_API_KEY: LLM を使うモジュールで必要
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（本番では 0 推奨）

停止と Kill Switch
- 実行停止（外部から安全に停止）:
  - run_monitoring / run_execution はプロジェクトの data/stop_requested.flag を監視しています。これを作成するとループを終了します。
- Kill Switch:
  - リスク条件（ドローダウン超過など）で data/kill.flag が作成され、ExecutionEngine の停止トリガとなります。
  - kill.flag は Settings.kill_flag_path（デフォルト data/kill.flag）で管理されます。

---

## ディレクトリ構成（抜粋）

リポジトリは src/kabusys 以下に主要モジュールを配置しています。主要ファイル・ディレクトリを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成 / 永続層
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留 / 約定異常監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - alert_manager.py       — LINE 通知
    - kill_switch.py         — フラグファイルによる停止信号
  - execution/                — Execution 系（発注、OrderRepository 等）※一部未表示
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み付け
    - position_sizing.py     — 株数計算 / aggregate cap
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py            — ニュースを OpenAI でスコアリング、ai_scores に書込
    - regime_detector.py     — MA + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

- data/
  - （実行時に生成される SQLite / DuckDB ファイルやフラグファイル等を想定）
  - stop_requested.flag
  - kill.flag
  - execution.pid
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb

---

## 注意事項 / 運用メモ

- .env は絶対に VCS にコミットしないこと（config_setup.py も警告文あり）。
- run_monitoring は「監視用」処理で、Settings に関わらず監視 DB（SQLITE_PATH）を本番用パスで利用する設計です。運用時に意図せぬ DB を上書きしないよう注意してください。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に分離して記録します。
- OpenAI を使う機能は API 呼び出しの失敗を考慮したフェイルセーフ設計になっていますが、API キーやコストの取り扱いは注意してください。
- validate_config は PyYAML がない場合 YAML の中身検証をスキップします（存在チェックは行います）。
- process priority / cpu affinity の設定は psutil に依存し、権限不足やプラットフォーム非対応時には警告を出してスキップします。

---

この README はコードベースの主要な使い方と構成をまとめたものです。個別のモジュールや関数の詳細は各ファイルのドキュメンテーション（ソース内 docstring）を参照してください。必要であれば、README に含める追加情報（システム図、データベーススキーマ、運用手順など）を追記します。