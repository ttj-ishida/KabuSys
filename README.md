# KabuSys

日本株向け自動売買システムのコアライブラリ群（リポジトリ内の主要スクリプト・ユーティリティ群を抜粋）。  
本READMEはコードベースの主要機能、セットアップ手順、使い方のサマリ、およびディレクトリ構成を日本語でまとめたものです。

注意：これはライブラリ/管理スクリプト群の説明です。実際にマーケットに接続して発注する際は十分な確認とテストを行ってください。

---

## プロジェクト概要

KabuSys は、日本株自動売買に必要な以下の責務を分離して実装したモジュール集合です。

- データ取得・集計（DuckDB を想定した分析）
- シグナル生成・ポートフォリオ構築（純粋関数群）
- 発注実行エンジン（実口座 / ペーパートレードの切り替え対応）
- 監視（System / Trade / Risk のモニタリング、Kill Switch）
- AI 補助機能（ニュースの NLP スコアリング、レジーム判定）
- 設定ウィザード・検証ツール・運用向けユーティリティ

設計方針の主な点：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV により挙動切替）
- 外部 API 呼び出し（例: OpenAI）は独立モジュールでラップ、リトライ等フェイルセーフ実装あり
- ログ・PID・フラグファイルを使ったシンプルな運用インタフェース

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（.env / .env.local、ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 対話式の .env 生成ウィザード（config_setup）
  - 起動前設定検証ツール（validate_config）

- 実行・監視
  - ExecutionEngine 起動スクリプト（run_execution）
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を利用
    - PID ファイル、停止フラグ（data/stop_requested.flag）による停止制御
  - SystemMonitor のポーリング起動（run_monitoring）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視ログは SQLite（data/monitoring.db）へ永続化

- 監視サブシステム
  - SystemMonitor: CPU/メモリ/Disk/プロセス起動状態、データ鮮度チェック
  - TradeMonitor: 注文ログや約定の監視（滞留注文や価格異常など）
  - RiskMonitor: ドローダウン監視、ポジション上限監視（Kill Switch と連携）
  - MonitoringDB: 監視用 SQLite テーブル群（system_status, trade_logs, positions, risk_logs, dashboard）

- ポートフォリオ構築（純粋関数）
  - 候補選定、等金額/スコア加重の重み計算
  - セクター上限適用、レジーム乗数計算
  - ポジションサイズ計算（lot 単位丸め、aggregate cap 処理）

- リサーチ / 分析
  - ファクター計算（モメンタム・ボラティリティ・バリュー等） — DuckDB 接続を受ける純粋関数
  - 将来リターン、IC、統計サマリなどの分析ユーティリティ

- AI 関連
  - news_nlp: OpenAI を利用したニュースセンチメント集約（バッチ処理・JSON バリデーション・リトライ）
  - regime_detector: MA200 とマクロニュース（LLM）を組み合わせた市場レジーム判定

- 運用ツール
  - paper_verification_report: ペーパートレード DB の検証レポート生成（稼働率、注文成功率、レイテンシなど）

---

## 必要要件（依存パッケージ）

