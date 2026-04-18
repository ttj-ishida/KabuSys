# KabuSys

日本株向け自動売買システムのライブラリ / 実行スクリプト群（README）。

このリポジトリは戦略計算・ポートフォリオ構築・発注エンジン・監視・AI ツール類を含むモジュール設計になっています。ここではプロジェクト概要、主要機能、セットアップ、実行方法、ディレクトリ構成をまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を提供します。

- ファクター計算・特徴量探索（DuckDB を使ったバッチ分析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 発注エンジン（ExecutionEngine：kabuステーション等のブローカークライアント経由で発注）
- 監視（System / Trade / Risk のポーリング監視、kill switch）
- Paper Trading 検証・レポート生成
- ニュース NLP（OpenAI を使った銘柄別センチメント）
- 市場レジーム判定（AI と ETF MA を組合せ）

設計方針の一部：
- DuckDB / SQLite を使ったデータ永続化（分析 DB と監視 DB を分離）
- 環境変数（.env）による設定
- 本番/ペーパートレードの分離（paper_trading モードでは専用 DB / MockBroker を使用）
- 外部 API 呼び出しは明示的に制御し、フェイルセーフ実装を志向

---

## 機能一覧（抜粋）

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker（data/paper_trading.db に記録）
- 監視ループ起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- ファクター計算 / 研究用ユーティリティ（kabusys.research）
- ポートフォリオ構築（kabusys.portfolio）
- AI 関連
  - ニュースセンチメント: kabusys.ai.score_news（DuckDB 接続と target_date を与えて実行）
  - レジーム判定: kabusys.ai.regime_detector.score_regime

---

## 前提・依存関係

推奨 Python バージョン: 3.10+

主な Python パッケージ（用途に応じて）:
- duckdb
- psutil
- openai
- PyYAML（config 検証時に config/*.yaml をパースする場合）
- （必要に応じて）その他ブローカークライアントの依存

サンプルインストール（requirements.txt が無い場合の例）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## 主要な環境変数（デフォルト値 / 説明）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (default: development) — 有効値: development | paper_trading | live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db) — 監視 DB（monitoring は環境に関わらず本番 sqlite_path を参照）
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — ペーパートレード専用 DB
- PAPER_FILL_MODE (default: instant) — paper_trading の約定挙動（instant | partial | never | reject）
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (default: 0) — Execution 起動時に kill.flag を自動クリアするか
- MONITOR_POLL_INTERVAL (default: 60) — run_monitoring のポーリング間隔（秒）
- OPENAI_API_KEY — OpenAI 呼び出し用（AI モジュールで必須）

注意:
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

---

## セットアップ手順（簡易）

1. レポジトリをクローンし作業ディレクトリへ移動
2. 仮想環境を作成して有効化
3. 必要な Python パッケージをインストール（上記参照）
4. 初期設定ファイル（.env）を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、設定内容を確認して保存してください。
5. 設定検証:
   ```
   python -m kabusys.validate_config
   # 警告も厳密にチェックする場合:
   python -m kabusys.validate_config --strict
   ```
6. データディレクトリ（data/ や logs/）は自動で作成されますが、パーミッション等を確認してください。

---

## 使い方（主要コマンド）

- 実行エンジン起動
  - 通常:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード（.env で KABUSYS_ENV=paper_trading を設定）では MockBroker を使用し、data/paper_trading.db に注文ログを残します。

  実行の挙動:
  - 起動時に process priority を "high" に設定しようとします（権限がない場合は警告）。
  - stop フラグ (data/stop_requested.flag) が存在する場合は起動を行いません。
  - 起動中に stop フラグが作成されると ExecutionEngine.stop() を呼びスムーズに終了します。
  - PID ファイル: data/execution.pid を使用します（Settings.pid_file_path で変更可）。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は本番 sqlite_path（SQLITE_PATH）を使用して system_status / trade_logs / risk_logs 等を記録します。
  - data/stop_requested.flag を置くと監視ループが安全に終了します。
  - 監視は SystemMonitor / TradeMonitor / RiskMonitor を組み合わせ、必要に応じて kill.flag を書き込み ExecutionEngine 停止を誘発します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を個別指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
  - 出力により稼働率・注文成功率・レイテンシ等を確認できます。

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（再掲）
  ```
  python -m kabusys.validate_config
  ```

- AI 関連（ライブラリ呼び出し）
  - ニューススコア付与（プログラム内で呼ぶ）:
    ```py
    from kabusys.ai import score_news
    # duckdb_conn: duckdb.connect(...) の接続
    count = score_news(duckdb_conn, target_date, api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="sk-...")
    ```
  - 上の関数は OpenAI API キーが必要です。api_key 引数を省略すると環境変数 OPENAI_API_KEY を参照します。

---

## 停止・Kill Switch の仕組み

- run_execution / run_monitoring はプロジェクトの data/stop_requested.flag を監視しているため、停止したい場合は以下どちらかを行います:
  - stop フラグを作成:
    ```
    mkdir -p data
    touch data/stop_requested.flag
    ```
  - または ExecutionEngine 内部の kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は監視側が書き込み、Engine 側で検出されると停止します（kill.flag は明示的に作成・削除できます）。

- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアしますが、本番では危険なのでデフォルト 0 を推奨します。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル/モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / Settings 管理・自動 .env ロード
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクター制限・レジーム乗数
    - position_sizing.py — 株数計算・上限・rounding
  - research/
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — forward returns / IC / 統計量
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で銘柄別スコア作成
    - regime_detector.py — ETF MA と マクロ NLP を合成したレジーム判定
  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブル作成・読み書き層
    - system_monitor.py — システム状態・データ鮮度のチェック
    - trade_monitor.py — （発注ログ）トレード監視（ファイル内に定義あり）
    - risk_monitor.py — ドローダウン・ポジション数監視
    - monitoring_engine.py — 各 Monitor を束ねるループ実装
    - kill_switch.py — kill.flag 制御ユーティリティ
    - alert_manager.py — 外部通知（LINE 等）を送るマネージャ（実装に依存）
  - utils/
    - logging_setup.py — 統一ログ設定（コンソール + 日次ローテートファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は主要ファイルのみ抜粋しています。完全なファイル一覧はリポジトリを参照してください）

---

## 開発・デバッグのヒント

- ログはデフォルト logs/<app_name>.log に日次ローテートで出力されます（logs ディレクトリ）。必要なら LOG_DIR 環境変数で変更。
- DuckDB 接続は分析処理で多用します。大きなデータ処理を行う際はメモリ・IO のモニタリングを推奨します。
- AI 周りは API エラーやレートリミットを緩やかにリトライする実装ですが、試験時は小さいチャンクで実行するかテスト用のモックを使ってください。
- 設定検証ツールで YAML の構文チェックを行うには PyYAML をインストールしてください。

---

## FAQ（よくある質問）

Q: ペーパートレードと本番は完全に分離されますか？
A: はい。KABUSYS_ENV=paper_trading の場合は BrokerFactory が MockBroker を返し、発注ログは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます。本番用 monitoring は環境に関わらず SQLite_PATH（data/monitoring.db）を使用します。

Q: 監視や実行を停止する安全な方法は？
A: data/stop_requested.flag を作成すると安全にループを抜けます。KillSwitch（監視側）が条件を満たすと data/kill.flag を書き込んで ExecutionEngine に停止を促します。

---

以上がリポジトリの概要と基本的な使い方です。必要であれば各モジュールごとの詳細なドキュメント（API 使用例、関数仕様、戻り値の例、単体テストの書き方等）を追加で作成します。どの部分を深掘りしたいか教えてください。