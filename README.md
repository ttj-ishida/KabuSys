# KabuSys — 日本株自動売買システム

このリポジトリは、日本株向けの自動売買システム（KabuSys）のコアコンポーネント群を含みます。システムは発注エンジン、監視、リサーチ（ファクター計算）、ポートフォリオ構築、AI を使ったニュースセンチメント評価などから構成されています。

## プロジェクト概要
- 発注（ExecutionEngine）とモニタリング（MonitoringEngine）を分離して実装。
- paper_trading（ペーパートレード）モードを持ち、本番 DB と完全分離して動作可能。
- DuckDB を分析（ファクター計算・リサーチ）に、SQLite を監視・発注ログに使用。
- OpenAI（gpt-4o-mini）を使ったニュース NLP による銘柄センチメント評価、およびマクロニュースを用いた市場レジーム判定機能を提供。
- Kill Switch（閾値超過時の停止フラグ）、LINE へのアラート通知、リスク監視など運用に必要な仕組みを備える。

## 主な機能一覧
- Execution
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - Broker クライアントの抽象化（実運用 / Mock 切り替え）
  - Order 管理・リコンシリエーション・リスク管理
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存確認・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格の異常検知
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: フラグファイルによる停止シグナル生成
  - AlertManager: LINE Push による通知（トークン未設定時はログ出力）
  - 実行用ポーリングスクリプト（python -m kabusys.run_monitoring）
- Research / Portfolio
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC（Information Coefficient）算出
  - ポートフォリオ構築（候補選定、重み付け、リスク調整、ポジションサイズ計算）
- AI
  - ニュースセンチメント（score_news）: raw_news → ai_scores へ書き込み
  - 市場レジーム判定（score_regime）: ETF + マクロニュースの合成
- ユーティリティ
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

---

## 必要条件（推奨）
- Python 3.9+（実装は typing 注釈等を使用）
- pip パッケージ:
  - duckdb
  - psutil
  - requests
  - openai
  - PyYAML（config 検証を行う場合）
- SQLite（標準ライブラリ）
- ネットワーク接続（OpenAI / LINE を利用する場合）

requirements.txt がない場合は手動でインストールしてください。例:
```
pip install duckdb psutil requests openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を作成
   ```
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb psutil requests openai pyyaml
   ```

2. .env を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - あるいはプロジェクトルートに `.env` を手動で作成（例は下記）。

3. 設定を検証
   ```
   python -m kabusys.validate_config
   # 警告を FAIL として扱う場合:
   python -m kabusys.validate_config --strict
   ```

4. データディレクトリの確認・作成
   - デフォルトでは `data/` 配下に DB ファイルやフラグファイルを置きます。必要に応じて親ディレクトリを手動で作成してください。
   - validate_config は親ディレクトリの存在有無を警告しますが、起動時に自動作成される箇所もあります。

.env の最小例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
# OPENAI_API_KEY=sk-...
# LINE_CHANNEL_ACCESS_TOKEN=...
# LINE_USER_ID=...
```

---

## 使い方

### 実行エンジン（ExecutionEngine）
- 本番 / 開発 / ペーパートレードの切り替えは KABUSYS_ENV による。
  - paper_trading: MockBrokerClient を使用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と分離する。
- 起動:
  ```
  python -m kabusys.run_execution
  ```
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - 実行中は `data/execution.pid` に PID を書きます。Process 優先度は最初に High に設定されます。

### 監視ループ（Monitoring）
- 起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず 本番 sqlite_path（Settings.sqlite_path）を使用します（監視ログは本番 DB を参照）。
  - 停止フラグ: プロジェクトルートの `data/stop_requested.flag` の存在を検知すると監視ループを終了します。

### Paper Trading 検証レポート
- 過去期間のパフォーマンス指標を集計して表示します。
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

### AI / リサーチ機能（ライブラリ的利用）
- ニュースセンチメント（DuckDB 接続を渡す）:
  ```
  from kabusys.ai.news_nlp import score_news
  # conn: duckdb.DuckDBPyConnection
  score_news(conn, target_date, api_key="sk-...")
  ```
- 市場レジーム判定:
  ```
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key="sk-...")
  ```
- ファクター計算:
  ```
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  results = calc_momentum(duckdb_conn, date(2026,4,1))
  ```

---

## 設定（主な環境変数）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 任意 / 推奨
  - KABUSYS_ENV: execution 環境（development / paper_trading / live）。デフォルト: development
  - DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
  - SQLITE_PATH: 監視 DB（SQLite）パス。デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 用）
  - PAPER_FILL_MODE: ペーパートレード時の擬似約定モード（instant/partial/never/reject）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - OPENAI_API_KEY: OpenAI を使う機能で必要
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=自動クリア）。本番は 0 推奨。

詳細は `kabusys.config.Settings` と `kabusys.config_setup` を参照してください。`python -m kabusys.validate_config` で不足項目を検出できます。

---

## 運用上の注意・挙動
- Monitoring は「監視」に特化しており、KABUSYS_ENV に関係なく本番監視 DB（Settings.sqlite_path）を参照します。
- ExecutionEngine は paper_trading 時に別 DB を使用して本番と完全分離します。
- プロセス優先度の設定（set_process_priority）は psutil を使います。権限不足で失敗する場合は警告が出ますが処理は継続します。
- Kill Switch（data/kill.flag）を書き込むと実行中のエンジンに停止シグナルを送ります。clear() で削除できます。
- ストップ制御: `data/stop_requested.flag` による即時停止検出が各起動スクリプトに組み込まれています。

---

## ディレクトリ構成（抜粋）
（リポジトリの src/kabusys 以下を示します）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 作成ウィザード CLI
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI 連携）
    - regime_detector.py       — 市場レジーム判定
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ・永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
  - execution/                 — 発注関連（order_manager 等はここに実装）
    - (OrderRepository, ExecutionEngine 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py

data/ 以下（運用側に生成・使用される）
- data/kabusys.duckdb         — DuckDB（分析用）
- data/monitoring.db          — 監視ログ（SQLite）
- data/paper_trading.db       — ペーパートレード用 DB（paper_trading 時）
- data/execution.pid          — 実行エンジン PID（実行中に生成）
- data/kill.flag              — Kill Switch フラグ
- data/stop_requested.flag    — 停止フラグ（手動停止など）

---

## トラブルシュート（よくある問題）
- 必須環境変数が未設定:
  - `python -m kabusys.validate_config` を実行してエラーを確認。
- OpenAI API 関連エラー:
  - OPENAI_API_KEY を .env または引数で正しく設定してください。
  - リトライ / バックオフ機構はありますが、ネットワークやクォータ制限に注意。
- psutil による優先度設定が失敗:
  - 権限不足の場合は警告が出ますが処理は継続します。
- DuckDB / SQLite のファイルパスの親ディレクトリがない:
  - validate_config が警告します。手動で `mkdir -p data` など作成してください。

---

## 開発者向けメモ
- 多くのモジュールは DB 接続（duckdb/ sqlite3）を引数で受け、サイドエフェクトを最小化した純粋関数的実装が意図されています。ユニットテストが書きやすい設計です。
- OpenAI 呼び出し部分は内部ヘルパー関数を分離してあり、テスト時はモックしやすいようになっています（例: unittest.mock.patch）。
- monitoring_db.init_monitoring_db は冪等であり、既存 DB に対する簡易マイグレーションも含みます。

---

必要であれば、README にインストール手順（apt/yum ベースの依存関係）、CI / デプロイ手順、例の .env.example、または主要 CLI の使い方をより詳細に追記します。どの部分を拡張したいか教えてください。