主に以下の Python パッケージを使用します（抜粋）：

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config 検証で YAML の中身を検証したい場合に必要）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai PyYAML
```

※ 実際の project 配布では requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. Python 環境構築（上記依存パッケージをインストール）
3. 対話式で .env を作成:
   ```
   python -m kabusys.config_setup
   ```
   - もしくは手動で `.env` を作成（下記に主要キーの例を記載）

4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告もエラー扱い（exit 1）

5. データディレクトリの確認:
   - デフォルト DB / ファイルパス例:
     - DuckDB: data/kabusys.duckdb
     - SQLite(監視): data/monitoring.db
     - Paper SQLite: data/paper_trading.db (paper_trading 時)
     - PID / Kill flag: data/execution.pid, data/kill.flag
   - 必要に応じてこれらの親ディレクトリ（data, logs）を作成してください。logging_setup は自動で logs ディレクトリを作成しようとします。

.env に設定する主要な環境変数（例）
```
KABUSYS_ENV=development   # development | paper_trading | live
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
LINE_CHANNEL_ACCESS_TOKEN=    # 任意（アラート）
LINE_USER_ID=
OPENAI_API_KEY=your_openai_key  # AI 使うなら必須
PAPER_FILL_MODE=instant  # instant | partial | never | reject
```

自動ロード挙動:
- プロジェクトルート（.git または pyproject.toml が見つかった場所）から `.env` と `.env.local` を自動で読み込みます（既存の OS 環境変数は保護されます）。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要スクリプト）

以下は主要な実行方法の例です。各スクリプトはパッケージモジュールとして起動できます。

- 設定ウィザード（対話式）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視（SystemMonitor のポーリングを開始）:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視スクリプトは起動時にプロセス優先度を高くし（set_process_priority("high")）、monitoring DB（settings.sqlite_path）と DuckDB に接続します。
  - 監視ループを終了させるにはプロジェクトルートの `data/stop_requested.flag` を作成するか、Ctrl+C。

- 実行エンジン（ExecutionEngine）起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使い、データは `data/paper_trading.db` に保存されます。
  - 起動時に `data/stop_requested.flag` が存在する場合は起動せず終了します。
  - 実行エンジンは `data/execution.pid` を使用して PID 管理を行います。
  - 停止は `data/stop_requested.flag` を作成すると検知して停止します。

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI / リサーチ関数（プログラムから直接呼び出す）
  - ニューススコアリング:
    ```python
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect() の接続オブジェクト、target_date は datetime.date
    count = score_news(duckdb_conn, target_date, api_key="...")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```
  - ファクター計算等:
    ```python
    from kabusys.research import calc_momentum
    results = calc_momentum(duckdb_conn, target_date)
    ```

- ログ設定
  - すべての起動スクリプトは `kabusys.utils.logging_setup.setup_logging(app_name=...)` を呼び出します。ログは stdout と `logs/<app_name>.log` に日次ローテーションで出力されます（デフォルト 30 日保持）。

---

## 運用に関する注意点

- Kill Switch:
  - RiskMonitor の評価により KillSwitch が判定した場合、`data/kill.flag` に理由を書き込み、ExecutionEngine に停止を促します。
  - `KILL_FLAG_CLEAR_ON_START` が `1` の場合、起動時に自動で kill.flag をクリアします（本番では `0` を推奨）。

- 停止制御:
  - 監視/実行の停止は `data/stop_requested.flag` を作成することで実行プロセスが検知して安全に終了します。
  - `run_execution` は PID ファイル (`data/execution.pid`) を管理します。

- データベース分離:
  - 本番とペーパートレードは SQLite ファイルを分けて運用する設計です。設定による切替を厳守してください。

- OpenAI API:
  - AI 機能を使用する場合は `OPENAI_API_KEY` を設定してください。
  - 外部 API 呼び出しはリトライ・フォールバック挙動が入っていますが、料金やレスポンス時間に注意してください。

---

## ディレクトリ構成（主なファイル）

以下は `src/kabusys` 以下の主要ファイル・モジュールの簡易一覧です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                    # 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py              # .env 対話ウィザード
  - validate_config.py           # 設定検証 CLI
  - run_monitoring.py            # SystemMonitor ポーリング起動スクリプト
  - run_execution.py             # ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py           # SQLite 監視 DB テーブルの作成・永続化 API
    - system_monitor.py          # システム状態 / データ鮮度監視
    - trade_monitor.py           # 注文ログ監視（ファイルに存在）
    - risk_monitor.py            # ドローダウン・ポジション監視
    - kill_switch.py             # kill.flag の作成/検査
    - monitoring_engine.py       # 各 Monitor を束ねるエンジン
    - alert_manager.py           # （アラート送信管理、LINE 等への通知）
  - execution/
    - execution_engine.py        # ExecutionEngine（発注セッションの管理）
    - broker_factory.py          # ブローカークライアント生成（本番 / Mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py       # 候補選定・重み計算
    - position_sizing.py         # 単元丸め・投下資金スケーリング
    - risk_adjustment.py         # セクター制限・レジーム乗数
  - research/
    - factor_research.py         # モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py     # 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py                # ニュース NLP スコアリング（OpenAI）
    - regime_detector.py         # レジーム判定（MA200 + マクロニュース）
  - tools/
    - paper_verification_report.py  # ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py           # ログ設定ユーティリティ
    - process_priority.py        # プロセス優先度 / CPU affinity ユーティリティ

---

## よく使うコマンドまとめ

- .env 作成ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視プロセス起動:
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- 実行エンジン起動（ペーパートレード）:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 最後に / 開発上の注意

- 本プロジェクトは金融システムに関わるコードを含みます。実際にマネーを動かす前にロジック・設定・テストを十分に確認してください。
- 本リポジトリの .env は絶対に Git にコミットしないでください（config_setup でも同旨の警告があります）。
- DuckDB / SQLite のスキーマやマイグレーションは monitoring_db.init_monitoring_db 等で自動的に行われる箇所がありますが、本番運用では DB のバックアップ運用を検討してください。

もし README の補足（例: .env の完全なテンプレート、起動用 systemd ユニット例、Docker 化手順など）が必要であれば、目的に応じて追加で用意します。