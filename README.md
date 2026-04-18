# KabuSys

日本株自動売買システムの Python 実装（モジュール群）。  
この README はリポジトリ内の主要スクリプト・モジュールを元に作成した概要・セットアップ・使い方ドキュメントです。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提（依存ライブラリ）
- セットアップ手順
- 環境変数（.env）と推奨設定
- 実行方法（起動スクリプト）
- 主要ユーティリティ / ツール
- ディレクトリ構成（ファイル一覧）
- 運用メモ / 注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネントをモジュール化したシステムです。  
主に以下の責務を持つモジュールで構成されています。

- データ収集・保管（DuckDB / SQLite）
- ファクター計算・研究（research）
- ポートフォリオ構築・ポジションサイジング（portfolio）
- Execution（ブローカ・発注処理） — 実行エンジン（run_execution）
- 監視（system / trade / risk）・アラート・Kill Switch（run_monitoring）
- AI（ニュース NLP / レジーム判定）を利用した補助機能
- 運用ツール（設定ウィザード・設定検証・検証レポート）

設計方針として「本番データベースとペーパートレードの分離」「ルックアヘッドバイアスの防止」「外部 API 呼び出しのフェイルセーフ化（部分失敗を許容）」などが取り入れられています。

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成 / 更新）
- 設定検証 CLI（必須環境変数や config/*.yaml の存在・パスなどをチェック）
- ExecutionEngine（本番 / ペーパートレード）起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper DB に記録
- Monitoring（System / Trade / Risk）ポーリングループ
  - CPU / メモリ / ディスクの監視、データ鮮度チェック、プロセス生存確認
  - Kill Switch（データフラグを書き込んで ExecutionEngine 停止）
- Portfolio モジュール（候補選定・重み計算・ポジションサイズ算出）
- Research（ファクター計算、将来リターン・IC 計算、統計サマリ）
- AI モジュール（ニュースからのセンチメント算出、レジーム判定）
- 運用ツール：Paper Trading 検証レポート生成

---

## 前提（依存ライブラリ）

最低限必要な主なライブラリ（例）:

- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML — config/*.yaml の検証に使用

インストール例:
```bash
python -m pip install duckdb psutil openai pyyaml
```

プロジェクトに requirements.txt があればそちらを利用してください。

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーを作成
2. Python 仮想環境を用意して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb psutil openai pyyaml
   ```
4. 初期環境変数ファイル (.env) を作成
   - 対話式ウィザードを使う（推奨）
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動でプロジェクトルートに `.env` を作成する

5. 設定検証（エラー・警告を確認）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

---

## 環境変数（.env）と代表的な設定

自動ロード:
- プロジェクトルートに `.env` / `.env.local` があれば、デフォルトで自動読み込みされます。
- 自動読み込みを無効にする場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

代表的な必須/重要な環境変数:
- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development / paper_trading / live（default: development）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading モード用）
- OPENAI_API_KEY — OpenAI を使う機能（ニュース NLP / レジーム判定）を使う場合に必要
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（default: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用フラグファイル（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- PAPER_FILL_MODE — ペーパートレードの約定振る舞い（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、default: 60）

簡単な .env の最小例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 実行方法（起動スクリプト）

- 監視（Monitoring）を起動
  - デフォルトで MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可（デフォルト 60 秒）。
  - 監視プロセスは常に Settings.sqlite_path（本番 sqlite_path）を使用します（環境に依らず）。
  ```bash
  python -m kabusys.run_monitoring
  # 例: ポーリング間隔を 30 秒にする
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- ExecutionEngine を起動
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動しません。実行中も同ファイルの有無で停止制御を受けます。
  ```bash
  python -m kabusys.run_execution
  # paper_trading モードで起動する例
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

---

## 主要ユーティリティ / ツール

- Paper Trading 検証レポート
  - ペーパートレードのログ DB（PAPER_TRADING_SQLITE_PATH）から指標を集計し PASS/FAIL を判定するツール
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を直接指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```
  - 指標例: 稼働率、注文成功率、送信率、P95 レイテンシ など

- AI 関連
  - kabusys.ai.news_nlp.score_news — ニュース記事を OpenAI へ送りセンチメントを ai_scores テーブルへ書き込む（OPENAI_API_KEY が必要）
  - kabusys.ai.regime_detector.score_regime — ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成して market_regime を更新

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと説明です（抜粋）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 自動読み込み・Settings クラス
  - config_setup.py
    - .env 対話式作成ウィザード
  - validate_config.py
    - 設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py — ログ設定（stdout + 日次ローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・永続化 API
    - system_monitor.py — システム / データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - trade_monitor.py (参照されるがここに省略) — 注文系監視
    - kill_switch.py — data/kill.flag を使った停止フラグ
    - monitoring_engine.py — 各モニタの束ねとアラート発火
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・集約キャップ処理
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — モメンタム/バリュー/ボラ計算（DuckDB を使用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースを LLM でセンチメント化
    - regime_detector.py — レジーム判定（MA200 + マクロセンチメント）
  - execution/ (発注ロジック、ブローカファクトリなど、別ファイル群)
  - data/ (ランタイムで生成されることが多い)
    - monitoring.db（デフォルト SQLITE_PATH）
    - paper_trading.db（paper_trading モード用）
    - kill.flag / stop_requested.flag / execution.pid 等

（実際のリポジトリにはさらに多くのファイルが存在します。ここでは主要なものを抜粋しています。）

---

## 運用メモ / 注意点

- ログ:
  - デフォルトで stdout と logs/<app_name>.log に出力します。ログディレクトリは LOG_DIR 環境変数で変更可。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。権限不足やプラットフォームによっては警告が出ますが処理は継続します。
- Kill Switch / stop フラグ:
  - kill.flag（Settings.kill_flag_path）: KillSwitch が評価して書き込むファイル。存在すると ExecutionEngine 停止のトリガになります。誤って本番で自動クリアしないよう注意（KILL_FLAG_CLEAR_ON_START）。
  - stop_requested.flag（data/stop_requested.flag）: run_monitoring / run_execution がループ停止や起動拒否に使用します。手動停止や CI 等で利用できます。
- データベースの分離:
  - paper_trading モードでは paper_sqlite_path を使用して本番監視 DB と分離します（必ず環境を確認してください）。
- OpenAI:
  - news_nlp / regime_detector は OPENAI_API_KEY を必要とします。API 呼び出しはリトライロジックを備えていますが、API の料金・レートに注意してください。
- .env の自動読み込み:
  - プロジェクトルートの検出は __file__ を基準に行われます。配布後やインストール環境で動作しない場合は手動で環境変数を設定してください。

---

## よく使うコマンドまとめ

- .env を対話的に作る:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定チェック:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 監視プロセス起動:
  ```bash
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```
- 実行エンジン起動（ペーパートレード例）:
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

以上が README のサマリです。実装や運用に関してさらに詳しい部分（ExecutionEngine の設定、ブローカ実装、DB マイグレーション方針など）を追記したい場合は、対象のモジュールや運用フローに合わせて別途ドキュメント化することを推奨します。必要であれば、その作成を支援します。