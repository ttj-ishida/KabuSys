# KabuSys

日本株向けの自動売買システムのコアライブラリ群（シグナル / ポートフォリオ構築 / 実行 / 監視 / 研究 / AI ユーティリティ）。この README はリポジトリ内の主要モジュールと使い方をまとめたものです。

注意: 本 README はソースコード（src/kabusys 以下）を参照して作成しています。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成されます。

- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定）
- リスク調整（セクター上限、レジーム乗数）
- 実行エンジン周り（OrderManager、Reconciler、ExecutionEngine 起動スクリプト）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor、監視 DB、アラート送信）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- 研究ユーティリティ（ファクター計算・IC 計算など）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針の一例:
- DuckDB / SQLite をデータ層に利用し、分析や監視ログを永続化する。
- 環境変数 / .env による設定管理（kabusys.config.Settings）。
- Paper trading 用に本番 DB を分離（PAPER_TRADING_SQLITE_PATH）。
- LLM 呼び出し（OpenAI）に対してはリトライやバリデーションを実装してフェイルセーフ化。

---

## 機能一覧（抜粋）

- ポートフォリオ
  - select_candidates、calc_equal_weights、calc_score_weights
  - calc_position_sizes（risk_based / equal / score）
  - apply_sector_cap、calc_regime_multiplier
- 実行（execution）
  - OrderManager（発注フロー）、Reconciler（自動復旧）
  - Broker クライアントを抽象化する工場パターン（paper_trading 用の Mock 対応）
- 監視（monitoring）
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセス生存、データ鮮度チェック
  - TradeMonitor：滞留注文、約定異常価格の検出
  - RiskMonitor：ドローダウンやポジション上限の監視、kill.flag 生成
  - AlertManager：LINE Messaging API で通知（クールダウン管理あり）
  - MonitoringDB：監視用 SQLite スキーマ（system_status / trade_logs / positions / risk_logs / dashboard）
  - Streamlit ダッシュボード（監視 DB を可視化）
- AI
  - news_nlp.score_news：ニュース記事をまとめて OpenAI でセンチメント評価し ai_scores に書き込む
  - regime_detector.score_regime：ETF の MA200 とマクロニュースの LLM 評価を合成して日次レジーム判定
- ツール
  - tools.paper_verification_report：Paper Trading DB に対する検証レポート出力

---

## 必要要件（推奨）

- Python 3.9+
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite は標準ライブラリで使用

（プロジェクトに requirements.txt があればそちらを使ってください。なければ上記を pip install してください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
```

---

## セットアップ手順

1. リポジトリをクローン（省略）
2. Python 仮想環境を作成して依存パッケージをインストール（上記参照）
3. 環境変数を設定 (.env または .env.local をプロジェクトルートに配置可能)
   - 自動読み込みは Settings モジュールで行われます（.git または pyproject.toml を基準にプロジェクトルートを探索）
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV（development | paper_trading | live） — デフォルトは development
5. データディレクトリの初期化
   - default path:
     - monitoring DB: data/monitoring.db （Settings.sqlite_path）
     - duckdb: data/kabusys.duckdb （Settings.duckdb_path）
     - paper trading DB: data/paper_trading.db
   - 監視 DB は起動時に init_monitoring_db() でテーブルが作成されます（冪等）

サンプル .env（最低限の例）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LINE_CHANNEL_ACCESS_TOKEN=   # 任意
LINE_USER_ID=                # 任意
LOG_LEVEL=INFO
```

---

## 使い方（起動・コマンド）

このリポジトリはパッケージとしてインストールせずに `PYTHONPATH=src` を指定して実行できます。プロジェクトルートから次のように実行してください。

共通: パスを通す（パッケージとしてインストールしない場合）
```
export PYTHONPATH=src
```

1. 監視ループを起動（SystemMonitor を定期実行）
```
# デフォルト poll 間隔 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可）
MONITOR_POLL_INTERVAL=60 PYTHONPATH=src python -m kabusys.run_monitoring
```
- 注意: run_monitoring は常に「本番 sqlite_path」（Settings.sqlite_path）を監視用 DB に使用します（KABUSYS_ENV に依存しない点に注意）。

停止:
- プロジェクトルートの `data/stop_requested.flag` を作成すると、ポーリングループが検知して自然終了します。

