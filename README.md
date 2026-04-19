# KabuSys

日本株自動売買システム「KabuSys」のリポジトリ内 README。  
このドキュメントはローカル実行および開発者向けに、プロジェクトの概要、機能、セットアップ、よく使うコマンド、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を提供するモジュール型システムです。

- 発注エンジン（ExecutionEngine）
- 監視・アラート（Monitoring、Kill Switch）
- ポートフォリオ構築（候補選定・配分・サイズ計算）
- リスク管理（ドローダウン監視・ポジション上限監視）
- リサーチ（ファクター計算・特徴量解析）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- ツール（ペーパートレード検証レポート等）
- ユーティリティ（ログ設定、プロセス優先度管理、設定ウィザード等）

設計上の注力点は「本番とペーパートレードの分離」「ルックアヘッドバイアス回避」「外部 API（OpenAI等）呼び出しの堅牢なリトライ」「DBは DuckDB / SQLite を用途別に使い分ける」点です。

---

## 主な機能一覧

- 設定管理
  - .env ウィザード（kabusys.config_setup）
  - 起動前の設定検証（kabusys.validate_config）
- 実行エンジン
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（BrokerClientFactory）
- 監視
  - 定期ポーリングでシステム状態を記録（CPU/メモリ/ディスク、プロセス生存）
  - 取引ログ・リスクログの永続化（SQLite）
  - Kill Switch：条件により ExecutionEngine を停止するフラグ生成
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重の重み計算
  - ポジションサイズ計算（リスクベース、利用可能現金に応じたスケーリング、単元株丸め）
  - セクター集中制限、レジーム乗数
- リサーチ
  - Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）等の解析
- AI（OpenAI）
  - ニュースの銘柄別センチメント（news_nlp）
  - マクロ＋ETF MA200 による日次レジーム判定（regime_detector）
- ツール
  - ペーパートレード検証レポート生成（tools.paper_verification_report）
- ユーティリティ
  - 統一的なログ設定（stdout + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity の設定（psutil 利用）

---

## 前提 / 必要ソフトウェア

- Python 3.10 以上（typing の | 型等を利用）
- pip（パッケージ管理）
- 主要 Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（任意、config 検証時に推奨）
- OS 標準の sqlite3（Python 標準モジュール）

必要パッケージはプロジェクトの requirements.txt がある場合はそれを使用してください。無ければ下記のように個別インストールします：

```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil openai PyYAML
```

注意: psutil によるプロセス優先度設定は OS と権限に依存します（root / 管理者権限が必要な場合があります）。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

   ```
   git clone <this-repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化し依存をインストール

   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows では .venv\Scripts\activate
   pip install duckdb psutil openai PyYAML
   ```

3. 初期環境変数ファイルの作成（対話式ウィザード推奨）

   ```
   python -m kabusys.config_setup
   ```

   ウィザードが .env を作成します。重要な必須項目：
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

4. 設定検証

   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合
   python -m kabusys.validate_config --strict
   ```

5. 必要な DB / データディレクトリの確認（.env の DUCKDB_PATH / SQLITE_PATH の親ディレクトリ等）  
   デフォルト：
   - DuckDB: data/kabusys.duckdb
   - monitoring SQLite: data/monitoring.db
   - paper trading SQLite: data/paper_trading.db

---

## 環境変数の主要説明（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: 実発注を行わず MockBroker を使用。DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- DB / ログ
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - LOG_LEVEL: ログレベル（デフォルト INFO）
  - LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- AI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 等で利用）
- 監視・停止
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（0/1、デフォルト 0。注意: 本番では危険）

自動で .env を読み込む仕組みがあり、プロジェクトルートの .env/.env.local を優先して読み込みます。自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## よく使うコマンド（実行例）

- 実行エンジン起動（本番／paper_trading は KABUSYS_ENV による）

  ```
  # 本番/開発/ペーパートレード切替は .env の KABUSYS_ENV を設定
  python -m kabusys.run_execution
  ```

  - paper_trading の場合は MockBroker を使用し、データは data/paper_trading.db に記録されます。

- 監視ループ起動

  ```
  python -m kabusys.run_monitoring
  ```

  - ポーリング間隔を上書きするには環境変数 MONITOR_POLL_INTERVAL を設定（秒）。
  - 監視は .env にある sqlite_path（デフォルト data/monitoring.db）に書き込みます（監視は環境に関わらず本番 sqlite_path を使用します）。

- 停止方法
  - 両スクリプトはプロジェクトルートの data/stop_requested.flag の存在を監視し、存在すると安全に終了します。手動で停止させたい場合はファイルを作成してください。

    ```
    touch data/stop_requested.flag
    ```

  - ExecutionEngine を強制停止させる自動手段（Kill Switch）は内部的に data/kill.flag を作成します。手動で kill.flag（KABUSYS の kill flag path）を作ることで Engine を停止させることも可能ですが、本番では慎重に扱ってください。

- 設定ウィザード / 検証

  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート（ツール）

  ```
  # デフォルト DB を使用
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

