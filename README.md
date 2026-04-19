# KabuSys

KabuSys は日本株の自動売買システム用ライブラリ／実行スクリプト群です。本リポジトリは以下の主要機能を提供します：

- 注文実行エンジン（ExecutionEngine）：ブローカーとの接続、注文管理、リスク管理、レコンシリエーション
- 監視（Monitoring）：システム稼働状態、注文ログ、リスク指標のポーリングとアラート / Kill Switch
- ポートフォリオ構築（Portfolio）：候補選定、重み付け、ポジションサイズ計算、セクター制約など
- リサーチ（Research）：ファクター計算、将来リターン、IC 計算、特徴量解析
- AI 支援モジュール（AI）：ニュースの NLP スコアリング、マーケットレジーム判定（OpenAI を利用）
- ユーティリティとツール類：.env ウィザード、設定検証、Paper Trading 検証レポート生成 等

この README では概要・機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## 機能一覧（概要）

- Execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカー抽象化（MockBrokerClient / 実ブローカー）
  - OrderManager / Reconciler / RiskManager を備えた ExecutionEngine
  - PID ファイル管理、停止フラグ監視
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス、データ鮮度の監視
  - TradeMonitor: 注文滞留・約定異常検出（trade_logs を利用）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - MonitoringEngine: 各モニタを束ねてポーリング、KillSwitch 判定、AlertManager に通知
  - SQLite ベースの監視 DB（冪等初期化、マイグレーション機能あり）
- Portfolio（純粋関数群）
  - 候補選定（select_candidates）
  - 等配分 / スコア加重配分
  - ポジションサイズ計算（risk_based、equal、score）
  - セクターキャップ、レジーム乗数
- Research
  - モメンタム / ボラティリティ / バリュー系ファクター計算（DuckDB 接続）
  - 将来リターン、IC、統計サマリー（外部ライブラリ依存を極力排除）
- AI
  - news_nlp: raw_news を集約し OpenAI（gpt-4o-mini 等）で銘柄ごとにセンチメントスコア化
  - regime_detector: ETF MA とマクロニュースから市場レジーム判定
  - OpenAI の呼び出しは堅牢なリトライ・検証ロジックを実装
- ツール
  - config_setup.py: .env の対話式ウィザード（初期作成・更新）
  - validate_config.py: .env / config/*.yaml の検証 CLI（--strict モードあり）
  - tools.paper_verification_report: Paper Trading 結果の検証レポート生成

---

## 必要条件（依存パッケージ・環境）

主な Python パッケージ（抜粋）:

- python >= 3.10（型注釈などの記法を利用）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の内容検証を行う場合）
- その他標準ライブラリ

requirements.txt は同梱されていない想定のため、最低限以下をインストールしてください：

例：
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（必要に応じてバージョン固定や追加パッケージを導入してください）

---

## 環境変数（主要）

必須（実行前に設定／.env に記載）:

- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意または推奨:

- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使用する場合）
- PAPER_FILL_MODE — ペーパートレードの約定方式（instant/partial/never/reject、デフォルト instant）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするフラグ（0/1、デフォルト 0）

その他設定はコードの Settings クラス（kabusys.config）を参照してください。

サンプル .env（最低限）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

※ .env は絶対に機密情報を含めたまま Git にコミットしないでください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-directory>
   ```

2. 仮想環境作成・依存パッケージインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai PyYAML
   ```

3. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - 既存 .env があれば読み込み、Enter で既存値を再利用できます。
   - 作成後、`python -m kabusys.validate_config` で検証してください。
   - 本番（live）の場合は LINE トークン等のアラート設定を忘れずに。

4. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

5. DB 初期化
   - 実行スクリプトは起動時に必要なテーブルを作成します（init_monitoring_db）。

---

## 使い方（主要スクリプト）

- 設定ウィザード（.env 作成・更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告もエラー扱い
  ```

- ExecutionEngine（取引エンジン）起動
  - 通常起動（KABUSYS_ENV に応じて Paper / Live を自動切替）
  ```
  python -m kabusys.run_execution
  ```
  - 実行挙動:
    - プロセス優先度を high に設定し（set_process_priority）
    - Paper Trading の場合は settings.paper_sqlite_path を使用して DB を分離
    - data/execution.pid に PID を書き、data/stop_requested.flag の存在で停止
    - Kill Switch（data/kill.flag）は Monitoring 側により書き込まれる

- Monitoring（ポーリングループ）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
  - 監視は本番 sqlite_path を利用（KABUSYS_ENV に関係なく監視 DB は本番 path が使われる点に注意）
  - プロセス優先度を high に設定します

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。`--db PATH` または環境変数 PAPER_TRADING_SQLITE_PATH で指定可。

- AI 機能（プログラム的に呼び出す）
  - ニューススコアリング:
    ```python
    from kabusys.ai import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date, api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```

停止・Kill の仕組み:
- run_execution は data/stop_requested.flag の存在を監視して停止します（起動前に存在する場合は起動しない）。
- monitoring.kill_switch はリスク条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。ExecutionEngine 側は kill.flag の扱いをチェックして停止するよう設計されています。
- kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START=1 を使えますが、本番では 0 推奨です。

ログ:
- ログは stdout とログファイルの両方に出力されます（logs/<app_name>.log、日次ローテーション、30日分保持）。
- app_name は起動スクリプトにより "execution" / "monitoring" 等が指定されます。

---

## ディレクトリ構成（主要ファイル／モジュール）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み / Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - execution/  — 実行系（Engine, OrderManager, BrokerFactory など）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層
    - system_monitor.py — システム監視
    - trade_monitor.py — 注文監視（滞留・異常）
    - risk_monitor.py — ドローダウン等の監視
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — Kill Switch 実装
    - alert_manager.py — （通知/アラート）※実装に応じて存在
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI を利用）
    - regime_detector.py — 市場レジーム判定
  - data/ — 実行時に使う data ディレクトリ（DB、pid、flag ファイル等）
  - utils/
    - logging_setup.py — 統一ログ設定
    - process_priority.py — プロセス優先度（Windows/Linux 向け抽象化）
  - monitoring/monitoring_db.py — SQLite スキーマ初期化と永続化 API

注意：上記はソース構成の要約です。細かい実装・クラス関係は各モジュールのドキュメントを参照してください。

---

## 運用上の注意点

- .env に機密情報を含めたままバージョン管理しないこと（config_setup にも警告コメントあり）。
- 本番（KABUSYS_ENV=live）では kill_flag の自動クリアや LINE 通知設定などを慎重に確認すること（validate_config が追加チェックを行います）。
- AI 機能を使う際は OPENAI_API_KEY を適切に管理し、API 利用制限や費用に注意してください。
- Paper Trading は本番 DB と分離されます（settings.paper_sqlite_path を使用）。Paper 環境では MockBrokerClient を使用します。
- ログディレクトリ作成に失敗した場合はファイル出力が無効化され stdout のみになります。ログの保存先は LOG_DIR で変更可能です。
- プロセス優先度設定は psutil によるため、権限やプラットフォームにより一部機能が無効化されることがあります（警告ログが出ます）。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動（ポーリング）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README に書かれている事項はリポジトリの現行実装（コード内の docstring / コメント）に基づいています。詳細な実装や拡張、運用ルールは各モジュールのソースコメントを参照してください。必要であれば README にデプロイ手順（systemd ユニット例 / Dockerfile / CI 設定）や追加の運用ドキュメントを追記します。必要な内容を教えてください。