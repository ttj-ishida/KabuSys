# KabuSys

日本株自動売買システムの一部を切り出した Python パッケージ。  
このリポジトリには、監視 (monitoring)、実行エンジン起動スクリプト、ポートフォリオ構築やリサーチ用ユーティリティ、AI を使ったニュース NLP / レジーム判定、各種ツール類が含まれます。

---

## プロジェクト概要

KabuSys は自動売買を実行・監視するためのコンポーネント群を提供します。主な目的は以下です。

- ExecutionEngine（発注エンジン）の起動と運用（本番 / ペーパートレード対応）
- システム稼働状況・注文状況・リスク指標の監視とログ永続化（SQLite）
- ポートフォリオ構築・ポジションサイズ計算・リスク調整の純粋関数
- DuckDB を用いたリサーチ・ファクター計算
- OpenAI を使ったニュースセンチメント（ai_scores）と市場レジーム判定
- ペーパートレード検証レポート生成などのツール

---

## 主な機能一覧

- run_execution
  - ExecutionEngine を起動（KABUSYS_ENV によるペーパートレード分離）
  - ブローカークライアントは環境に応じて実装を切替
  - PID ファイル管理・停止フラグ検出（data/stop_requested.flag）
- run_monitoring
  - SystemMonitor のポーリングループ起動
  - MONITOR_POLL_INTERVAL で間隔上書き（デフォルト 60 秒）
  - 監視ログは SQLite（monitoring.db）へ永続化、分析は DuckDB
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み、ExecutionEngine 停止
  - AlertManager（実装ファイル参照）：アラート通知の集約（LINE など）
- Portfolio（純粋関数）
  - 候補選定、等重/スコア重み、リスク制約（セクターキャップ）、ポジションサイズ決定
- Research
  - DuckDB 接続でファクター（モメンタム/ボラティリティ/バリュー）計算
  - forward return / IC / 統計サマリー等
- AI
  - news_nlp.score_news(): OpenAI でニュース記事を銘柄ごとにセンチメント評価して ai_scores に保存
  - regime_detector.score_regime(): ma200 とマクロニュースセンチメントを合成し市場レジーム判定・永続化
- ツール
  - config_setup: .env の対話式ウィザード生成
  - validate_config: .env + config/*.yaml の起動前検証
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## 要件（主な依存）

- Python 3.10+
- pip パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml を検証する場合）
- SQLite（Python 標準ライブラリで利用）
- ネットワーク（OpenAI を利用する場合）

インストール例:
```bash
python -m pip install -r requirements.txt
# requirements.txt に上記パッケージを記載しておく想定
```

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化する。
2. 依存パッケージをインストールする（上記参照）。
3. 初期設定ファイル（.env）を作成する:
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - ウィザード実行後に .env が生成されます（機密情報を含むため Git 管理しないでください）。
4. 設定を検証する:
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにする（厳格モード）
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリ（デフォルト: data/）や DB（デフォルト: data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db）を準備する。スクリプト実行時に自動作成される場合があります。

重要なデフォルトパス／ファイル:
- DuckDB: data/kabusys.duckdb（環境変数: DUCKDB_PATH）
- Monitoring SQLite: data/monitoring.db（環境変数: SQLITE_PATH）
- Paper trading SQLite: data/paper_trading.db（環境変数: PAPER_TRADING_SQLITE_PATH）
- PID: data/execution.pid（Settings.pid_file_path）
- Stop フラグ: data/stop_requested.flag（run_* スクリプトが使用）
- Kill フラグ: data/kill.flag（Settings.kill_flag_path）

---

## 主要な環境変数

（.env に設定する主要な項目）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（例: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（例: data/paper_trading.db）
- KABUSYS_ENV: execution モード（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリア（0/1）

実行時オーバーライド:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方（起動・コマンド例）

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動
  - 通常:
    ```bash
    python -m kabusys.run_execution
    ```
  - ペーパートレード（.env の KABUSYS_ENV=paper_trading を使用）では MockBrokerClient を使用し、data/paper_trading.db に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。
  - 実行中に同フラグを作成すると停止処理を試みます。

- Monitoring 起動（ポーリング監視）
  ```bash
  # MONITOR_POLL_INTERVAL で秒間隔を上書き可能
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - デフォルト 60 秒間隔。
  - Monitoring は環境に関わらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを保存します。

- ペーパートレード検証レポート生成
  ```bash
  # 環境変数または --db で DB を指定可能
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- AI 関連（プログラムから呼び出す例）
  - ニューススコア保存（DuckDB 接続を渡す）
    ```python
    from kabusys.ai import score_news
    # conn は duckdb.connect(...) の接続オブジェクト
    n_written = score_news(conn, target_date, api_key="sk-...")
    ```
  - レジーム判定
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```

- 停止 / キルスイッチ
  - 管理者は data/kill.flag を生成すると ExecutionEngine に停止シグナルを送れます（KillSwitch が自動で作成することもあります）。
  - ExecutionEngine は起動時に kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START）を確認します。

---

## 注意事項 / 運用メモ

- .env には機密情報が含まれるため、Git 等にコミットしないでください。
- KABUSYS_ENV=live を使う場合は特に注意（本番発注が行われます）。validate_config の警告を必ず確認してください。
- MONITOR_POLL_INTERVAL が 0 以下の値や非整数の場合、デフォルト 60 秒にフォールバックします。
- ペーパートレードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH）。
- OpenAI API 呼び出しはレート制限やエラーが想定されており、モジュールはリトライ・フェイルセーフ処理を備えています。API キー管理に注意してください。
- process_priority の設定は OS により成功しない場合があります（権限不足など）。失敗時はログに警告が出ますが処理は継続します。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - config_setup.py
    - .env ウィザード（対話式）
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（schema 定義 + DB 操作用クラス）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 滞留注文・約定異常価格検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 Monitor の束ね・ループ基盤
    - alert_manager.py — アラート送信（LINE 等）集約（実装参照）
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...
    - ExecutionEngine のコア実装や注文管理
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 発注株数計算・キャップ/丸め
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラ/バリュー等の計算（DuckDB）
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py — OpenAI を用いたニュースセンチメント（ai_scores）書込み
    - regime_detector.py — ma200 + マクロセンチメント合成で市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 開発 / 貢献

- コードの責務分離を意識して実装されています（DB 層とビジネスロジックの分離、純粋関数群など）。
- 新機能追加や修正時はテスト・validate_config によるチェックを推奨します。
- 機密情報（.env）は必ず暗号化・安全管理をしてください。

---

README はここまでです。追加で以下の情報が欲しい場合は教えてください：
- 各 CLI / モジュールの詳細なコマンド引数一覧
- deployment（systemd / docker など）用の起動例
- サンプル .env.example ファイルの生成（内容のテンプレート）