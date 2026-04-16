# KabuSys

日本株向けの自動売買 / リサーチ基盤（モジュール群・実行ランナー・監視機能を含む）。  
このリポジトリは、注文エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、LLM を使ったニュース評価などの機能を持つ。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような機能を持つ自動売買プラットフォームのプロトタイプ実装です。

- 注文生成とブローカーインタフェース（paper/live 切替）
- ExecutionEngine（発注実行・リスク管理・リコンシリエーション）
- 監視 (System / Trade / Risk) とアラート（LINE Push）
- 監視データの永続化（SQLite）とダッシュボード（Streamlit）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ファクター計算・リサーチユーティリティ（DuckDB ベース）
- ニュース NLP / レジーム判定（OpenAI を利用）
- 運用用ユーティリティ（プロセス優先度設定、kill flag 制御 等）

---

## 主な機能一覧

- monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス有無を監視
  - TradeMonitor: 滞留注文、約定異常を検出
  - RiskMonitor: ドローダウン／ポジション数監視・リスクログ化
  - KillSwitch: しきい値超過で `data/kill.flag` を書き、ExecutionEngine を停止させる
  - AlertManager: LINE に一方向のプッシュ通知
  - Streamlit ダッシュボード（read-only）
- execution
  - ExecutionEngine: 発注ループ・セッション管理
  - OrderManager / OrderRepository: 注文の状態管理・永続化
  - Reconciler: 再起動時の照合（ブローカーとの同期）
  - BrokerFactory: KABUSYS_ENV に応じて実ブローカー / モックを切替
- portfolio
  - 候補選定、等重/スコア重み、リスク調整（セクターキャップ）、ポジションサイズ計算
- research
  - ファクター計算（momentum/value/volatility）
  - 特徴量探索（forward returns / IC / summary）
- ai
  - ニュースのセンチメント評価（OpenAI）と ai_scores への書き込み
  - レジーム判定（マクロ＋ETF MA200 乖離から daily レジーム判定）
- utils
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 前提 / 必要ソフトウェア

- Python 3.9+
- SQLite（Python に組み込み）
- 推奨 Python パッケージ（最低限）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
（requirements.txt があればそれを使ってください）

例（仮想環境作成・インストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローン / 展開する
2. Python 仮想環境を作成して依存をインストール
3. 環境変数を設定（.env / .env.local を利用可。自動読み込みされます）
   - 自動ロードを無効化する場合:
     - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
4. 必要なディレクトリを作る（`data/` 等）
```bash
mkdir -p data
```
5. （paper_trading を使う場合）`data/paper_trading.db` の初期化やテストデータを用意

---

## 主要な環境変数（代表例）

- KABUSYS_ENV
  - 値: `development` | `paper_trading` | `live`
  - デフォルト: `development`
- SQLITE_PATH
  - 監視用 SQLite（monitoring.db）のパス（デフォルト: `data/monitoring.db`）
- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- PAPER_TRADING_SQLITE_PATH
  - paper_trading モードで使用する専用 SQLite（デフォルト: `data/paper_trading.db`）
- PID_FILE_PATH
  - ExecutionEngine の PID ファイルパス（デフォルト: `data/execution.pid`）
- KILL_FLAG_PATH
  - KillSwitch のフラグファイル（デフォルト: `data/kill.flag`）
- MONITOR_POLL_INTERVAL
  - Monitoring のポーリング間隔（秒）。1 以上の整数を指定（デフォルト: 60）
- PAPER_FILL_MODE
  - paper_trading の MockBroker の約定モード: `instant` | `partial` | `never` | `reject`（デフォルト: `instant`）
- OPENAI_API_KEY
  - OpenAI 呼び出しに必要（ai/news_nlp.py, ai/regime_detector.py）
- KABU_API_PASSWORD, JQUANTS_REFRESH_TOKEN, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID など
  - 各外部 API 用のトークン類

簡易 .env 例:
```
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
PAPER_FILL_MODE=instant
```

---

## 実行方法（代表コマンド）

