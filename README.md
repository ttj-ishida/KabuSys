# KabuSys

日本株自動売買フレームワークのコアライブラリ群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI ニューススコアリング 等）。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム（バックエンドライブラリ）です。主な機能は次のとおりです。

- 発注とリスク管理を担う ExecutionEngine（本番 / ペーパートレード対応）
- システム監視・アラート・Kill Switch 機能
- ポートフォリオ構築（候補選定、重み計算、ポジションサイジング）
- ファクター計算・特徴量探索（DuckDB 利用）
- ニュース NLP によるセンチメントスコアリング（OpenAI）
- 設定ウィザード・設定検証スクリプト、運用支援ツール（Paper Trading レポート）
- ロギング・プロセス優先度設定などユーティリティ

設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス回避」「外部 API 呼び出し部分は鍵（APIキー）で制御」「フェイルセーフ（API失敗時は安全にフォールバック）」を重視しています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine：注文の発行・管理、OrderManager、RiskManager、Reconciler 等の組み立て
  - ペーパートレード対応（KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用、data/paper_trading.db に記録）
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス監視、データ鮮度チェック
  - TradeMonitor：注文滞留・約定異常などのチェック（該当コードあり）
  - RiskMonitor：ドローダウン / 保有上限監視、ダッシュボード永続化
  - KillSwitch：条件に応じて data/kill.flag を作成し ExecutionEngine を停止
  - MonitoringEngine：上記を束ねるポーリングエンジン（MONITOR_POLL_INTERVAL で間隔制御）
- Portfolio
  - 候補選定（score によるソート）、等重・スコア重み、セクター制限、レジーム乗数、ポジションサイズ計算（lot 単位）
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI
  - news_nlp：ニュース記事を OpenAI でセンチメント評価し ai_scores に格納
  - regime_detector：ETF（1321）の MA とマクロニュースを組み合わせてレジーム判定
- ツール
  - config_setup：対話式 .env 生成ウィザード
  - validate_config：環境変数・config/*.yaml の事前検証
  - paper_verification_report：ペーパートレードの検証レポート生成
- Utils
  - ロギング設定（日次ローテート + stdout）
  - プロセス優先度 / CPU affinity 設定

---

## 前提・依存関係

- Python 3.10+（typing の | 記法などを使用）
- 推奨 Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML をパースする場合）
- SQLite（標準ライブラリ sqlite3 を使用）
- ネットワーク接続（OpenAI を使う場合）

requirements.txt を用意している場合はそれを使用してください。手動でインストールする場合の例:

```bash
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン／配置して仮想環境を作成・有効化する。

2. 依存パッケージをインストールする。

3. 環境変数の設定
   - 推奨: 対話式ウィザードで .env を作る
     ```bash
     python -m kabusys.config_setup
     ```
     ウィザードに従って J-Quants トークン、kabu API パスワード などを入力します。
   - 必須環境変数
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定するか、score_news / score_regime 呼び出し時に引数で渡す
   - 監視設定
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH（必要に応じて上書き）
   - 自動ロード:
     - プロジェクトルートの .env / .env.local は起動時に自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

4. 設定検証（任意だが推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの作成（logs/ data/ 等は自動作成されますが念のため）
   ```bash
   mkdir -p data logs
   ```

---

## 使い方

- ExecutionEngine の起動（本番 / ペーパートレードに応じて .env の KABUSYS_ENV を設定）
  ```bash
  python -m kabusys.run_execution
  ```
  特徴:
  - 起動時にプロセス優先度を「high」に設定します（プラットフォーム依存、設定に失敗した場合は警告）。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録されます。
  - 起動時に data/stop_requested.flag があると起動を行わず終了します。
  - 実行中に data/stop_requested.flag を置くことでスレッドの停止を促します。

- Monitoring の起動
  ```bash
  # ポーリングループを起動
  python -m kabusys.run_monitoring
  ```
  オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60秒）。
  - 監視は Settings の sqlite_path（デフォルト data/monitoring.db）を使用します（monitoring は環境にかかわらず本番 sqlite_path を使用する設計）。
  - 監視ループを停止するにはプロジェクトルートの data/stop_requested.flag を作成します。

- Kill Switch の利用
  - KillSwitch は監視結果に基づき data/kill.flag を作成します。ExecutionEngine 起動時に Kill Flag が存在する場合、起動を抑止または停止処理を行います。
  - Settings.kill_flag_clear_on_start=1 にすると起動時に kill.flag を自動でクリア（本番では推奨しません）。

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート（ツール）
  ```bash
  # デフォルト DB パスを使用
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（ニューススコア、レジーム判定）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、関数呼び出し時に api_key を渡してください。
  - 例（ライブラリ呼び出し）:
    ```python
    from kabusys.ai import score_news
    # DuckDB 接続を渡して呼び出す
    n = score_news(duckdb_conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```

- ログ
  - デフォルトは logs/ に日次ローテートで出力されます。LOG_DIR 環境変数で変更可能。
  - 各アプリ名（execution / monitoring など）ごとに logs/<app_name>.log に出力されます。

---

## 運用上の注意

- KABUSYS_ENV を `live` にする際は設定や LINE 通知の有効性を十分に確認してください（validate_config は live 時の追加注意を出します）。
- Kill Switch / stop_requested.flag の扱いに注意してください。特に本番で KILL_FLAG_CLEAR_ON_START=1 にするのは危険です（デフォルトは 0）。
- OpenAI を使う処理は外部 API 呼び出しが発生するため、API 利用料・レート制限に注意してください。失敗時はフォールバック処理が実装されていますが、期待どおり動作しない可能性があります。
- DuckDB / SQLite のファイルパスは .env で指定できます。パスの親ディレクトリが存在しない場合、起動時に作成されることがありますが、事前に作成しておくことを推奨します。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイルと役割を示します（src/kabusys 以下）。

- __init__.py
  - パッケージ初期化（バージョン、エクスポート）

- config.py
  - Settings クラス: 環境変数の取得、.env の自動読み込み、検証ルール

- config_setup.py
  - 対話式 .env 生成ウィザード

- validate_config.py
  - 起動前の設定検証 CLI（必須環境変数・YAML ファイル・パスチェック等）

- run_execution.py
  - ExecutionEngine 起動スクリプト（スレッド実行・停止フラグ対応）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）

- utils/
  - logging_setup.py: 統一ロギング設定（stdout + TimedRotatingFileHandler）
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py: SQLite ベースの永続化レイヤ（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py: （注文まわりの監視実装ファイル）
  - risk_monitor.py: ドローダウン/ポジション上限監視
  - kill_switch.py: kill.flag の生成/削除ロジック
  - monitoring_engine.py: 各モニタを束ねるポーリングエンジン
  - alert_manager.py: （アラート送信の実装）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 発注・リスク管理の主要コンポーネント

- portfolio/
  - portfolio_builder.py: 候補選定・重み付け
  - position_sizing.py: 株数計算・資金配分・単元丸め
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: momentum/volatility/value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン / IC / 統計サマリ

- ai/
  - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores に保存
  - regime_detector.py: マクロニュース + ETF MA によるレジーム判定

- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成スクリプト

- data/
  - （runtimeで生成されるファイル）monitoring.db, paper_trading.db, kill.flag, execution.pid, stop_requested.flag など

---

## よく使うコマンドまとめ

- .env を対話式で作る:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動:
  ```bash
  python -m kabusys.run_execution
  ```

- 監視ループ起動:
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要があれば、README に「開発環境でのユニットテスト実行方法」「CI 設定例」「詳細な設定項目一覧（.env の説明）」などの追加セクションを追記します。どの情報を優先して追加しますか？