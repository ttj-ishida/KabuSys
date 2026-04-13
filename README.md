# KabuSys

KabuSys は日本株向けの自動売買・研究プラットフォーム（プロトタイプ）です。価格データの集計・ファクター計算、ポートフォリオ構築、注文発行・実行、実行監視、ニュースの NLP によるセンチメント評価などの機能を備えています。

この README はリポジトリ内の主要コンポーネント（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI モジュール、ユーティリティ、ツール）の概要、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## 主要な特徴（機能一覧）

- 実行（Execution）
  - ExecutionEngine による注文発行・状態管理（OrderManager、OrderRepository、RiskManager、Reconciler 等）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を用い、本番 DB と分離して `data/paper_trading.db` を使用

- 監視（Monitoring）
  - SystemMonitor: プロセス生存、CPU/メモリ/ディスク使用率、データ鮮度の監視
  - TradeMonitor: 注文滞留（stale orders）、約定価格の異常検出
  - RiskMonitor: ドローダウン、ポジション上限の監視とアラート
  - KillSwitch: 条件を満たした場合にフラグファイルを書き込み、ExecutionEngine 停止をトリガー
  - AlertManager: LINE Messaging API 経由で通知（クールダウン管理あり）
  - Streamlit ダッシュボード（read-only）で監視情報の可視化

- ポートフォリオ構築（Portfolio）
  - 銘柄の候補選定、等重・スコア加重の配分、リスク考慮の調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（単元丸め、リスクベース配分、aggregate cap）

- リサーチ（Research）
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターンの計算、IC（Information Coefficient）や統計サマリ等のユーティリティ
  - DuckDB を使った高速なデータ処理

- AI（OpenAI）連携
  - news_nlp: raw_news を LLM（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ保存
  - regime_detector: ETF の MA200 乖離とマクロニュースの LLM 評価を組み合わせて市場レジーム（bull/neutral/bear）を判定・永続化
  - API 呼び出しはリトライやフェイルセーフを備えています

- ユーティリティ
  - process_priority: OS に依存しないプロセス優先度 / CPU affinity 設定
  - 設定管理: `.env` 自動ロード（プロジェクトルート基準）、必須環境変数のチェック

- ツール
  - paper_verification_report: Paper Trading の検証レポートを生成（稼働率、注文成功率、レイテンシ等）

---

## 前提条件

- Python 3.10 以降（型ヒントに `X | Y` を利用）
- SQLite（標準ライブラリに含まれます）
- 推奨依存パッケージ（最低限）:
  - duckdb
  - openai
  - psutil
  - requests
  - streamlit（ダッシュボード利用時）

requirements.txt がない場合は手動でインストールしてください。例:

pip install duckdb openai psutil requests streamlit

（プロジェクトに requirements.txt を用意している場合はそれを使ってください）

---

## セットアップ手順

1. リポジトリをクローン / 展開する

2. 仮想環境を作成し有効化（推奨）

python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

pip install -r requirements.txt  # 存在する場合
# または最低限:
pip install duckdb openai psutil requests streamlit

4. 環境変数を設定
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（CWD ではなくソース配置を基準にプロジェクトルートを検出）。
- 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（重要なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合は必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（AlertManager のプッシュ用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の行為設定: instant | partial | never | reject）
- PID_FILE_PATH（デフォルト: data/execution.pid）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔を秒で上書き、デフォルト 60）

例 .env（最小）

JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

5. データディレクトリ作成（必要に応じて）

mkdir -p data

---

## 実行方法（使い方）

ここでは主要なエントリポイントの起動方法を示します。

- 実行エンジン（ExecutionEngine）を起動

python -m kabusys.run_execution

備考:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して `PAPER_TRADING_SQLITE_PATH`（既定: data/paper_trading.db）に書き込みます。本番 DB と分離されます。
- ExecutionEngine は起動時にプロセス優先度を `high` にし、PID ファイル（Settings.pid_file_path）を使用します。

- 監視ループ（SystemMonitor の単体起動）

python -m kabusys.run_monitoring