- 監視ループを起動（モニタリング用）
```bash
python -m kabusys.run_monitoring
# 環境変数で間隔を変更
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
注: run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（Settings.sqlite_path）を使用します。

- ExecutionEngine を起動（発注エンジン）
```bash
python -m kabusys.run_execution
```
- Streamlit ダッシュボード（ローカルで監視状態確認）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポート生成
```bash
python -m kabusys.tools.paper_verification_report
# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パス指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- AI スコア / レジーム判定（モジュール API を利用）
  - これらはライブラリ関数として提供されています。例（スクリプトや REPL から）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
# NEWS スコアリング（OPENAI_API_KEY 必須）
score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
# レジーム判定
score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
```

---

## 運用・運転上の注意点

- stop フラグ / kill フラグ
  - run_execution.py / run_monitoring.py はプロジェクト直下の `data/stop_requested.flag`（あるいは Settings.kill_flag_path の `kill.flag`）で停止命令を検知します。
  - KillSwitch は `data/kill.flag` を書き込み ExecutionEngine に停止を促します（ExecutionEngine は起動時に `kill.flag` を検出したら起動しません）。
- PID ファイル
  - ExecutionEngine は `data/execution.pid` に PID を書きます（Settings.pid_file_path 参照）。stale PID が検出されると SystemMonitor が削除してリスクログを追加します。
- MONITOR_POLL_INTERVAL は 1 以上の整数にしてください。0 や負値を与えるとデフォルト（60秒）にフォールバックします。
- OpenAI 関連
  - API キーが未定義の場合、score_news / score_regime は ValueError を出します（呼び出し側で api_key を渡すか環境変数を設定してください）。
  - レート制限や一時的な API エラーは内部でリトライしますが、失敗時はフェイルセーフ（ゼロ判定やスキップ）で継続する設計です。
- プロセス優先度変更
  - set_process_priority は OS によって権限が必要な場合があります（psutil.AccessDenied の可能性）。権限がない場合は警告ログを出してスキップします。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings 管理（.env 自動ロード機構あり）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- utils/
  - process_priority.py — プロセス優先度・CPU affinity ユーティリティ
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・永続化層
  - system_monitor.py — システム状態 / データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常検知
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py — 注文ライフサイクル管理（OrderManager）
  - reconciler.py — 起動時のリコンシリエーション
  - (その他ブローカー周り / engine 等はリポジトリ内に存在)
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 発注株数計算（lot 丸め・aggregate cap）
  - risk_adjustment.py — セクターキャップ / レジーム乗数
- research/
  - factor_research.py — momentum/value/volatility 計算（DuckDB）
  - feature_exploration.py — forward returns / IC / 統計
- ai/
  - news_nlp.py — ニュース集約・OpenAI による銘柄別センチメント評価
  - regime_detector.py — マクロ + MA200 によるレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

（上記は主要モジュールの抜粋です。実際のファイルはさらに細かい実装ファイルが存在します。）

---

## 開発 / テストのヒント

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI やテスト環境で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB / SQLite を使う関数群は接続を外部から渡す設計なので、テスト時はインメモリ / テスト DB を使ってユニットテストを実行できます。
- OpenAI 呼び出しは `_call_openai_api` のパッチでモック可能です（unit テスト用の差し替えポイントが用意されています）。

---

## トラブルシューティング

- psutil による優先度変更で AccessDenied が出る → 実行ユーザーの権限を確認（root / 管理者権限が必要な場合あり）。ログは無害に処理されます。
- Streamlit で DB が開けない（読み取り専用 URI） → MonitoringEngine を起動して DB を作成しているか確認。read-only オープンを試みるので DB ファイルが存在しないとエラーになります。
- OpenAI API エラーが頻発する → API キー／ネットワーク／レートに注意。内部で一時的なリトライを行いますが上限があります。

---

必要に応じて README を拡張します。例えば CI 用のセットアップ、requirements.txt の追加、より詳細な運用手順（systemd ユニット定義、ロギング設定、バックアップ方法）などを追記できます。どの部分を詳しく書いてほしいか教えてください。