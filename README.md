# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアライブラリと起動スクリプト群を含むリポジトリです。  
主な目的は、戦略（ファクター計算・シグナル生成）・ポートフォリオ構築・発注エンジン・監視・リスク管理・AI を用いたニュース解析などの機能をモジュール化して提供することです。  
実行時は .env や環境変数で挙動を切り替えられ、paper_trading（ペーパートレード）モードは本番データベースと完全に分離して動作する設計になっています。

---

## 主な機能一覧

- 環境設定管理
  - .env 自動読み込み / 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- 実行エンジン（ExecutionEngine）
  - Live / Paper トレード切替（paper_trading 用に MockBroker を使用）
  - 発注・注文管理・リスク管理・照合（reconciler）
- 監視（Monitoring）
  - システム稼働監視（CPU/メモリ/ディスク、プロセス死活）
  - 注文ログ監視（滞留注文, 約定異常など）
  - リスク監視（ドローダウン, ポジション上限）
  - Kill Switch による安全停止（kill.flag）
- ポートフォリオ構築
  - 候補選定、重み計算（等金額 / スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、リスクベース等）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 前提）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI 支援
  - ニュースのセンチメントスコアリング（OpenAI API を利用）
  - 市場レジーム判定（MA200 + マクロニュースを LLM で評価）
- ユーティリティ
  - 統一的なロギング設定（stdout + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - Paper Trading の検証レポート生成スクリプト

---

## 前提条件 / 依存ライブラリ（代表例）

動作に必要な代表的な Python パッケージ（環境に応じて適宜インストールしてください）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定ファイル検証を行う場合）

例:
```
pip install duckdb psutil openai PyYAML
```

プロジェクトに requirements.txt があればそれを使用してください:
```
pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置する

2. Python 依存パッケージをインストール

3. .env の作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成 / 更新します。API トークンやパスワード等はここで設定してください。

4. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   ```
   必須環境変数や config/*.yaml の存在などを検証します。`--strict` を付けると警告もエラー扱いになります。

5. データディレクトリの作成（必要に応じて）
   - デフォルトでは `data/` を使います（DuckDB・SQLite・PID・フラグファイルなど）。
   - ログは既定で `logs/` に出力します（LOG_DIR 環境変数で変更可）。

---

## 主要な環境変数（代表）

- 基本
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - LOG_LEVEL: ログレベル（DEBUG / INFO / ...）
- API 鍵
  - JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API（AI 機能を使用する場合）
- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- その他
  - LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

注意: 必須環境変数が未設定の場合は validate_config や Settings クラスでエラーになります。

---

## 使い方（起動 / 停止）

基本的にモジュールをモジュール実行します。

- 監視プロセスを起動（SystemMonitor ベースのポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒）。
  - 停止はプロジェクトルートの `data/stop_requested.flag` ファイルを作成することで監視ループが検知して終了します。

- 実行エンジン（ExecutionEngine）を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録されます（本番 DB と分離）。
  - 実行エンジンは `data/execution.pid` に PID を書きます。
  - 停止は `data/stop_requested.flag` を作成するか、ExecutionEngine 側から KillSwitch によって `data/kill.flag` が書かれることで安全停止されます。

- 設定検証（前述）
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。

- AI 関連例（プログラム API）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)

---

## 停止・Kill スイッチの仕組み（運用メモ）

- stop_requested.flag
  - run_monitoring / run_execution が監視している「停止要求」ファイル。
  - このファイルが存在するとメインループが終了またはエンジン停止処理を行います（外部からの手動停止に便利）。

- kill.flag
  - KillSwitch（monitoring 側の判定）によって書き込まれるフラグ。
  - ExecutionEngine はこれを検出して安全に発注停止・終了処理を行います。
  - 実運用では本番環境で自動クリアを有効にするのは危険（KILL_FLAG_CLEAR_ON_START は 0 推奨）。

---

## ログ

- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一管理されます。
- 出力先:
  - コンソール（stdout）
  - 日次ローテートされたファイル: logs/<app_name>.log（デフォルト）
- ログレベルは環境変数 LOG_LEVEL や setup_logging の引数で制御できます。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主な構成（抜粋）:

- src/kabusys/
  - __init__.py  (パッケージ情報)
  - config.py  (Settings クラス、.env 自動読み込み)
  - config_setup.py  (対話式 .env ウィザード)
  - validate_config.py  (設定検証 CLI)
  - run_monitoring.py  (SystemMonitor ポーリング起動)
  - run_execution.py  (ExecutionEngine 起動)
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (※実装ファイルがある想定)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/ (実行時に使用する data ディレクトリ — DB や flag ファイル等)
  - logs/ (ログ出力先)

（リポジトリにより細かなファイルは異なりますが、上記が主要モジュール群です）

---

## 開発者向けメモ

- DuckDB 接続は多くのリサーチ / AI モジュールで使用されます（prices_daily / raw_financials / raw_news 等のテーブルを前提）。
- MonitoringDB は SQLite を使った永続化層で、マイグレーション処理（カラム追加等）が冪等に行われます。
- AI 系（news_nlp, regime_detector）は OpenAI API（gpt-4o-mini 等）を利用します。API キーは OPENAI_API_KEY に設定してください。
- process_priority モジュールは psutil を使ってプロセス優先度を設定します。権限や OS により設定に失敗する場合があります（警告ログのみ）。

---

## よくあるコマンドまとめ

- .env を作る（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定チェック
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視起動
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## サポート / 追加情報

- 設定ファイルのテンプレート（.env.example）や config/*.yaml の生成スクリプト（scripts/generate_config.py）等がリポジトリに含まれている場合はそれに従ってください。
- 本 README はソース内の docstring と起動スクリプトの挙動を基に作成しています。実際の運用時は必ずローカル環境で validate_config によるチェックを行ってください。
- 本番（KABUSYS_ENV=live）では kill/stop フラグの自動クリア設定や LINE 通知（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）の未設定に注意してください。

---

必要であれば、README に含める具体的な .env のサンプルや systemd / supervisor 用のサービス定義テンプレート、Docker 化手順なども作成します。どの情報を追加しますか？