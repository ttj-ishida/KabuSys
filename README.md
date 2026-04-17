# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ。  
バックテスト／研究用ファクター計算、ポートフォリオ構築、発注実行（本番 / ペーパートレード）、監視・アラート、LLM を用いたニュースセンチメント評価などの機能を備えています。

---

## プロジェクト概要

KabuSys は以下のような責務を持つコンポーネント群で構成されます。

- データ処理・研究（DuckDB を利用したファクター計算、将来リターン算出、統計解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター制限、レジーム調整）
- 発注実行（本番は kabuステーション API、paper_trading 環境では MockBrokerClient と専用 SQLite DB）
- 監視（システム状態、注文滞留、約定異常、リスク閾値などの監視・ログ記録）
- アラート（LINE Messaging API へのプッシュ）
- AI（OpenAI を用いたニュースのセンチメント付与、マクロセンチメントによるレジーム判定）
- 各種 CLI ツール（.env ウィザード、設定検証、Paper Trading 検証レポートなど）

バージョン: 0.1.0

---

## 主な機能一覧

- 環境セットアップウィザード（`python -m kabusys.config_setup`）で .env を対話的に生成
- 設定ファイル・環境変数検証（`python -m kabusys.validate_config`）
- ExecutionEngine の起動（`python -m kabusys.run_execution`）
  - KABUSYS_ENV が `paper_trading` のときは MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db）に記録
- Monitoring の起動（`python -m kabusys.run_monitoring`）
  - 監視ログは SQLite（monitoring.db）へ永続化。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト: 60 秒）
- モジュール化された監視エンジン（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch（data/kill.flag による実行停止シグナル）
- AI モジュール
  - ニュースセンチメントの算出と ai_scores テーブルへの書き込み（`kabusys.ai.score_news`）
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）
- 研究用ユーティリティ（ファクター計算、IC 計算、統計サマリー等）
- Paper Trading 向けの検証レポート生成（`python -m kabusys.tools.paper_verification_report`）

---

## 依存関係（主なもの）

- Python 3.9+
- duckdb
- psutil
- openai
- requests
- PyYAML（config ファイルの検証に任意で使用）
- 標準ライブラリ: sqlite3, threading, logging 等

（requirements.txt がある場合はそれを使用してください。無い場合は上記パッケージをインストールしてください。）

---

## セットアップ手順（簡易）

1. リポジトリをクローンする
   - git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests PyYAML

4. .env を生成・編集
   - python -m kabusys.config_setup
     - 対話形式で J-Quants token、kabu API パスワード、DB パス、KABUSYS_ENV などを設定できます。
   - 自動読み込み: デフォルトでプロジェクトルートの .env / .env.local が自動で読み込まれます（無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

5. 設定検証（起動前のチェック）
   - python -m kabusys.validate_config
   - `--strict` を付けると警告も失敗（exit 1）扱いになります。

6. Data ディレクトリ作成（必要に応じて）
   - デフォルトの DB パスは `data/kabusys.duckdb` と `data/monitoring.db`（ペーパートレードは `data/paper_trading.db`）です。ディレクトリがない場合は作成されます。

---

## 主要な環境変数（抜粋）

必須（起動・主要機能で使用）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

推奨 / よく使うもの
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
  - paper_trading のとき、ExecutionEngine は MockBrokerClient を使い DB を分離します
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（未設定なら通知は行われません）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動でクリアするか（0/1）

設定は .env または OS 環境変数で指定できます。自動ロードはプロジェクトルートの .env / .env.local から行われます。

---

## 使い方

1. .env を作成して設定を適切に埋める
   - python -m kabusys.config_setup

2. 設定を検証
   - python -m kabusys.validate_config
   - 重要な環境（live）の場合は警告にも注意すること

3. 発注エンジンを起動（Production / Paper）
   - python -m kabusys.run_execution
   - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします
   - 実行は別プロセス（スレッド）で行われ、PID ファイル（data/execution.pid）を生成します

