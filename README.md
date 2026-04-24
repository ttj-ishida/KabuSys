# KabuSys

日本株向け自動売買システムのコードベース README。以下は本リポジトリの概要、主な機能、導入手順、実行方法、ディレクトリ構成の説明です。

※ 本 README はソースコード（src/kabusys 以下）を参照して作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買およびそれに付随するモニタリング／リサーチツール群をまとめたシステムです。  
主に以下の責務を持ちます。

- 注文の発行・管理（ExecutionEngine）
- システム稼働状況・注文状態の監視（Monitoring）
- ポートフォリオ構築とポジションサイズ計算（Portfolio）
- ファクター計算や特徴量解析（Research）
- ニュースの NLP によるセンチメント評価・市場レジーム判定（AI）
- ペーパートレード結果の検証レポート生成（Tools）

設計上のポイント：
- 設定は .env ファイル / 環境変数で管理（config モジュール）
- 監視ログは SQLite（monitoring.db）へ永続化、分析データは DuckDB（kabusys.duckdb）
- Paper Trading モードでは本番 DB と分離し、MockBrokerClient を使用して data/paper_trading.db に記録
- OpenAI（gpt-4o-mini 等）を利用する機能あり（API キー必須）

---

## 機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine（注文実行エンジン）起動スクリプト
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に記録
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
    - 環境変数 `MONITOR_POLL_INTERVAL` で間隔を上書き可能（デフォルト 60 秒）
- 設定管理
  - config_setup.py: .env を対話式で作成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
- 監視
  - monitoring/monitoring_db.py: 監視用 SQLite のスキーマ初期化・永続化 API
  - monitoring/system_monitor.py: CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - monitoring/trade_monitor.py, monitoring/risk_monitor.py, monitoring/kill_switch.py 等によるリスク監視と Kill Switch
  - monitoring/monitoring_engine.py: 各モニタを束ねるポーリングエンジン
- 実行・リスク管理
  - execution/*: ブローカーファクトリ、ExecutionEngine、OrderManager、RiskManager、Reconciler、OrderRepository 等（注文制御、リスク制御）
- ポートフォリオ構築
  - portfolio/*: 候補選定、重み付け、セクター制限、ポジションサイズ計算
- リサーチ
  - research/*: ファクター計算（Momentum, Volatility, Value 等）、将来リターン、IC 計算、統計要約
- AI / NLP
  - ai/news_nlp.py: ニュース記事を OpenAI で評価し ai_scores に書き込む機能
  - ai/regime_detector.py: ma200 とマクロニュースセンチメントを組み合わせた市場レジーム判定
- ツール
  - tools/paper_verification_report.py: Paper Trading DB から検証レポートを生成

---

## 前提 / 必要環境

- Python 3.10 以上（typing の | アノテーションを使用しているため）
- 必須 Python パッケージ（最低限）
  - duckdb
  - psutil
- OpenAI を使う機能を利用する場合:
  - openai（OpenAI の Python SDK）
- config/*.yaml を検証したい場合:
  - PyYAML（任意）
- 推奨: 仮想環境（venv / conda）を利用

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

必要なパッケージはプロジェクトに requirements.txt があればそれを使用してください（本コード断片では同梱されていません）。

---

## セットアップ手順（基本）

1. リポジトリをクローンしてチェックアウト
2. 仮想環境を作成して依存パッケージをインストール
3. .env を作成
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは .env.example を参考に手動で作成する
4. 設定を検証
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにする strict モード
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリの作成（必要に応じて）
   - デフォルトでは `data/` 配下に DB / pid / フラグファイルが置かれるため、適宜ディレクトリを作成するか起動時に自動作成されます。
6. DuckDB / SQLite のパス
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）
   - 環境変数で上書き可（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）

---

## 主な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用/動作関連:
- KABUSYS_ENV: 実行環境（development | paper_trading | live） — デフォルト `development`
  - paper_trading: Mock ブローカーを使い paper DB に記録（本番 DB と分離）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） — デフォルト `INFO`
- LOG_DIR: ログの保存先ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI を利用する機能で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading における約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（1 = クリア）※本番では危険

パス:
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH

---

## 使い方（コマンド例）

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（本番 / ペーパートレード切替）
  - 本番（KABUSYS_ENV=live 等を .env で設定）
    ```bash
    python -m kabusys.run_execution
    ```
  - ペーパートレード
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 実行開始時にプロセス優先度が上げられ、PID ファイル（デフォルト data/execution.pid）が作られます。
  - 停止は以下のフラグで制御（詳しくは停止/制御節参照）。

- Monitoring を起動（監視ループ）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更するには:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（ニューススコアリング / レジーム判定）はライブラリ関数として使用可能
  - 例: ai/news_nlp.score_news(conn, target_date, api_key=...)
  - OpenAI API キーが必要（OPENAI_API_KEY）

---

## 停止 / 制御

- run_monitoring / run_execution はファイルベースのフラグで停止や制御を行います。
  - data/stop_requested.flag:
    - run_monitoring/run_execution のループがこのファイルの存在を検知すると安全停止します。
  - data/kill.flag:
    - KillSwitch が条件（大きなドローダウン等）を満たすと書き込み、ExecutionEngine に停止を促す目的で使用されます。
    - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアされる設定があるため注意（本番では 0 推奨）。
- PID ファイル:
  - data/execution.pid（ExecutionEngine）などを通じてプロセス管理を補助します。

---

## ログについて

- ログは stdout に出力されると同時に日次ローテーションでファイルに保存されます（kabusys.utils.logging_setup）。
  - デフォルトログディレクトリ: logs/
  - ファイル名: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - ローテーション保持期間: 30 日
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御します。

---

## 注意事項 / 運用上のヒント

- KABUSYS_ENV を `live` にした場合は実際に注文が発行されます。LINE 等の通知設定や Kill Switch の挙動を十分に確認してください。
- Paper Trading モードでは本番データベースと分離されますが、設定ミスで本番 DB を参照しないかを validate_config で事前に確認してください。
- OpenAI を利用する機能は API コスト・レイテンシ・失敗に注意。実装ではリトライとフェイルセーフ（失敗時はスコア 0 等）を備えていますが、運用監視が必要です。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル／ディレクトリと役割のまとめです。

- src/kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - config.py                  — 環境変数 / Settings ラッパ
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度・CPU affinity ユーティリティ
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    (注文実行に関する実装群)
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ・永続化 API
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文ログ監視（滞留・約定異常等）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — アラート送信管理（LINE 等への通知）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP / OpenAI 呼び出しと ai_scores 書き込み
    - regime_detector.py      — 市場レジーム判定（ma200 + マクロセンチメント）
  - data/                     — 実行時に作成されるデータ例（data/*.db, pid, flag 等）

---

## 開発者向け補足

- DB スキーマやマイグレーションは monitoring_db.init_monitoring_db() で冪等に作成されます。
- 多くのユーティリティ関数は「副作用を最小化」する設計で、テストの差し替え（mock）を想定しています（例: OpenAI 呼び出し関数はテストで差し替え可能）。
- research / portfolio モジュールは純粋関数（DB 参照が限定的）で単体テストが容易に書ける設計です。

---

もし README に追記したい箇所（例: 実際の起動例や systemd / supervisor 用のユニットファイルサンプル、より詳しい環境変数一覧、CI 設定など）があれば教えてください。必要に応じて追記・整備します。