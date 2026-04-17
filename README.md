# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買・リサーチ・監視を行うための内部ライブラリ群です。戦略の研究、ポートフォリオ構築、注文実行、監視・アラート、AI を使ったニュース解析などの機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的を持ったモジュール群です。

- 戦略リサーチ（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定、重み算出、株数決定）
- 注文実行基盤（ExecutionEngine。paper_trading モードあり）
- 監視（System / Trade / Risk）と Kill Switch による自動停止
- AI を用いたニュースセンチメント解析・市場レジーム判定（OpenAI）
- 運用補助ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）
- 永続化: SQLite（監視・取引ログ等） / DuckDB（時系列・リサーチデータ）

設計方針の一部：
- 本番用・ペーパートレードは DB を分離
- ルックアヘッドバイアス対策（関数は date 引数などを直接参照しない設計）
- フェイルセーフ：API 失敗やデータ不足時はシステムを停止させずログ/警告で対応

---

## 主な機能一覧

- config 管理（.env 自動ロード、Settings クラス）
- 対話式 .env ウィザード（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
- ExecutionEngine の起動（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading で MockBrokerClient を用い、別 DB に記録
  - 起動時にプロセス優先度を設定、停止フラグを監視
- 監視ループ（kabusys.run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行
  - kill.flag による停止、監視ログは SQLite に永続化
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能
- MonitoringDB: system_status / trade_logs / positions / risk_logs / dashboard テーブル管理
- Trade / Risk の自動アラート／Kill Switch 発動ロジック
- Portfolio モジュール（候補選定、等分配/スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数）
- Research モジュール（momentum/value/volatility 等のファクター計算、forward returns、IC 計算、統計サマリー）
- AI モジュール
  - news_nlp: raw_news を集約して OpenAI へ送信し銘柄ごとの ai_score を ai_scores テーブルへ書き込み
  - regime_detector: ETF 指標と LLM センチメントを合成して market_regime を算出・保存
- ツール: paper_verification_report（ペーパートレードの検証レポート生成）

---

## 必要要件（推奨）

- Python 3.10+
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML 検証を行う場合）
- SQLite（標準ライブラリ sqlite3 を使用）
- ネットワークアクセス（kabuステーション API / OpenAI を利用する場合）

※ requirements.txt はこのスニペットには含まれていません。実運用ではプロジェクトの requirements を用意してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 生成後、内容を確認・編集（.env は絶対に Git にコミットしないでください）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. DB ディレクトリの準備
   - デフォルトでは data/ 配下に DuckDB・SQLite を置きます。必要に応じて環境変数でパスを変更してください。

---

## 主要な環境変数（概要）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）
  - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。run_monitoring で参照）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動消去するか（0/1）
- PID_FILE_PATH / KILL_FLAG_PATH: ファイルパス（デフォルトは data/ 以下）

Settings クラス（kabusys.config）で詳しく取得可能です。

---

## 使い方（主要コマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 特記事項:
    - 起動時にプロセス優先度を "high" に設定します（可能なら）
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient と paper_trading DB を使用
    - data/stop_requested.flag が存在すると起動をスキップ・もしくは実行中に停止します
    - 実行中は data/execution.pid に PID を書きます

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 特記事項:
    - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視データは Settings.sqlite_path（監視は常に本番 sqlite_path を使用）
    - stop_requested.flag の検出でループを終了します

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）

- AI / リサーチ関数（Python からの呼び出し例）
  - DuckDB 接続を作り、関数を呼ぶことで処理できます（CLI 実行用ラッパーは一部のみ実装）。
  - 例（news_nlp のスコアを生成）:
    - import duckdb
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, target_date=date(2026,4,10), api_key="...")

  - 注意: OpenAI API を利用する場合は OPENAI_API_KEY が必要です。関数は API 失敗時にフォールバックやログ出力を行いますが、API キー未設定の場合は例外になります。

---

## 停止 / Kill Switch の挙動

- KillSwitch（data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送ります。MonitoringEngine が評価条件に応じて書き込みます。
- run_execution / run_monitoring は data/stop_requested.flag を見て起動停止を行います（プロセス間の停止同期に利用）。
- Settings に kill フラグのパスや自動クリア設定があります（KILL_FLAG_CLEAR_ON_START）。

---

## ディレクトリ構成（主要ファイル）

（ルート: src/kabusys 以下）

- __init__.py
- config.py               — 環境変数読み込み・Settings クラス
- config_setup.py         — .env の対話式ウィザード
- validate_config.py      — 起動前の設定検証 CLI
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py           — ニュースを LLM でスコアリングして ai_scores に書き込み
  - regime_detector.py    — 市場レジーム判定と保存
- monitoring/
  - monitoring_db.py      — SQLite テーブル初期化・簡易 ORM
  - system_monitor.py     — CPU/Mem/Disk/データ鮮度/プロセス監視
  - trade_monitor.py      — 注文滞留・約定異常監視
  - risk_monitor.py       — ドローダウン・ポジション上限監視
  - kill_switch.py        — kill.flag の生成/削除/判定
  - monitoring_engine.py  — 各 Monitor を束ねるループ
  - alert_manager.py      — （アラート送信の管理。未完：ファイル省略）
- execution/
  - （order_manager, execution_engine, broker_factory 等 — 実行ロジック）
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数決定・投下資金スケーリング
  - risk_adjustment.py     — セクター制限・レジーム乗数
- research/
  - factor_research.py     — モメンタム/ボラ/バリュー等の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/                    — 実行時に生成される DB / PID / flag ファイル（git 管理外推奨）

（上記は主要ファイルの抜粋です。細かい実装は各モジュールを参照してください。）

---

## 開発・運用メモ / 注意点

- .env は機密情報を含むため Git にコミットしないでください（config_setup にも注意書きあり）。
- KABUSYS_ENV によって実行挙動が変わるので、本番（live）時は特に LINE アラートや kill フラグの設定を確認してください（validate_config のライブガードあり）。
- AI を使う機能はコストがかかります。テスト時はモック関数や API キーを注意して扱ってください（news_nlp._call_openai_api 等はテストでパッチ可能）。
- DuckDB/SQLite スキーマは init_monitoring_db によってマイグレーションを行います。既存 DB と互換性の必要がある場合は注意してください。
- run_execution/run_monitoring はプロセス優先度を上げます。権限がない環境では設定失敗を警告でスキップします。

---

## トラブルシューティング（よくある項目）

- .env が読み込まれない
  - .env はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に自動ロードします。自動ロードを無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- OpenAI 関連でエラーが出る
  - OPENAI_API_KEY が設定されているか、API のレート制限やネットワークを確認してください。news_nlp / regime_detector はリトライ処理を持ちますが、キー未設定の場合はエラーとなります。
- ExecutionEngine が起動しない
  - data/stop_requested.flag が存在しないか確認してください（存在すると起動をスキップします）。PID ファイルの整合性や kill.flag の設定も確認。

---

README は簡潔に要点をまとめています。各モジュールの詳細な挙動や API（関数引数・戻り値）はソースコードの docstring を参照してください。追加で README に含めたいサンプルや運用手順があれば教えてください。