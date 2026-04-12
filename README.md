# KabuSys

日本株向け自動売買フレームワークの参照実装（モジュール群のみ）。  
この README はリポジトリ内のソースコードから抜粋した動作説明・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

注意: 本リポジトリにはブローカー接続等の実運用に関わるコードが含まれます。実際に資金を動かす前に十分なテストと安全確認を行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買／研究／監視を行うためのモジュール群です。主な機能は次の通りです。

- ExecutionEngine（発注エンジン）: ブローカー API 経由での注文管理・リスク管理・再同期（リコンシリエーション）
- Monitoring（監視）: システム状態・データ鮮度・注文滞留・ドローダウン等の監視、アラート通知、kill flag 発行
- Portfolio construction: 候補選定・重み計算・ポジションサイズ計算・セクター制限
- Research: ファクター計算（Momentum/Value/Volatility 等）・将来リターン・IC 計算
- AI 支援: ニュース記事を LLM（OpenAI）でセンチメント化してスコア化、マクロセンチメントと MA200 乖離を合成して市場レジーム判定
- Tools: Paper Trading 検証レポート生成、簡易ダッシュボード（Streamlit）など
- DB 層: DuckDB（市場データ等）・SQLite（監視ログ / paper_trading）を使用

設計方針のハイライト:
- DuckDB を用いた履歴処理（SQL + Python）
- SQLite を監視ログや発注履歴に利用（ファイル単位で環境分離可能）
- OpenAI API 呼び出しはフェイルセーフ実装（リトライ・部分失敗保護）
- .env / .env.local から設定を読み込み（自動ロードは無効化可能）

---

## 機能一覧（抜粋）

- run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV によって paper_trading モードで MockBroker を使用可。
- run_monitoring.py: SystemMonitor をポーリングする監視ループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔指定可。
- monitoring:
  - SystemMonitor: CPU/メモリ/ディスク・プロセス・データ鮮度チェック
  - TradeMonitor: 注文の滞留チェック・約定価格異常チェック
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: 条件に応じて kill.flag を書き、ExecutionEngine に停止を促す
  - AlertManager: LINE Messaging API を用いた通知（クールダウン管理）
  - streamlit_dashboard: Streamlit ベースの監視ダッシュボード
- portfolio:
  - 銘柄選定（スコア降順）、等比率／スコア比率配分、リスクベースのポジションサイズ算出、セクターキャップ適用、レジーム乗数
- research:
  - ファクター計算（モメンタム/ボラティリティ/バリュー）、将来リターン、IC/統計サマリー
- ai:
  - news_nlp.score_news(): raw_news を LLM でスコアし ai_scores に書き込む
  - regime_detector.score_regime(): マクロ記事＋MA200 を合成して market_regime に書き込む
- tools.paper_verification_report: Paper Trading DB（data/paper_trading.db など）から検証レポートを出力

---

## 前提・依存

推奨 Python バージョン: 3.10+（型アノテーションで | 記法を使用）

主要依存ライブラリ（一例）:
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

必要に応じて requirements.txt を作成して `pip install -r requirements.txt` を推奨します。

---

## 環境変数と設定（Settings）

設定は環境変数およびルートの `.env`, `.env.local` から自動読み込みされます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な環境変数:
- KABUSYS_ENV: 起動環境（"development" | "paper_trading" | "live"） — デフォルト "development"
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI 利用時に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading モードの約定挙動（"instant" | "partial" | "never" | "reject"、デフォルト "instant"）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill flag ファイル（デフォルト: data/kill.flag）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定なら通知はスキップ）

必須環境変数が欠けていると Settings が例外を投げます（起動前に .env を用意してください）。

.env の例（最低限）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=your_openai_api_key
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## セットアップ手順

