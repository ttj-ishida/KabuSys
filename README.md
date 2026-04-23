# KabuSys

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。策略（Research / Signal） → ポートフォリオ構築 → Execution（発注）という流れと、システム監視 / リスク監視 / アラート / ペーパートレード検証など運用に必要な周辺機能群を含みます。

バージョン: 0.1.0

---

## 概要

主な設計方針と特徴：

- モジュール分割により研究・バックテスト・本番実行・監視を分離
- DuckDB（分析用）と SQLite（監視 / 発注履歴用）を併用
- Paper Trading（ペーパートレード）を本番 DB と分離（data/paper_trading.db）
- OpenAI を用いたニュース NLP / レジーム判定を統合可能（API キー必要）
- 設定は .env ファイルまたは環境変数で管理。対話式ウィザード・検証 CLI を提供
- ロギングは統一インターフェース（stdout + 日次ローテートファイル）
- Kill Switch（フラグファイル）による外部停止・安全停止の仕組み

---

## 主な機能一覧

- 実行系
  - ExecutionEngine（発注エンジン、リスク管理・注文管理・リコンシリエーションを統合）
  - Broker クライアントの切り替え（KABUSYS_ENV=paper_trading では MockBrokerClient を使用）
- 監視
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態・データ鮮度の監視
  - TradeMonitor：注文滞留・約定異常等の監視（コード中に参照あり）
  - RiskMonitor：ドローダウン・ポジション上限の検出とログ記録
  - MonitoringEngine：上記監視をポーリングし Kill Switch / アラートを統合
  - monitoring DB（SQLite）管理ユーティリティ（テーブル作成・マイグレーション）
- ポートフォリオ構築
  - 候補選定、等配分・スコア加重配分、リスクベースポジションサイズ計算
  - セクターキャップ適用、レジーム乗数算出
- 研究（Research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 将来リターン計算、IC（Information Coefficient）計算、要約統計
- AI
  - news_nlp: OpenAI（gpt-4o-mini 等）でニュースを銘柄毎にセンチメント付与して ai_scores に書き込み
  - regime_detector: ETF の ma200 乖離 + マクロニュースで市場レジーム判定・テーブル書込
- ツール
  - ペーパートレード検証レポート生成スクリプト（paper_verification_report）
- 設定・運用
  - config_setup.py：対話式で .env を生成
  - validate_config.py：設定検証 CLI（--strict オプションあり）
  - utils: ログ設定、プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてプロジェクトルートへ移動

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境の作成（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール（最低限の想定依存）

   ```
   pip install duckdb openai psutil pyyaml
   ```

   備考：
   - sqlite3 は標準ライブラリで提供されます。
   - PyYAML は config/*.yaml の中身検証に使用します（省略可）。
   - requirements.txt がプロジェクトに含まれている場合は `pip install -r requirements.txt` を使用してください。

4. 初期設定 (.env) の作成

   - 対話式ウィザードで作成：

     ```
     python -m kabusys.config_setup
     ```

   - もしくは .env.example を参考に手動で `.env` を作成してください。

5. 設定の検証

   ```
   python -m kabusys.validate_config
   # 警告を厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```

---

## 環境変数（主なもの）

必須（最低限）：
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション・デフォルト：
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート用（任意）
- OPENAI_API_KEY: OpenAI API を使う機能で必要
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- PID_FILE_PATH / KILL_FLAG_PATH: ファイルパス上書き可能

設定は .env に書いておくことを推奨（.env は Git にコミットしない）。

---

## 使い方（実行例）

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 監視プロセス起動（SystemMonitor ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - 監視プロセスはデフォルトで本番 sqlite_path を使用（監視ログは常に本番 DB に書き込む設計）。

- 実行（ExecutionEngine）起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と完全分離）。
  - 起動前に data/stop_requested.flag が存在する場合は起動を見送り終了します。
  - 停止は data/stop_requested.flag を作ることで実行スレッドに検知され安全停止します。

- ペーパートレード検証レポート（コマンドライン）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI スコアリング / レジーム判定（ライブラリとして呼び出し）
  - news NLP:
    from kabusys.ai.news_nlp import score_news
    - 引数に DuckDB 接続と target_date、api_key（または環境変数 OPENAI_API_KEY）を渡す
  - regime detector:
    from kabusys.ai.regime_detector import score_regime

- 停止 / Kill Switch
  - 監視側から Kill Switch がトリガーされると data/kill.flag が書かれ、ExecutionEngine 側で停止判定に使用されます。
  - 外部から強制停止したい場合は kill.flag を作成してください（実運用では慎重に扱ってください）。

---

## ログ

- ログは標準出力（stdout）とファイルの両方に出力されます。
- デフォルトログディレクトリ: logs/
- ログファイル名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
- 日次ローテーション（30日分保持）

ログ設定は kabusys.utils.logging_setup.setup_logging を各起動スクリプトが呼び出して統一されています。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトは src/kabusys 配下にパッケージ化されています）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（自動 .env ロード機能含む）
  - config_setup.py            — 対話式 .env 生成ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_monitoring.py          — SystemMonitor ポーリング loop 起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ初期化・永続化 API
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — （滞留注文等の監視）※参照あり
    - risk_monitor.py          — ドローダウン / ポジション数監視
    - monitoring_engine.py     — 各 Monitor を束ねるポーリングエンジン
    - kill_switch.py           — フラグファイル操作 (kill.flag)
    - alert_manager.py         — アラート送信（LINE 等） ※参照あり
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数算出・aggregate cap ロジック
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py       — ファクター計算（momentum / value / volatility）
    - feature_exploration.py   — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py       — 市場レジーム判定（ma200 + macro sentiment）
  - execution/
    - ...                     — Execution 系の実装（Engine, OrderManager, BrokerFactory 等）※参照
  - data/                      — デフォルト DB / フラグファイル配置場所（git に含めない）

（実際のファイル数・構成はリポジトリの内容に依存します。ここでは主要モジュールを抜粋しています）

---

## 運用上の注意

- .env は機密情報を含むため、リポジトリに含めない（.gitignore に追加してください）。
- KABUSYS_ENV=live で起動する場合は特に注意（実際の発注が行われます）。validate_config の警告を必ず確認してください。
- Kill Switch / stop flag の設定は運用ルールを決めてから使用してください（誤操作防止）。
- OpenAI API を利用する機能は API 利用料が発生します。API キー管理に注意してください。
- DuckDB / SQLite ファイルは適切にバックアップしてください（分析データ / ログの損失を防ぐため）。

---

## 開発者向けヒント

- テスト実行用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みをスキップできます。
- news_nlp / regime_detector の OpenAI 呼び出し部分はテストで差し替え可能（モジュール内の呼び出し関数をパッチする想定）。
- MonitoringDB.init_monitoring_db は冪等でマイグレーションも一部扱います（カラム追加等）。

---

もし README に追加したい事項（例: CI / テスト手順、詳細な設定値の説明、API 仕様ドキュメントなど）があれば教えてください。必要に応じて追記します。