4. 監視ループを起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能
   - 監視は monitoring DB（settings.sqlite_path）へ記録し、kill.flag の評価等を実行します

5. Kill Switch
   - `kabusys.monitoring.KillSwitch` は `data/kill.flag` を書き込むことで ExecutionEngine の停止シグナルを送ります
   - `data/stop_requested.flag` は run_* スクリプトが外部停止を検知するためのフラグとして使われています

6. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または `data/paper_trading.db`

7. AI 機能（ニューススコア / レジーム判定）
   - OpenAI API キーを設定（OPENAI_API_KEY）
   - ニューススコア: kabusys.ai.score_news(conn, target_date, api_key=None)
   - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - これらは DuckDB 接続を受け取り、raw_news / prices_daily 等のテーブルを参照します
   - API 呼び出しはリトライ・フェイルセーフあり（失敗時はスコアをフォールバックする設計）

---

## 便利な CLI コマンド一覧

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

## ディレクトリ構成（主要ファイル）

リポジトリの src/kabusys 配下（抜粋）:

- __init__.py
- config.py
  - Settings クラス: 環境変数読み込み、自動 .env ロード、各種プロパティ
- config_setup.py
  - .env を対話式に生成・更新するウィザード
- validate_config.py
  - .env と config/*.yaml の事前検証ツール
- run_execution.py
  - ExecutionEngine を組み立てて起動するスクリプト（paper_trading は専用 DB）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・読み書きクラス
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス検査
  - trade_monitor.py — 注文滞留・約定価格異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限チェック
  - kill_switch.py — kill.flag による停止シグナル管理
  - alert_manager.py — LINE へのプッシュ通知実装
  - monitoring_engine.py — 各モニタを束ねる実行ループ
- execution/
  - （OrderManager, OrderRepository, ExecutionEngine 等 — 発注ロジック）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- data/
  - pipeline 等（DuckDB を扱うユーティリティ）
- ai/
  - news_nlp.py — ニュースの LLM スコアリング
  - regime_detector.py — マクロセンチメント + MA200 によるレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 向けの検証レポート生成

（上記は主要ファイルの抜粋です。完全なファイル一覧はリポジトリツリーを参照してください。）

---

## 運用上の注意 / トラブルシューティング

- プロセス優先度や CPU affinity を設定するために psutil を使っています。権限不足により設定に失敗してもプロセスは継続します（警告ログのみ）。
- Monitoring は運用環境にかかわらずデフォルトで本番用 sqlite_path を使います。ペーパートレード DB は run_execution 内で分離されます。
- OpenAI を使う機能は API キーが必須です。API 呼び出しの失敗はフォールバックロジックがあるため即座に致命的な失敗にはなりませんが、機能的な影響があります。
- `data/kill.flag` や `data/stop_requested.flag` 等のフラグファイルは手動での停止・再起動運用に使います。`.env` の KILL_FLAG_CLEAR_ON_START を有効にする設定は本番では推奨されません。
- DuckDB・SQLite のパスは .env で調整可能です。config/ 配下の YAML ファイル（存在するなら）も利用されますが、PyYAML が無い場合は YAML 検証はスキップされます。

---

## 開発・拡張メモ

- 多くのコンポーネントは純粋関数（副作用のない関数）または DB アクセス層とロジックが明確に分離されています。拡張や単体テストが容易な設計を意識しています。
- 将来的な改善候補として、銘柄ごとの lot_size をマスタ化する、価格取得のフォールバック強化、より詳細なモニタリング指標の追加などが挙げられます。
- テストを書いて CI を回すことを推奨します（モジュール単位で DuckDB のテスト用 DB を用いるのが簡便）。

---

必要であれば README に「環境変数の全一覧」「DB スキーマ（詳細）」「実際の運用手順（systemd / Supervisor 用ユニット例）」などのセクションを追加します。どの情報がより詳しく欲しいか教えてください。