オプション:
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に注意してください（監視ログは本番パスへ記録されます）。

- Streamlit ダッシュボード（監視情報の可視化）
（read-only で sqlite DB を参照）

streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成

python -m kabusys.tools.paper_verification_report
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを明示する場合:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI モジュールの利用（プログラム的に）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key=...)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=...)

（これらは DuckDB 接続を受け取り、データテーブルを参照して結果をテーブルへ永続化します。OPENAI_API_KEY が必要です。）

---

## 運用時の重要ポイント / 注意事項

- プロセス優先度:
  - run_execution / run_monitoring の開始時にプロセス優先度を high に設定します（権限不足で失敗しても警告のみ）。
- PID / kill.flag:
  - ExecutionEngine と Monitor は PID ファイルや kill.flag を参照します。PID ファイルが stale（プロセスが存在しない）場合、Monitor はファイルを削除してイベントをログに残します。
  - KillSwitch は条件発生時に kill.flag を書き、ExecutionEngine 側でそれを検知して停止する設計です。
- Paper Trading モード:
  - 本番 DB と分離して検証可能です。PAPER_FILL_MODE によりモック約定の挙動を制御可能です。
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml の存在箇所）を基準に .env/.env.local を自動ロードします。OS 環境変数は保護されます。
- データ鮮度:
  - SystemMonitor は DuckDB の prices_daily を参照してデータ鮮度をチェックします（デフォルト許容 ≤ 3 日差）。
- OpenAI API:
  - レート制限・ネットワーク断・5xx に対して指数バックオフでリトライしますが、失敗時はフォールバック値（例: macro_sentiment=0.0）で継続するように設計されています。

---

## ディレクトリ構成（抜粋）

リポジトリの主要なファイル/モジュール構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数/設定管理（.env 自動ロード、Settings クラス）
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading 検証レポート生成スクリプト
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py             — 市場レジーム判定（MA200 + マクロ NLP）
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite ベースの監視ログ永続層
    - system_monitor.py              — システム状態・データ鮮度の監視
    - trade_monitor.py               — 注文滞留・約定異常の監視
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — kill.flag 書き込みロジック
    - alert_manager.py               — LINE Push 通知
    - monitoring_engine.py           — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py         — Streamlit ダッシュボード（read-only）
  - execution/
    - order_manager.py               — 注文マネジメント
    - reconciler.py                  — 起動時の自動復旧・リコンシリエーション
    - (その他: broker_factory, order_repository, order_record, execution_engine 等)
  - portfolio/
    - __init__.py
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 株数決定・単元丸め
    - risk_adjustment.py             — セクター制限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum/volatility/value）
    - feature_exploration.py         — 将来リターン, IC, 統計サマリ
  - data/
    - pipeline.py (参照されるモジュール) — DuckDB からの最終価格取得等
  - utils/
    - __init__.py
    - process_priority.py            — プラットフォーム非依存の優先度/affinity 設定

（上記はリポジトリ内の主要ファイルを抜粋しています。詳細はソースを参照してください）

---

## よくある操作例（サンプル）

- 監視をデフォルト設定で起動（60秒間隔）:

MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Execution を Paper Trading モードで起動（Mock ブローカー使用）:

export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution

- Paper Trading 検証レポート（過去 10 日分）:

python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード（監視 DB を参照）:

streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 開発・拡張メモ

- DuckDB をデータ分析基盤として利用しているため、prices_daily / raw_financials / raw_news 等のスキーマに依存します。ローカル開発では DuckDB に必要なテーブルをロードしておくこと。
- AI モジュールは OpenAI API を利用するため、API キーの管理・コスト・レート制限に注意してください。
- 実運用では PID / kill.flag の扱い、LINE 通知の権限・運用、DB のバックアップ方針等を明確にしてください。

---

以上がこのコードベースの概要・セットアップ・使い方・ディレクトリ構成の説明です。README に補足したい項目（例: 依存関係の正確なバージョン、CI / テスト実行方法、運用 runbook のテンプレート 等）があれば指示ください。