2. ExecutionEngine を起動（注文実行エンジン）
```
# paper_trading モード（MockBrokerClient を使用し data/paper_trading.db を利用）
KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution

# 本番（live）モード
KABUSYS_ENV=live PYTHONPATH=src python -m kabusys.run_execution
```
- 実行時、プロセス優先度を high に設定します（可能な環境でのみ適用）。
- 停止は `data/stop_requested.flag` の作成でトリガされます。
- ExecutionEngine は paper_trading の場合、paper_sqlite_path（Settings.paper_sqlite_path）を使用して完全に分離された DB で動作します。

3. Streamlit 監視ダッシュボード（ローカルで可視化）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- 監視 DB を読み取り専用で開きます（存在しない場合は開始メッセージが出ます）。

4. Paper Trading 検証レポートの生成
```
# デフォルト DB: data/paper_trading.db
PYTHONPATH=src python -m kabusys.tools.paper_verification_report

# 期間指定（例）
PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB パスを明示する場合
PYTHONPATH=src python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

5. AI 機能（スコア付与・レジーム判定）
- news_nlp.score_news と regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）を必要とします。プログラムから呼び出す際は api_key 引数でも渡せます。
- 例（Python スクリプト内で）:
```py
from kabusys.ai.news_nlp import score_news
import duckdb, datetime
conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, datetime.date(2026, 4, 1), api_key="sk-...")
```

---

## 主要な設定（Settings）と環境変数の挙動

kabusys.config.Settings で各種値を取得します（主なもの）:

- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - settings.is_paper / is_live / is_dev で切り分け可能
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視用デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE（instant | partial | never | reject、デフォルト instant）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START：監視・制御用ファイル位置
- LOG_LEVEL（デフォルト INFO）

.env ファイルのパースは独自実装で、.env / .env.local の自動読み込みロジックあり（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

---

## 実装ノート / 運用上の注意

- 監視（monitoring）は run_monitoring から動かす想定。監視は常に settings.sqlite_path を使用する（paper_trading の場合でも監視 DB は本番パスを使う点に注意）。
- ExecutionEngine は paper_trading モード時に mock broker と専用 DB を使って本番と切り離す設計。
- PID / stop flag:
  - 実行エンジンは data/execution.pid を PID 管理に使用（spawn 時にファイル作成）。
  - 停止を外部から要求するには data/stop_requested.flag を作成する方法が用意されている。
  - KillSwitch は data/kill.flag を書き込み ExecutionEngine に停止信号を送る仕組み（RiskMonitor などから評価される）。
- AI 呼び出し（OpenAI）:
  - レスポンスは JSON mode（response_format=json_object）で期待するため、レスポンスバリデーションやリトライロジックが組み込まれている。
  - API キー未設定時は ValueError を送出する箇所があるため、運用時は環境変数を確実に用意してください。
- プロセス優先度 / CPU affinity:
  - set_process_priority / set_cpu_affinity が用意されており、プラットフォーム差分を吸収するが権限不足時は警告でスキップされる。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数・設定管理
- run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト
- utils/
  - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- execution/
  - order_manager.py
  - reconciler.py
  - ...（broker_factory 等の実装）
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
  - streamlit_dashboard.py
- ai/
  - news_nlp.py                  — ニュースセンチメント取得（OpenAI）
  - regime_detector.py           — レジーム判定（MA200 + LLM）
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py

data/
- （運用で使う DB やフラグファイルを想定）
  - data/monitoring.db
  - data/kabusys.duckdb
  - data/paper_trading.db
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag

---

## よくある運用フロー（例）

1. 開発環境で duckdb に価格データをロード（外部 ETL 実装想定）
2. ExecutionEngine を paper_trading モードで実行・検証
3. MonitoringEngine を起動して system/trade/risk を継続監視
4. Streamlit でダッシュボードを確認
5. 本番運用時は KABUSYS_ENV=live、別途本番 Broker クライアントを設定して起動

---

## 追加情報 / 貢献

- 各モジュールには詳細な docstring と設計上の注記が埋め込まれています。実装の拡張・テストを行う際はそれらを参照してください。
- 外部 API（kabuステーション / J-Quants / OpenAI）統合部のテストはモック化が想定されています（テスト用の環境変数や関数差し替えポイントあり）。

---

この README はコードベースからの要点をまとめたものであり、実際の運用では環境依存の設定（API キー、DB の初期データ、Broker 設定など）を適切に準備してください。質問や追加のドキュメント化（例: 実行フロー図、設定ファイルテンプレート等）が必要であればお知らせください。