# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視ツール群を含むパッケージです。  
本リポジトリは注文管理（Execution）、監視（Monitoring）、ポートフォリオ構築（Portfolio）、リサーチ（Research）、AI を使ったニュース評価などの機能を提供します。

バージョン: 0.1.0

---

## 概要

- 注文発行・状態管理を行う Execution エンジン（本番／Paper Trading 切替対応）。
- システム・注文・リスク監視（ログ永続化、LINE 通知、kill-switch）。
- ポートフォリオ構築関数群（候補選定、重み決定、ポジションサイズ計算、セクター制限など）。
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー）、IC/統計解析ユーティリティ。
- AI を使ったニュースセンチメント評価・市場レジーム判定（OpenAI 利用）。
- 検証用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）。

設計上の特徴：
- DB は SQLite（監視ログ等）と DuckDB（時系列・ファクタ計算）を併用。
- Paper Trading は本番 DB と分離（専用 SQLite）。  
- .env 自動読み込み機能（プロジェクトルートを基準）。  
- 実プロセス優先度を設定するユーティリティ（psutil を利用）。

---

## 主な機能一覧

- Execution
  - 注文作成 / 送信 / 同期 / リコンサイル（再起動時の復旧）
  - RiskManager、OrderManager、Reconciler、ExecutionEngine
  - Paper Trading モード（モックブローカー、専用 DB、PAPER_FILL_MODE 制御）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス/データ鮮度の監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード集計の更新
  - KillSwitch / AlertManager（LINE 通知）
  - MonitoringEngine によるポーリングループ、Streamlit ダッシュボード

- Portfolio
  - 候補選定（select_candidates）、重み計算（等ウェイト／スコア加重）
  - ポジションサイズ算出（risk_based / equal / score）
  - セクターキャップ適用、レジーム乗数計算

- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリー

- AI
  - news_nlp: raw_news から銘柄別センチメントを生成して ai_scores に保存（OpenAI）
  - regime_detector: ETF とマクロ記事の組合せで市場レジーム判定

- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ベースの監視ダッシュボード

---

## セットアップ手順

必要な外部パッケージ（代表例）:
- python (3.9+ 推奨)
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)

（プロジェクトに requirements.txt がない場合は手動でインストールしてください）
例:
```
pip install duckdb psutil requests openai streamlit
```

1. リポジトリをクローンし、作業ディレクトリを移動
2. 仮想環境を作成・有効化（任意）
3. 必要パッケージをインストール（上記参照）
4. 環境変数を準備
   - .env をプロジェクトルートに置くと自動で読み込まれます（.env.local は上書き）。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（主なもののみ）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須機能を使う場合）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）で必須
- KABUSYS_ENV — 環境: `development` | `paper_trading` | `live`（デフォルト: development）
- LOG_LEVEL — ログレベル（例: INFO）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定挙動: `instant` | `partial` | `never` | `reject`（デフォルト: instant）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

注意:
- .env の読み込み順は OS 環境 > .env.local > .env（.env.local は上書き）。ただし OS 環境は保護されます。

---

## 使い方（代表的なコマンド）

プロジェクトルートで実行することを前提とします（data ディレクトリ等は自動作成されます）。

- 監視ループを起動（Monitoring）
```
python -m kabusys.run_monitoring
```
- ExecutionEngine を起動（実注文エンジン / Paper Trading は KABUSYS_ENV による切替）
```
python -m kabusys.run_execution
```
実行時の挙動:
- run_monitoring は常に Settings.sqlite_path（本番監視 DB）を使用します（KABUSYS_ENV に依存しません）。
- run_execution は KABUSYS_ENV=`paper_trading` のとき専用 DB (`PAPER_TRADING_SQLITE_PATH`) を使います。
- stop フラグ: 実行中にファイル `data/stop_requested.flag` が存在すると両スクリプトは安全に停止します。
- ExecutionEngine は起動時に `data/execution.pid` を使用／作成します。stale PID を検出すると監視が記録されます。

- Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB 指定
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- Streamlit ダッシュボード（監視ダッシュボード）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- AI（ニューススコアリング / レジーム判定）
  - これらはプログラムまたはスケジューラから呼び出します。例（Python）:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026,4,11), api_key="sk-...")
print("written:", n)
```
OPENAI_API_KEY を環境変数に設定しておけば api_key 引数は省略可。

---

## 停止・Kill スイッチについて

- run_monitoring / run_execution はプロジェクト内 `data/stop_requested.flag` を監視しています（存在でループ終了）。
- KillSwitch（監視ロジック）はリスク条件を満たした際に `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを出します。
- `KillSwitch.clear()` により kill.flag を削除できます（Execution 起動前のクリーンアップ用）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイルとディレクトリ構成です（省略あり）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - data/                    — 実行時に使用される SQLite/DuckDB/flag/pid など（デフォルト path: data/）
  - utils/
    - process_priority.py    — プロセス優先度設定ユーティリティ
  - monitoring/
    - monitoring_db.py       — 監視ログ用 SQLite 操作層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - execution_engine.py
    - broker_factory.py
    - ... (ブローカー API 抽象等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（上記は主要モジュールに限定した一覧です。詳細はソースを参照してください）

---

## 開発時の注意事項 / 補足

- DB マイグレーション: monitoring_db.init_monitoring_db() は冪等でテーブル作成・簡易マイグレーション（カラム追加）を行います。
- Paper Trading モードでは、本番 DB と分離して `PAPER_TRADING_SQLITE_PATH` に記録されます（安全な検証が可能）。
- OpenAI の呼び出しはネットワーク/429/5xx 等を考慮したリトライを実装していますが、API キーの管理やコストに注意してください。
- .env パーサは一般的な shell 形式（export 含む）に対応し、クォートやインラインコメントの取り扱いに配慮した実装になっています。
- プロセス優先度設定や CPU affinity 設定は psutil に依存し、権限や OS によってセットに失敗することがあります（警告ログによりスキップされます）。

---

README に書かれていない詳細な使用方法や API 形状は、各モジュール（src/kabusys 以下）の docstring と関数シグネチャを参照してください。必要であれば、特定モジュール用の詳しいドキュメントも作成します。