# KabuSys

KabuSys は日本株向けの自動売買・リサーチ・監視フレームワークの一部です。  
このリポジトリには、実行エンジン・監視コンポーネント・ポートフォリオ構築・リサーチ・AI（ニュース NLP / レジーム判定）などのモジュールを含みます。

注意: この README はコードベース（src/ 以下）から読み取れる仕様をまとめた概要ドキュメントです。

---

## プロジェクト概要

- 自動発注のための ExecutionEngine（発注管理、リスク管理、再同期機能）
- 監視サブシステム（System / Trade / Risk モニタ、アラート、kill switch、ストリームリットによるダッシュボード）
- ポートフォリオ構築ユーティリティ（候補選定、重み・ポジションサイズ計算、セクター制限）
- リサーチ機能（ファクター計算、特徴量解析、将来リターン、IC 計算）
- AI モジュール（ニュースを LLM でスコアリング、マクロニュース + ETF MA で市場レジーム判定）
- ツール群（Paper Trading 検証レポート生成など）

主要設計方針（抜粋）:
- ロジックの多くは純粋関数または DB 抽象層に分離されている。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離して動作する。
- ルックアヘッドバイアスを防ぐ設計（date.today() 直接参照を回避、SQL の date 条件注意など）。
- OpenAI/API 呼び出しはリトライ・フォールバックを実装してフェイルセーフにする。

---

## 主な機能一覧

- Execution
  - OrderManager、OrderRepository、Reconciler による起動時再同期と堅牢な発注フロー
  - RiskManager によるポジション／利用率制限
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存チェック・データ鮮度チェック
  - TradeMonitor: 滞留注文／約定異常価格の検出
  - RiskMonitor: ドローダウン、ポジション上限監視
  - KillSwitch: フラグファイルで ExecutionEngine を停止指示
  - AlertManager: LINE Push を用いたアラート送信（クールダウン付き）
  - Streamlit ダッシュボード（読み取り専用で監視状況を可視化）
- Portfolio
  - 候補選定（select_candidates）、等重／スコア重み付け、ポジションサイズの算出
  - セクターキャップ適用、レジーム乗数計算
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン、IC（Spearman）計算、統計サマリー
- AI
  - news_nlp.score_news: raw_news をまとめて OpenAI に送り銘柄毎にセンチメントを ai_scores テーブルへ格納
  - regime_detector.score_regime: ETF (1321) の MA200 とマクロニュースの LLM スコアを合成して market_regime に書き込み
- ツール
  - tools.paper_verification_report: Paper Trading の運用検証レポートを生成

---

## 必要条件 / 依存パッケージ

- Python 3.10+（構文で union types (A | B) を使用）
- 必要な Python パッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)
- SQLite（組み込み）
- （任意）.env ファイルの利用には .env/.env.local をプロジェクトルートに配置

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主なもの）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

主な環境変数とデフォルト:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の MockBroker 挙動 ("instant" | "partial" | "never" | "reject")（デフォルト "instant"）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60。無効値はデフォルトにフォールバック）
- LOG_LEVEL: ログレベル（"DEBUG","INFO"...）

PAPER_FILL_MODE の有効値: instant, partial, never, reject

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化
2. 依存パッケージをインストール（上記参照）
3. プロジェクトルートに `.env`（もしくは `.env.local`）を作成して必要な環境変数を設定
   - 例:
     ```
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_password
     JQUANTS_REFRESH_TOKEN=...
     ```
4. データディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```
5. DuckDB / SQLite の初期テーブルはモジュール起動時（init_monitoring_db 等）で自動作成されます

---

## 実行方法（代表的なコマンド）

- 監視ループを起動（SystemMonitor の簡易起動）
```bash
python -m kabusys.run_monitoring
# 環境変数で間隔を変更:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）
```bash
python -m kabusys.run_execution
# paper_trading モードの例:
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- Paper Trading 検証レポート生成
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB を直接指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
- Streamlit ダッシュボード（監視 DB の読み取り専用表示）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

---

## 使い方（主要コンポーネントの利用例）

- Monitoring
  - run_monitoring を常駐プロセスとして動かすと、SystemMonitor/TradeMonitor/RiskMonitor 相当のチェックを一定間隔で行い、SQLite（SQLITE_PATH）にログを残します。
  - AlertManager 経由で LINE に通知可能（トークン/ユーザーID の設定が必要）。
  - KillSwitch により kill.flag を作成し、ExecutionEngine に停止シグナルを送る運用が可能。

- Execution（本番・Paper）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper DB（PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と完全分離されます。
  - Reconciler は起動時に OrderSent の未決着注文をブローカーと突合して同期します。
  - 設定例: 起動時に process priority を "high" に設定（プラットフォーム依存で失敗する場合は警告でスキップ）。

- Research / AI
  - Research モジュールは DuckDB 接続を受け取り、prices_daily / raw_financials 等テーブルを参照してファクターや将来リターンを計算します。
  - AI モジュールは OpenAI を利用（OPENAI_API_KEY 必須）。news_nlp.score_news や regime_detector.score_regime を直接呼び出して結果を DB に書き込みます。
  - API 呼び出しはレート制限・一時エラーに対するリトライや、失敗時のフォールバック（0.0 やスキップ）を行います。

---

## ディレクトリ構成（src/kabusys の主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env ロード・Settings
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py — マクロ + ETF MA によるレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite スキーマと DB 操作ラッパー
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 滞留注文・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねる
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・等重/スコア重み
    - position_sizing.py — 発注株数算出（lot 単位丸め、集約キャップ）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - execution/
    - order_manager.py — 発注ワークフロー（状態遷移、重複チェック）
    - reconciler.py — 起動時の同期・ポジション差分検出
    - （その他: broker_factory, order_repository 等は実装ファイルが存在）
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

（注）この一覧はコードベースからの抜粋です。実際の機能は関連モジュール間の連携で成り立ちます。

---

## 運用上の注意点 / ヒント

- 自動環境読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` / `.env.local` を自動ロードします。テストや CI などで無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合は paper_db（PAPER_TRADING_SQLITE_PATH）へ書き込まれ、本番データと完全分離されます。
- OpenAI / API:
  - OPENAI_API_KEY が未設定のとき AI モジュールは例外を投げます。自動運用では環境変数に設定してください。
  - API 呼び出しはリトライロジックを持ちますが、過度の呼び出しを防ぐためバッチサイズや待機戦略を確認してください。
- MONITOR_POLL_INTERVAL:
  - run_monitoring は環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書きできます。無効値（0 や負数、数値以外）は警告されデフォルト 60 秒にフォールバックします。
- 権限:
  - process priority / cpu affinity の設定は OS 権限に依存します。失敗時は警告でスキップされます。

---

## 開発 / テスト

- モジュールはできるだけ副作用を抑えて実装されています（関数は DB 接続や DuckDB 接続を引数で受け取る、OpenAI 呼び出しをラップする等）。ユニットテストでは外部呼び出し（OpenAI / requests / psutil）をモックすることで高速にテストできます。
- Streamlit ダッシュボードは読み取り専用モード（SQLite を read-only URI で開く）で運用できます。

---

もし README に追加したいサンプル .env のテンプレートや、各スクリプトのより詳細な運用フロー（起動順序、systemd / Docker でのデプロイ例）などが必要でしたら、用途に合わせて追記します。