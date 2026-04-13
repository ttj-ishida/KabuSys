# KabuSys

日本株自動売買システムのライブラリ／実行スクリプト群です。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）やAIを使ったニュース解析までを含むモジュール群を提供します。

---

## 主な特徴（機能一覧）

- 実行系
  - ExecutionEngine 起動用スクリプト（run_execution.py）
  - Paper trading（模擬ブローカー）と本番ブローカーの切り替え
  - 再起動時のリコンシリエーション（Reconciler）による自動復旧

- 監視
  - System / Trade / Risk 各種 Monitor とポーリングエンジン（MonitoringEngine）
  - 監視ログ永続化（SQLite）
  - kill.flag による ExecutionEngine 停止シグナル
  - LINE Push によるアラート送信（AlertManager）
  - Streamlit ベースの監視ダッシュボード

- 研究・データ処理
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- ポートフォリオ構築
  - 候補選定、等重/スコア加重の重み計算
  - ポジションサイズ計算（リスクベース／等分配など）
  - セクター集中制限、レジームに応じた乗数

- AI（OpenAI）
  - ニュースのセンチメントスコアリング（ai.news_nlp.score_news）
  - マクロニュースとインデックス乖離を用いた市場レジーム判定（ai.regime_detector.score_regime）
  - API 呼び出しは堅牢にリトライ/フォールバック実装

- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - .env 自動ロード（プロジェクトルートの .env / .env.local）

---

## 前提・依存

- Python 3.10 以上（型注釈の union 演算子 `|` を使用）
- 必要な外部ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

※ 実際のプロジェクトでは requirements.txt / poetry 等で依存管理してください。

---

## 環境変数（主なもの）

- KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
  - paper_trading のときは MockBrokerClient を使い、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）にログを残します
- SQLITE_PATH: 監視用 SQLite データベースのパス（デフォルト: `data/monitoring.db`）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: `data/kabusys.duckdb`）
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite パス（デフォルト: `data/paper_trading.db`）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（`instant`|`partial`|`never`|`reject`、デフォルト: `instant`）
- PID_FILE_PATH: ExecutionEngine の PID ファイル保存先（デフォルト: `data/execution.pid`）
- KILL_FLAG_PATH: kill.flag パス（デフォルト: `data/kill.flag`）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合必須）
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 外部 API の認証情報（必須となる場合あり）
- LOG_LEVEL: ログレベル（`DEBUG`|`INFO`|`WARNING`|`ERROR`|`CRITICAL`）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: `1` にすると .env 自動ロードを無効化

.env ファイルはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から自動読み込みされます。テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. リポジトリをクローン、あるいはソースを取得
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. 必要な環境変数を設定（.env を作成）
   - 例（.env）:
     ```
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```
5. データディレクトリ作成:
   ```bash
   mkdir -p data
   ```
6. DuckDB / SQLite の初期化
   - 監視用 DB は起動スクリプトが自動でテーブルを作成します（init_monitoring_db）

---

## 使い方（主要コマンド）

- Monitoring（ポーリングループ）を起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 起動時にプロセス優先度が "high" に設定されます（psutil 経由、権限が不足する場合は警告）

- ExecutionEngine を起動（実取引または paper_trading）:
  ```bash
  # 本番 / 開発
  python -m kabusys.run_execution

  # Paper trading（環境変数で切り替え）
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - paper_trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）にログし、本番 DB と完全に分離されます
  - PAPER_FILL_MODE により模擬約定の挙動を制御できます

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB 指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- Streamlit ダッシュボード起動（監視データ閲覧）:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI モジュール（プログラムから呼び出す）
  - ニューススコアリング:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    n = score_regime(conn, target_date=date(2026,4,10), api_key="YOUR_OPENAI_KEY")
    ```

- ライブラリ的に使用する
  - ファクター計算:
    ```python
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    ```
  - ポートフォリオ構築:
    ```python
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
    ```

---

## 注意点 / 運用上の情報

- Settings（kabusys.config.Settings）は .env または環境変数から設定を読み込みます。必須のキーが未設定だと ValueError が投げられます。
- Monitoring のログは SQLite（default: data/monitoring.db）に保存され、init_monitoring_db が起動時にテーブルとマイグレーションを行います。
- kill.flag の存在は ExecutionEngine に停止を促す仕組みです。kill.flag は `KILL_FLAG_PATH`（既定: data/kill.flag）で管理されます。
- OpenAI API を利用する機能は API キー必須。API エラー時はリトライやフォールバック（例: macro_sentiment=0.0）を行うため、完全に失敗してもシステム全体は継続動作する設計です。
- process priority / CPU affinity の設定はプラットフォーム依存で、権限が不足する場合は警告出力してスキップします（安全フェイル）。

---

## ディレクトリ構成（抜粋・概観）

（実際のソースは `src/kabusys` 配下）

- src/kabusys/
  - __init__.py               — パッケージ情報
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み）
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py        — SQLite ベースの監視ログ永続化層
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — LINE Push 通知
    - monitoring_engine.py    — 各 Monitor を纏めるポーリングエンジン
    - streamlit_dashboard.py  — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - order_*                 — 発注関連実装（詳細はソース参照）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・スケーリング
    - risk_adjustment.py      — セクター制限・レジーム乗数
  - research/
    - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  — 将来リターン計算 / IC / 統計
  - data/
    - pipeline.py             — データパイプライン補助（DuckDB 操作用ユーティリティ）
    - stats.py                — 正規化ユーティリティ 等
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py      — レジーム判定（MA + マクロ NLP）
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

（上は主要ファイルの抜粋です。実装の詳細は各モジュールの docstring を参照してください。）

---

## 開発者向けメモ

- Settings は起動時にプロジェクトルートを基に .env / .env.local を自動読み込みします（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能）。
- DuckDB 接続や OpenAI クライアントの呼び出しは明示的に渡してテスト容易性を確保しています（ユニットテストでは接続や API 呼び出しをモック可能）。
- DB 書き込みは可能な限り冪等／トランザクションで実装されています（monitoring_db / ai の書き込みなど）。
- ロギングは標準 logging を使用。起動スクリプト側で logging.basicConfig(level=logging.INFO) が設定されます。デバッグ時は LOG_LEVEL=DEBUG を設定してください。

---

README は以上です。必要であれば、導入手順をさらに自動化するスクリプト（requirements.txt / Dockerfile / systemd ユニットファイル等）のテンプレートも作成します。どの部分を詳述したいか教えてください。