1. 仮想環境の作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell)
   ```

2. 依存パッケージのインストール
   ```
   pip install duckdb psutil requests openai streamlit
   ```

3. .env を作成
   - リポジトリルートに `.env`（と必要なら `.env.local`）を作成し、必要な環境変数を設定します。
   - 自動ロードを一時的に無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. データディレクトリ作成（デフォルト）
   ```
   mkdir -p data
   ```

5. （任意）DuckDB や SQLite の初期データ投入
   - モジュールは起動時に監視テーブル等を冪等で初期化します（init_monitoring_db が実行されます）。
   - 市場データ用の DuckDB テーブル（prices_daily / raw_financials / raw_news など）は別プロセスで用意してください（本 README ではデータロード手順は含めません）。

---

## 使い方（代表的な実行方法）

- ExecutionEngine を起動（本番／ペーパートレード判定は KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading にすると MockBroker を使用し、PAPER_TRADING_SQLITE_PATH の DB に書き込みます。
  - 起動時にプロセス優先度を High に設定します（psutil による設定。権限不足だと警告でスキップ）。

- Monitoring（SystemMonitor 単体）をポーリングで起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は MonitoringDB（SQLite）にログを書き込みます。

- Streamlit ダッシュボード（読み取り専用）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - Monitoring が作成する monitoring.db を読み取り専用で開きます。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI スコアリング / レジーム判定（Python API）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、ai_scores / market_regime 等テーブルを更新します。OpenAI キーを渡すか環境変数 OPENAI_API_KEY を設定してください。

---

## 重要な運用上の挙動・注意点

- .env の自動読み込み
  - ルート（.git か pyproject.toml があるディレクトリ）から `.env`、`.env.local` を順に読み込みます。OS 環境変数は保護され、explicit override が制御できます。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- Paper Trading 分離
  - KABUSYS_ENV=paper_trading のとき、ExecutionEngine は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離されます。
  - PAPER_FILL_MODE により MockBroker の約定挙動を制御できます（instant / partial / never / reject）。

- モニタリング → KillSwitch
  - RiskMonitor が DRAWDOWN や POSITION_LIMIT を検出すると KillSwitch が `data/kill.flag` を生成し、ExecutionEngine 側はこのファイルの存在を見て停止する設計です。
  - kill.flag のパスは Settings.kill_flag_path で変更可能。Execution 起動時に KILL_FLAG_CLEAR_ON_START を有効にすると自動クリアできます。

- OpenAI 呼び出し
  - API はリトライ（指数バックオフ）を組み込んでいますが、最終的に失敗した場合はフェイルセーフ（スコア 0.0 など）で継続します。
  - OPENAI_API_KEY 未設定だと ValueError が発生する関数があります（AI 機能を使う場合は必須）。

- プロセス優先度 / CPU affinity
  - 起動スクリプトは psutil を使ってプロセス優先度を設定します。権限不足だとログ警告でスキップします。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要モジュールのツリー（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート（CLI）
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py    — レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py      — SQLite 用永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 execution 関連モジュールは省略)
  - utils/
    - __init__.py
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (想定されるデータディレクトリ)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

（実際の repo にはここに示した以外のファイル／モジュールも存在します。上はコードベースから抜粋した主要箇所です。）

---

## トラブルシューティング

- 起動時に Settings が ValueError を出す
  - 必須環境変数が未設定です。.env.example を参考に .env を用意してください。

- psutil による優先度設定で AccessDenied が出る
  - 管理者権限が必要な場合があります。権限不足時はログで警告され、動作は継続されます。

- OpenAI 呼び出しが失敗する
  - OPENAI_API_KEY を設定してください。API のレート制限やネットワークエラー時にはリトライが行われますが、最終的に失敗する場合は該当処理がスキップされます。

- Streamlit ダッシュボードで DB を開けない
  - Monitoring が起動していない、または指定した path が間違っている可能性があります。`--db` で正しい monitoring.db ファイルを指してください。

---

## 開発上のヒント

- 自動 .env 読み込みは便利ですが、ユニットテストや CI で不要な副作用を避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してから Settings を直接差し替えて使うと良いです。
- DuckDB を使ったファクター計算や research は外部 API に依存しない設計です。DuckDB にテーブル（prices_daily / raw_financials / raw_news 等）を用意してユニットテストを行ってください。
- OpenAI 呼び出し部分は内部で `_call_openai_api` の関数を呼ぶ実装になっており、テスト時は patch してモック化できます（ソース内にその旨のコメントあり）。

---

この README はコードベースの主要点を抜粋してまとめたものです。さらに詳細な API 仕様や DB スキーマ・設計文書（PortfolioConstruction.md / StrategyModel.md 等）がリポジトリに存在する場合はそれらも参照してください。必要であれば README の改善点（例: 環境変数の完全一覧、requirements.txt、データロード手順）を追記しますので指示ください。