# KabuSys

日本株自動売買システム（ライブラリ＋起動スクリプト群）のリポジトリ用 README（日本語）。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤ライブラリです。  
主な目的は以下のとおりです。

- 戦略（ファクター計算・シグナル生成）およびポートフォリオ構築のための研究モジュール
- 発注・実行エンジン（本番 / ペーパートレード）を起動するランタイム
- 監視（システム稼働状況、注文ログ、リスク監視）機能
- ニュース NLP / レジーム判定などの AI 補助機能
- ペーパートレードの検証用レポート生成ツール

設計方針として、DB（DuckDB / SQLite）を使った分析・ログ永続化、openai クライアントによるニュース評価、各種ユーティリティ（ログ設定、プロセス優先度）を備えます。

---

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution.py）
  - 本番 / paper_trading を環境で切替。paper_trading 時は MockBroker と別 SQLite（data/paper_trading.db）を使用
  - ExecutionEngine の起動、PID ファイル管理、停止フラグ監視
- 監視プロセス（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングし、監視ログを SQLite に保存
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）
  - 停止フラグ（data/stop_requested.flag）を検知して終了
- 設定ウィザード / 検証
  - `config_setup.py` : 対話式で .env を生成 / 更新
  - `validate_config.py` : .env / config/*.yaml の基本チェック（--strict で警告も FAIL 扱い）
- AI 機能
  - ニュース NLU による銘柄別センチメント（ai.news_nlp.score_news）
  - レジーム判定（ai.regime_detector.score_regime）
  - OpenAI（gpt-4o-mini）を利用（API キー必須）
- 研究モジュール
  - ファクター計算（research.factor_research）: momentum / volatility / value 等
  - 特徴量探索（research.feature_exploration）: 将来リターン計算 / IC / 統計サマリ
- ポートフォリオ構築
  - 銘柄選定・重み計算（portfolio.portfolio_builder）
  - ポジションサイズ計算（portfolio.position_sizing）
  - セクターキャップ / レジーム乗数（portfolio.risk_adjustment）
- ツール
  - ペーパートレード検証レポート（tools.paper_verification_report）

---

## 必要環境 / 依存パッケージ（代表例）

- Python 3.9+
- pip でインストールする主なパッケージ:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (validate_config の YAML 検証を行う場合)

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt がある場合はそれを利用してください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. 初回設定（.env）を作成:
   - 対話式ウィザード
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env を手動作成（下記必須キー参照）
4. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合:
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリ等（data/ logs/）は起動時に自動作成されることが多いですが、パーミッション等を確認してください。

必須環境変数（一部）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使用する場合）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

重要: 自動ロードされたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。既定ではプロジェクトルートの .env / .env.local を自動的に読み込みます。

サンプル .env（抜粋）
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 使い方（主要コマンド）

- 設定ウィザード（.env の作成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視プロセス起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  備考:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト: 60）
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag が存在するとループを終了します
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）へ書き込みます（環境にかかわらず本番 sqlite_path を使用）

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  備考:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を利用して本番 DB と分離されます
  - 起動時に data/execution.pid を作成し、停止は stop_requested.flag を作ることで実行エンジンを停止できます

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- ライブラリ関数の呼び出し（例: AI スコア付け、レジーム判定）
  Python スクリプト内や REPL から:
  ```py
  from kabusys.ai.news_nlp import score_news
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
  ```

---

## 停止 / Kill スイッチ

- 実行ループ（monitoring / execution）はプロジェクトルートの data/stop_requested.flag を検知すると安全に終了します。
- Kill Switch（自動停止判定）は data/kill.flag を生成して ExecutionEngine に停止を促します。kill.flag の存在は Settings.kill_flag_path（デフォルト data/kill.flag）で参照されます。
- 本番運用時の注意:
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアします（本番では 0 推奨）

---

## ロギング

- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging
- デフォルトログディレクトリ: logs/
- 各アプリ（app_name: "execution", "monitoring" 等）ごとに logs/<app_name>.log を日次ローテーションで保存（30 日分保持）
- 環境変数 LOG_DIR で変更、LOG_LEVEL でレベル制御

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋）

- kabusys/
  - __init__.py (バージョン等)
  - config.py — 環境変数 / .env 自動読み込み、Settings クラス
  - config_setup.py — .env 対話式ウィザード（CLI）
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite のスキーマ作成・永続化 API（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — （注文ログ監視）※実装ファイルあり
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信管理）※実装ファイルあり
  - execution/
    - execution_engine.py — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py — Broker クライアント生成（Mock / 実ブローカー）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行周りのユーティリティ
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み生成
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター制限 / レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py — IC / forward returns / 統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄センチメント取得
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロ NLP）
  - utils/
    - logging_setup.py — ロギング設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール

（注）上記は主要ファイルの概要です。実装ファイルはさらに細分化されています。

---

## 開発 / テスト時のメモ

- .env の自動ロードはプロジェクトルートの .env / .env.local を参照します。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続は分析（research / ai）で使用。DuckDB のファイルパスは DUCKDB_PATH で指定します（デフォルト data/kabusys.duckdb）。
- SQLite は監視ログ（monitoring.db）と paper_trading 用 DB（paper_trading.db）で使い分けます。
- OpenAI を利用する機能は API キーの利用制限や料金に注意してください。API 呼び出しはリトライ・フェイルセーフ実装あり。

---

## よくある操作例

- 監視を 30 秒間隔で実行（環境変数で上書き）
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- ペーパートレード環境で Execution を起動
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Kill Switch を手動で有効化（ExecutionEngine を止めたいとき）
  ```bash
  echo "manual kill requested" > data/kill.flag
  ```

---

## ライセンス / コントリビューション

（この README にはライセンス情報は含まれていません。実際のリポジトリには LICENSE ファイルを追加してください。）

---

README は以上です。必要であれば次の点について追記できます:
- 各モジュールのより詳細な API ドキュメント（関数・クラス仕様）
- CI / テスト実行方法
- 追加の環境変数一覧とデフォルト値一覧