---

## ログ・DB・PID について

- ログ
  - デフォルトで stdout にも出力され、ログファイルは logs/<app_name>.log（日次ローテーション、30日保持）に出力されます。
  - 例: app_name="execution" → logs/execution.log
  - ログレベルは LOG_LEVEL で制御。

- DB
  - DuckDB: 分析用（prices_daily / raw_financials 等）
  - SQLite: 監視・発注履歴用（monitoring.db）、ペーパートレードは paper_trading.db に分離

- PID / フラグ
  - 実行時に PID を data/execution.pid 等へ出力（設定で変更可）
  - 停止フラグ: data/stop_requested.flag（run_* スクリプトのループ停止検知）
  - Kill Switch: data/kill.flag（KillSwitch が書き込み）

---

## ディレクトリ構成（主要ファイル / モジュール説明）

（src/kabusys 以下）

- __init__.py
  - パッケージ定義・バージョン

- config.py
  - 環境変数読み込み / Settings クラス（アプリ設定の集中管理）

- config_setup.py
  - .env 作成の対話式ウィザード

- validate_config.py
  - .env と config/*.yaml の起動前検証ツール

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 切替、DB 接続、スレッド起動）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）

- utils/
  - logging_setup.py: ルートロギングの統一設定（stdout + TimedRotatingFileHandler）
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py: SQLite テーブル作成・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: システム状態（CPU/MEM/DISK）とデータ鮮度監視
  - trade_monitor.py: （ファイル内に見えませんが存在する想定）取引ログ監視・滞留注文検出
  - risk_monitor.py: ドローダウン監視・ポジション上限監視
  - kill_switch.py: Kill Switch（条件を満たせば kill.flag を書き込む）
  - alert_manager.py:（アラート送信の仲介、LINE 等に通知する実装想定）
  - monitoring_engine.py: 複数 Monitor を束ねて動かすエンジン

- execution/
  - execution_engine.py: 実行セッションの中心（注文の送信、注文管理等）
  - broker_factory.py: ブローカークライアント生成（本番 vs Mock）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py: 発注・リスク管理の構成要素

- portfolio/
  - portfolio_builder.py: 候補選定、重み計算（等配分・スコア加重）
  - position_sizing.py: 発注株数計算（risk_based / equal / score）
  - risk_adjustment.py: セクターキャップ、レジーム乗数

- research/
  - factor_research.py: Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン計算、IC、統計サマリ

- ai/
  - news_nlp.py: ニュース集約 → OpenAI でセンチメント → ai_scores へ書き込み
  - regime_detector.py: ETF MA200 とマクロニュースを合成して market_regime を決定

- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成

---

## 注意事項 / 運用上のヒント

- 本番運用時は KABUSYS_ENV=live を慎重に扱ってください。validate_config は live 時に注意喚起を出します。
- KILL_FLAG_CLEAR_ON_START=1 を本番で利用するのは危険です（kill.flag が自動でクリアされるため、保護機構が失効します）。
- process priority の設定や CPU affinity の変更は権限・プラットフォーム依存です。失敗した場合は警告ログを出して継続します。
- OpenAI API を利用する機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しにはレート制限やエラーの扱いを組み込んでいますが、利用コストに注意してください。
- DuckDB / SQLite のファイルは .env の設定で任意のパスに変更可能です。運用環境ではバックアップやディスク容量に注意してください。
- DB マイグレーションやスキーマ変更は、monitoring_db.init_monitoring_db が幾つかの後方互換対応（列追加）を実装していますが、重大なスキーマ変更は慎重に行ってください。

---

## 開発 / 貢献

バグ修正や機能拡張の提案は Issue を立ててください。Pull Request の際は relevant tests / linters の実行をお願い致します（このリポジトリのテスト方針がある場合はそれに従ってください）。

---

以上が README の基本内容です。必要であれば、以下を追加で生成できます：

- 具体的な config/*.yaml の説明（system_config.yaml 等）
- 各モジュールの API 使用例（関数レベルの短いサンプル）
- デプロイ手順（systemd / supervisor / Dockerfile など）

どれをご希望か教えてください。