# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリです。戦略・ポートフォリオ構築、発注エンジン、監視モジュール、AIニューススコアリング、リサーチ用ユーティリティ等を含みます。

## 概要（Project overview）
- 戦略に基づく銘柄選定・配分計算（ポートフォリオ構築）
- 発注の実行と注文管理（ExecutionEngine / OrderManager）
- 監視（System / Trade / Risk）とアラート送信（LINE）
- Paper Trading 用の分離された DB と Mock ブローカー
- ニュースを LLM（OpenAI）でセンチメント評価して ai_scores に保存
- DuckDB を用いたリサーチ・ファクター計算モジュール
- Streamlit を用いた監視ダッシュボード、検証レポート生成ツール等

## 主な機能（Features）
- portfolio: 候補選出・重み付け・ポジションサイズ計算（等配分・スコア加重・リスクベース）
- execution: Broker 抽象化、Order 管理、再同期間（Reconciler）などの実行関連ロジック
- monitoring: system/trade/risk の定期監視、kill switch（停止フラグ）・LINE 通知・ダッシュボード
- ai: ニュースの NLP スコアリング（OpenAI）・市場レジーム判定
- research: DuckDB を使ったファクター計算・将来リターン・IC 等の解析ユーティリティ
- tools: Paper Trading の検証レポート生成スクリプト等

## 必要条件（Requirements）
- Python 3.9+（typing の一部機能を利用）
- 推奨パッケージ（主にコード内で使用）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード起動時)
- SQLite（標準ライブラリの sqlite3 を使用）
- （任意）.env 管理ツールは不要。プロジェクトがルートの `.env` / `.env.local` を自動で読み込みます（無効化可能）。

インストール例（venv を利用）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```
必要に応じて他の依存を追加してください。

## セットアップ手順（Setup）
1. リポジトリをクローン
2. 仮想環境を作成して依存をインストール（上の例参照）
3. プロジェクトルートに `.env` を作成（.env.example を参考に設定）
   - 自動ロードはデフォルトで有効。テスト時などに無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
4. data ディレクトリ（DB 等）を作成:
   ```bash
   mkdir -p data
   ```
5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN — J-Quants 用トークン（strategy 等で使用）
   - KABU_API_PASSWORD — kabuステーション接続用パスワード
   - OPENAI_API_KEY — OpenAI を利用する場合（ai.score_news / regime 判定）
   - KABUSYS_ENV — 動作モード（development / paper_trading / live）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知を有効にする場合

設定は Settings クラス（kabusys.config）を参照してください。多くの経路はデフォルト値が用意されています（例: DuckDB/SQLite のファイルパス）。

## 実行方法（Usage）

※いずれもプロジェクトルートで実行することを想定しています。

- ExecutionEngine（発注エンジン）起動
  - 本番 / 開発 / Paper Trading を切り替えるには環境変数 `KABUSYS_ENV` を設定します。
  - Paper Trading: `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し DB は `data/paper_trading.db` に分離されます。
  - 起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - エンジンは `data/execution.pid` に PID を書きます。停止は監視用のフラグファイル `data/stop_requested.flag` を作成するか、外部から kill してください。

- Monitoring（監視ループ）起動
  - 起動:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。Monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しません）。

- Streamlit 監視ダッシュボード
  - 起動（例: Monitoring DB を read-only で参照）:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - Web UI による状態確認、Positions / Orders / System / Dashboard 表示が可能です。

- Paper Trading 検証レポート（コマンドライン）
  - レポート生成:
    ```bash
    python -m kabusys.tools.paper_verification_report \
      --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
    ```
  - `--db` を省くと環境変数 `PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db` を利用します。

- AI スコアリング / 市場レジーム判定（ライブラリ API）
  - ニューススコアリング:
    - 関数: `kabusys.ai.score_news(conn, target_date, api_key=None)`（DuckDB 接続を渡す）
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - どちらも OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` で指定します。API 呼び出し失敗時のフォールバックやリトライの実装があります。

## 停止・フラグファイル
- 実行中プロセスの停止は以下のフラグファイルで制御できます:
  - data/stop_requested.flag — run_execution / run_monitoring のループを終了させる外部フラグ
  - data/kill.flag — KillSwitch が検出・書き込みすることで ExecutionEngine 停止要求を表明（ExecutionEngine は Settings.kill_flag_path を参照）
- Execution エンジンは PID を `data/execution.pid` に書きます。古い PID が存在し、プロセスが存在しない場合は stale PID として検出・削除されます（SystemMonitor の処理）。

## 設定（主要な環境変数）
（Settings クラスに定義されているプロパティの主要項目）
- KABUSYS_ENV: 動作環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の約定挙動: instant | partial | never | reject)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- LOG_LEVEL

.env 自動読み込み:
- プロジェクトルートにある `.env` と `.env.local` を自動でロードします（OS 環境変数が優先されます）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## ディレクトリ構成（Directory structure）
（主要ファイルのみ要約）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（Settings）
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 株数計算・配分調整
    - risk_adjustment.py      — セクター制限・レジーム乗数
  - execution/
    - order_manager.py        — 注文管理
    - reconciler.py           — 再起動時のリコンシリエーション
    - (その他 broker/ repository 関連モジュール)
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - alert_manager.py        — LINE 通知
    - kill_switch.py          — kill.flag 管理
    - monitoring_engine.py    — 各モニタを束ねるエンジン
    - streamlit_dashboard.py  — Streamlit ダッシュボード
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + LLM 結合）
  - research/
    - factor_research.py      — ファクター計算（momentum / value / volatility）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - data/                     — 実行時に使用する DB / flag など（プロジェクトルート直下に想定）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート

（各サブパッケージにはさらに補助モジュール・テストが存在する可能性があります）

## 開発上の注意事項 / 実運用時の注意
- Monitoring は常に Settings.sqlite_path（本番監視 DB）を参照します。paper_trading 環境下でも監視は本番 DB を使用する仕様です。
- Paper Trading は発注処理を本番 DB と分離するため `PAPER_TRADING_SQLITE_PATH` を使用します。実際の実行（kabu API への発注）を行う場合は `KABUSYS_ENV=live` を確認してください。
- OpenAI の呼び出しはコストが発生します。API キー・レート制限に注意してください。失敗時のフォールバック処理が実装されていますが、意図しないループを避けるためログを監視してください。
- process priority / CPU affinity の設定はプラットフォーム依存です（psutil を使用）。権限不足で設定できない場合は警告ログが出力されます。
- DB マイグレーション（monitoring_db.init_monitoring_db）で既存カラムがない場合は自動追加していますが、完全なスキーマ管理ツールは別途用意することを推奨します。

---

README の内容はコードベースの説明に基づいて作成しています。運用やデプロイに合わせて .env の例ファイル（.env.example）を作成し、requirements.txt / Poetry 等で依存管理を整備することを推奨します。必要であれば README に含める .env.example のテンプレートや、systemd / Docker 用の起動例も作成できます。希望があれば指定してください。