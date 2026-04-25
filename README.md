# KabuSys

日本株向け自動売買フレームワーク（プロトタイプ）  
この README は与えられたコードベースに基づき、日本語でプロジェクトの概要・機能・セットアップ手順・使い方・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。以下の主要機能を持ち、プロダクション（live）／ペーパートレード（paper_trading）／開発（development）での運用を想定しています。

- 発注エンジン（Execution Engine）
- 監視（Monitoring）: システム稼働・注文状況・リスク監視とアラート発行
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量解析）
- AI ユーティリティ（ニュースセンチメント評価・市場レジーム判定）
- 設定ウィザード・設定検証ツール
- ペーパートレード検証レポート生成ツール

設計方針として、DB（DuckDB/SQLite）を用いたデータ処理、外部 API 呼び出しは明示的（OpenAI 等）、監視/停止はファイルフラグで制御するなど運用を重視した構成になっています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper trading モード時は MockBrokerClient を利用し、専用 DB（data/paper_trading.db）に記録
  - PID ファイル管理・停止フラグ検出（data/stop_requested.flag）

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・実行プロセス生存監視
  - TradeMonitor：注文滞留・約定異常検出（trade_logs 参照）
  - RiskMonitor：ドローダウン・ポジション上限監視、risk_logs / dashboard 更新
  - KillSwitch：危険条件検知時に data/kill.flag を作成して ExecutionEngine を停止
  - MonitoringEngine：上記 Monitor をまとめて定期実行

- Portfolio
  - 銘柄選定（スコア順で上位を選択）
  - 重み計算（等分配・スコア加重）
  - セクター集中抑制、レジーム乗数
  - ポジションサイズ計算（リスクベース / 等配分 / スコアベース、単元株丸め、aggregate cap）

- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC（Information Coefficient）算出・統計サマリ

- AI
  - ニュース NLP（OpenAI を用いたセンチメント算出、ai_scores への書込）
  - レジーム判定（ETF MA200 とマクロニュースセンチメントの合成）

- ツール
  - 設定ウィザード（python -m kabusys.config_setup）
  - 設定検証（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

- ユーティリティ
  - ロギング統一設定（logs/<app>.log、日次ローテート）
  - プロセス優先度・CPU affinity 設定ユーティリティ

---

## 前提 / 必要環境

- Python 3.9+（型アノテーションや一部ライブラリの想定）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - （オプション）PyYAML（設定検証時の YAML パース用。ただし未インストール時は YAML 検証はスキップされます）

インストール例（仮）
pip install duckdb psutil openai

（プロジェクト用に requirements.txt / Poetry 等があればそれを利用してください）

---

## 環境変数（主なもの）

必須
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

AI 関連（使用時）
- OPENAI_API_KEY

運用 / 任意
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合は MockBrokerClient が使用され、DB は別ファイルに書き込まれます
- DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（Settings 参照）

設定の自動読み込み
- プロジェクトルートの `.env` と `.env.local` は自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
- `.env` は絶対にリポジトリへコミットしないでください

---

## セットアップ手順（ローカル起動の最低手順）

1. リポジトリをクローン / ソースを用意
2. 仮想環境を用意して依存パッケージをインストール
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb psutil openai
3. .env を用意（手動で作成するかウィザードを使用）
   - ウィザード:
     python -m kabusys.config_setup
   - 最低限必要な値（例）
     JQUANTS_REFRESH_TOKEN=your_token
     KABU_API_PASSWORD=your_password
     KABUSYS_ENV=development
4. 設定検証:
   python -m kabusys.validate_config
   - 問題があれば修正してください。--strict を付けると warnings も失敗扱いになります。
5. DB ディレクトリ作成（必要なら）
   mkdir -p data logs
   - 初回起動スクリプトが自動作成する場合もありますが、アクセス許可に注意。

---

## 使い方（起動例）

- ExecutionEngine を起動する
  - デフォルト（development / paper_trading / live は .env の KABUSYS_ENV に依存）
    python -m kabusys.run_execution
  - 停止するには data/stop_requested.flag を作成するか（監視コンポーネントや手動でフラグファイルを作る）、実行プロセスへ SIGINT を送る

- Monitoring を起動する
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（秒、デフォルト 60）
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring

- 設定ウィザード
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで PAPER_TRADING_SQLITE_PATH を上書き可能

- AI 機能（プログラム的に呼ぶ例）
  - OpenAI API キーを設定（環境変数 OPENAI_API_KEY）
  - 例（ニューススコアリング）:
    from pathlib import Path
    import duckdb
    from kabusys.ai import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=<dateオブジェクト>)

  - レジーム判定も類似の呼び出し（OpenAI キー必須）

- ログ
  - ログは stdout に出力され、かつ logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリが適切に作成されていることを確認してください）。

---

## 停止・Kill スイッチの運用

- ExecutionEngine / Monitoring はファイルベースのフラグで制御します。
  - 停止要求（外部から）: data/stop_requested.flag を作成すると起動ループが検知して終了します
  - KillSwitch（重大リスク発生時）: data/kill.flag が書かれると ExecutionEngine 側で停止処理を行います
- Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリアします（本番では 0 を推奨）

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー内の主要ファイル / モジュール（与えられたコードに基づく）。実際のプロジェクトルートは src/ 配下に kabusys パッケージを含みます。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/               — 発注周りコンポーネント群（ファクトリ / エンジン / リポジトリ / マネージャ等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート管理、実装依存）
  - portfolio/
    - portfolio_builder.py   — 候補選定、等重/スコア重み
    - position_sizing.py     — 株数計算・資金配分ロジック
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — モメンタム/ボラ/バリュー等
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — レジーム判定（ETF + マクロ NLP）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

- data/                      — 実行時に使用する SQLite / PID / フラグ等（デフォルト）
- logs/                      — ログ出力先（デフォルト）

（上記は該当コードの抜粋に基づく要約です。細かな実装ファイルはプロジェクトに依存します）

---

## 注意事項 / 運用上のヒント

- .env ファイルは機密情報を含むため絶対に Git にコミットしないでください。
- KABUSYS_ENV=live の場合は実際の売買が発生します。必須設定・LINE 通知設定等を十分に確認してください。
- OPENAI_API_KEY を用いる機能は API コスト・利用制限があります。レート制限やエラーに対してはリトライ実装がありますが、運用時は監視を強化してください。
- DuckDB / SQLite のパスは Settings で上書き可能。production では適切なパスとバックアップを確保してください。
- Monitoring は MONITOR_POLL_INTERVAL（秒）でポーリングします。デフォルト 60 秒を基準に運用要件に合わせて調整してください。
- 実行時にプロセス優先度を High に設定します（set_process_priority）。権限不足で失敗した場合は警告ログが出ます。

---

必要であれば README を拡張して、具体的な起動フロー（ExecutionEngine の内部構成、OrderManager/RiskManager の詳細設定、テーブルスキーマの説明、サンプル .env）や運用手順（デプロイ／監視／障害時対応フロー）などを追加で作成します。どの項目を詳しく書くか指定してください。