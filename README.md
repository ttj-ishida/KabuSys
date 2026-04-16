# KabuSys

日本株向け自動売買基盤のコアライブラリ群。シグナル → ポートフォリオ構築 → 発注 → モニタリング／アラート／検証 を含むモジュール群を提供します。

以下はこのリポジトリに基づく README（日本語）です。

---

## プロジェクト概要

KabuSys は、日本株の自動売買システム向けに設計された Python モジュール群です。主要機能は以下のとおりです。

- シグナルやファクタ計算に基づくポートフォリオ構築（等金額／スコア重み／リスクベース）
- 発注管理（OrderManager、ExecutionEngine、Reconciler）
- Paper Trading 用の分離された DB / モックブローカー対応
- モニタリング（システム状態、注文滞留、リスク／ドローダウン監視）
- アラート（LINE Push）と Kill Switch（フラグファイルによるエンジン停止）
- AI 支援モジュール（ニュースセンチメント、レジーム判定） — OpenAI を利用
- 検証ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針として、DuckDB / SQLite をデータ層に使用し、外部 API 呼び出しやランタイム時のルックアヘッドを避ける実装になっています。

---

## 主な機能一覧

- ポートフォリオ構築
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（risk_based / equal / score）
  - セクターキャップ適用、レジーム乗数

- 発注 / 実行
  - ExecutionEngine（本番／ペーパートレード切替）
  - OrderManager（重複防止、状態遷移管理）
  - Reconciler（再起動時の自動復旧・ポジション照合）

- モニタリング
  - SystemMonitor（CPU/Mem/Disk、データ鮮度、PID チェック）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン、ポジション数上限）
  - AlertManager（LINE Push、クールダウン管理）
  - KillSwitch（条件一致で data/kill.flag を書き込み実行停止）
  - MonitoringEngine（上記を束ねるポーリングエンジン）
  - SQLite ベースの永続化層（monitoring_db.py）

- AI（OpenAI）
  - news_nlp.score_news：ニュースを LLM でセンチメント化して ai_scores に記録
  - regime_detector.score_regime：MA とマクロニュース（LLM）を合成して市場レジーム判定

- ツール
  - paper_verification_report：Paper Trading DB から検証レポートを生成
  - streamlit_dashboard：監視用ダッシュボード（Streamlit）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型注釈や一部表記に合わせて）
- ソースは `src/` 配下にあり、パッケージとして実行できます（例: `PYTHONPATH=src python -m ...`）
- 必要なパッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
  - (必要に応じて) sqlite3 は標準ライブラリ

推奨手順（UNIX 系シェルの例）:

1. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   （プロジェクトに requirements.txt がない場合は手動で）
   ```
   pip install duckdb psutil requests openai streamlit
   ```

3. 開発モードでインストール（任意）
   ```
   pip install -e src
   ```
   これにより `python -m kabusys.xxx` のようなモジュール実行が容易になります。

4. データディレクトリ作成
   ```
   mkdir -p data
   ```
   初期データベース等は実行時に必要に応じて作成されます（monitoring 用テーブルは init_monitoring_db で作成されます）。

環境変数（主な必須／推奨）
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- OPENAI_API_KEY （AI 機能を使う場合に必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時のマッチ挙動、デフォルト: instant）
- SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
- DUCKDB_PATH（DuckDB ファイル。デフォルト: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE 通知）

.env 自動読み込み
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数 > .env.local > .env）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要コマンド）

注意: パッケージをインストールしていない場合は `PYTHONPATH=src python -m ...` で実行します。パッケージを pip install -e している場合は `python -m kabusys.run_monitoring` のように実行可能です。

1. 監視ループの起動（Monitoring）
   ```
   # PYTHONPATH を通す例
   PYTHONPATH=src python -m kabusys.run_monitoring
   ```
   オプション／挙動:
   - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を指定。デフォルト 60 秒。
   - Monitoring は常に本番の sqlite_path（Settings.sqlite_path）を使用します（環境に関わらず）。
   - 停止: プロジェクトルート `data/stop_requested.flag` ファイルを作成するとループが終了します。

2. 実行エンジン起動（Execution）
   ```
   PYTHONPATH=src python -m kabusys.run_execution
   ```
   挙動:
   - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し、DB は paper_trading 用の `data/paper_trading.db` に記録します（本番 DB と分離）。
   - 実行中は `data/execution.pid` に PID を書き込みます。`data/stop_requested.flag` の存在で安全に停止します。
   - 起動前に `data/kill.flag` が存在すると起動を行いません（Kill Switch 用）。

3. Paper Trading 検証レポート
   ```
   PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   オプション:
   - --from / --to: レポート期間（YYYY-MM-DD）
   - --db: データベースパス（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

4. Streamlit ダッシュボード（監視用）
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   引数 `--db` で monitoring DB を指定（デフォルト: data/monitoring.db）。読み取り専用で開きます。

5. AI 機能（ニュース NLP / レジーム判定）
   - `OPENAI_API_KEY` を環境変数で設定してから、該当モジュールの公開関数を呼び出してください。
   - 例: `kabusys.ai.score_news(conn, target_date)` / `kabusys.ai.regime_detector.score_regime(conn, target_date)`
   - OpenAI のエラー時はフェイルセーフで継続／0.0 フォールバックが多用されています。

---

## 主要設定（Settings クラスに基づく）

Settings は `kabusys.config.Settings` で提供され、環境変数から値を取得します。主なキー:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject (paper_tradingの注文約定モード)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL

自動読み込みの詳細は `src/kabusys/config.py` を参照してください。

---

## 停止・キルフラグ

- data/stop_requested.flag: run_monitoring / run_execution が監視している停止フラグ。存在すると安全にループやエンジンを停止します。
- data/kill.flag: KillSwitch が書き込むファイルで、ExecutionEngine の明示的停止を意図します。KillSwitch はリスク条件（ドローダウン、ポジション上限等）により書き込まれます。
- run_execution は起動時に `KILL_FLAG_CLEAR_ON_START` を用いてフラグをクリアする設定がある点に注意してください。

---

## ディレクトリ構成

（重要なファイル・モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート CLI
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py            — OpenAI を用いたニュース NLP スコアリング
      - regime_detector.py     — 市場レジーム判定（MA + LLM）
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他ブローカー/engine などの実装)
    - utils/
      - process_priority.py    — psutil を使った優先度 / CPU affinity 設定
    - data/ (実行時に生成される想定)
      - monitoring.db
      - paper_trading.db
      - kabusys.duckdb
      - execution.pid
      - stop_requested.flag
      - kill.flag

---

## 注意点 / 運用上の補足

- Monitoring は常に Settings.sqlite_path（本番 path）を使います。ペーパートレード DB は run_execution 側で切り替わります。
- process priority / affinity の設定は `psutil` に依存します。権限不足や未対応プラットフォームでは警告を出してスキップします。
- OpenAI を使う機能は API の失敗を想定し、リトライや安全側フォールバック（0.0等）を組み込んでいますが、API キーの管理・コストには注意してください。
- DuckDB / SQLite ファイルは適切にバックアップ・パーミッション管理を行ってください。特に本番 DB に Paper Trading のデータを書き込まないよう環境変数での切替を確認してください。
- `.env` の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。テストなどで自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

必要であれば README にサンプルの `.env.example`、起動スクリプトの Systemd ユニット例、もしくは Dockerfile / docker-compose のテンプレートを追記できます。どれを優先して追加しますか？