# KabuSys

日本株自動売買システム（部分実装サンプル）。  
このリポジトリは取引実行、監視、ポートフォリオ構築、ファクター計算、ニュースNLP/レジーム判定などのコンポーネント群を含みます。各コンポーネントはできるだけ副作用を抑えた純粋関数／小さなクラス群として設計されており、SQLite / DuckDB をデータ層に用います。

---

目次
- プロジェクト概要
- 主な機能
- 必要環境 / 依存関係
- セットアップ手順
- 環境変数（主なもの）
- 使い方（起動例）
- 開発や運用上の注意点
- ディレクトリ構成（主要ファイル説明）

---

## プロジェクト概要

KabuSys は日本株を対象にした自動売買システムのコンポーネント群です。主要な役割は以下の通りです。

- ExecutionEngine: ブローカーとやり取りして注文を発行・管理する実行層
- MonitoringEngine: システム稼働状態、注文の滞留・約定異常、ドローダウン等を監視する
- Portfolio construction: 候補選定、重み付け、株数決定（単元丸め含む）
- Research: DuckDB 上の時系列データからファクター計算、特徴量解析を行う
- AI utilities: ニュースをLLMでスコアリングして ai_scores に保存、マクロニュースとETF MAを使ったレジーム判定
- Tools: Paper Trading 検証レポート生成など

設計上のポイント:
- DB は SQLite (監視等) と DuckDB (時系列/分析) を併用
- 環境変数 / .env ファイルから設定を読み込む（Settings クラス）
- Paper trading 環境を本番 DB から分離して運用可能
- OpenAI（gpt-4o-mini）を使った NLP 部分は API キー必須で、失敗時のフォールバックやリトライを考慮

---

## 主な機能一覧

- 実行:
  - ExecutionEngine 起動（run_execution.py）
  - Broker クライアント切り替え（本番 / mock for paper_trading）
  - 起動時のリコンシリエーション（Reconciler）
- 監視:
  - SystemMonitor（CPU/Mem/Disk/プロセス・データ鮮度）
  - TradeMonitor（滞留注文 / 約定異常）
  - RiskMonitor（ドローダウン / ポジション上限）
  - KillSwitch（条件に応じて flag ファイルを作成して ExecutionEngine を停止）
  - AlertManager（LINE へのプッシュ通知）
  - Streamlit ダッシュボード（監視情報可視化）
- ポートフォリオ:
  - 候補選定、等分・スコア重み配分
  - セクターキャップ適用、レジーム乗数
  - 株数算出（単元株・コストバッファ・aggregate cap）
- リサーチ:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン、IC（スピアマン）計算、統計サマリ
- AI:
  - ニュースの銘柄別センチメントスコア化（OpenAI）
  - マクロニュース + ETF MA による市場レジーム判定
- ツール:
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## 必要環境 / 依存関係

推奨 Python バージョン: 3.10+（typing の | 演算子等を使用）

主な Python パッケージ（最低限）:
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使う場合)

pip で個別にインストールするか、requirements.txt を用意している場合はそれを使ってください（本リポジトリには requirements.txt の提供がないため手動でのインストール例を示します）:

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

SQLite は標準ライブラリで利用可能です。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. プロジェクトルートに .env または .env.local を作成して必要な環境変数を設定
   - Settings モジュールは自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（ただし OS 環境変数が優先）。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
5. data ディレクトリ等、DB を置くディレクトリを作成
   - デフォルトのパス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db

---

## 主な環境変数（代表的なもの）

- KABUSYS_ENV: 起動環境。`development` / `paper_trading` / `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な箇所あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須な箇所あり）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE 通知）用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill.flag のパス
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒）。run_monitoring で参照（デフォルト 60）

注意:
- Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計です（監視は本番 DB を見る想定）。
- Paper trading 実行時は ExecutionEngine が paper_sqlite_path を使って DB を分離します。

---

## 使い方（起動例）

1. ExecutionEngine を起動（本番/デバッグ）
```
# 通常（KABUSYS_ENV によって broker が切り替わる）
python -m kabusys.run_execution

# Paper trading 実行（Mock ブローカーを使い、data/paper_trading.db を使用）
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

2. Monitoring（SystemMonitor のポーリング）を起動
```
# デフォルト間隔（60秒）
python -m kabusys.run_monitoring

# ポーリング間隔を環境変数で上書き（例: 30秒）
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

3. Streamlit ダッシュボード（監視結果の可視化）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

4. Paper Trading 検証レポート生成
```
# DB パスは --db または PAPER_TRADING_SQLITE_PATH で指定可能
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# もしくは
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

5. AI 関連（ニューススコアリング / レジーム判定）
- OpenAI API キーが必要。プログラム的には kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して使用します。CLI 用の起動スクリプトは含まれていませんが、上記関数は DuckDB 接続と日付、APIキーを受け取ります。

---

## 開発・運用上の注意点

- Settings は起動時に `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。テスト時などで自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Monitoring の起動スクリプトは監視用 DB へ接続する際に production sqlite_path を使います。Paper trading DB とは分離されています。
- KillSwitch は `kill.flag` ファイル（デフォルト data/kill.flag）を書いて ExecutionEngine 停止を要求します。ExecutionEngine 側はこのファイルの存在をチェックしてシャットダウン処理を行う想定です。起動時にフラグをクリアする設定もあります（Settings.kill_flag_clear_on_start）。
- OpenAI 周りの呼び出しはリトライやフォールバックを実装していますが、APIキー未設定では例外が投げられます。運用時は環境変数に `OPENAI_API_KEY` を設定してください。
- process priority / cpu affinity 設定は utils/process_priority.py が跨プラットフォームで吸収しますが、権限不足で失敗することがあり、その場合はログに警告を出してスキップします。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブル作成・簡単なカラム追加マイグレーションを行います。

---

## 主なファイル・ディレクトリ構成

（src/kabusys 以下を中心に抜粋）

- src/kabusys/__init__.py
  - パッケージ初期化。バージョン情報等。

- src/kabusys/config.py
  - Settings クラス: 環境変数・.env の読み込みと検証ロジック

- 起動スクリプト
  - src/kabusys/run_execution.py — ExecutionEngine 起動
  - src/kabusys/run_monitoring.py — SystemMonitor 単体ポーリング起動

- execution/
  - execution/order_manager.py — 注文作成・送信を管理する OrderManager
  - execution/reconciler.py — 起動時のリコンシリエーション（ブローカー照合）
  - （その他: broker_factory, execution_engine, order_repository など：注文管理、永続化、リスク管理を含む）

- monitoring/
  - monitoring/monitoring_db.py — SQLite を使った監視ログ永続化層（MonitoringDB）
  - monitoring/system_monitor.py — CPU/Mem/Disk・プロセス・データ鮮度監視
  - monitoring/trade_monitor.py — 注文滞留 / 約定異常検出
  - monitoring/risk_monitor.py — ドローダウン / ポジション上限監視
  - monitoring/kill_switch.py — kill.flag の生成と評価
  - monitoring/alert_manager.py — LINE へプッシュ通知
  - monitoring/monitoring_engine.py — 各 Monitor を束ねてポーリング（テスト用 run_once あり）
  - monitoring/streamlit_dashboard.py — Streamlit による可視化

- portfolio/
  - portfolio/portfolio_builder.py — 候補選定、等分・スコア重み付け
  - portfolio/position_sizing.py — 株数決定（単元丸め・aggregate cap 等）
  - portfolio/risk_adjustment.py — セクターキャップ、レジーム乗数

- research/
  - research/factor_research.py — momentum / volatility / value ファクター計算（DuckDB）
  - research/feature_exploration.py — 将来リターン、IC、統計サマリ

- ai/
  - ai/news_nlp.py — raw_news を LLM で銘柄別にスコア化して ai_scores に書き込む
  - ai/regime_detector.py — ETF MA とマクロニュースでレジーム判定

- tools/
  - tools/paper_verification_report.py — Paper trading DB からの検証レポート生成

- utils/
  - utils/process_priority.py — プロセス優先度・CPU affinity のクロスプラットフォームユーティリティ

- data/
  - デフォルトで利用されるデータディレクトリ（DBファイル、pid/flag 等を置く）

---

この README はコードベースから主要な機能と使い方を要約したものです。実際の運用では .env の適切な管理、Credentials（OpenAI / ブローカー等）の安全な取り扱い、十分なテスト・モニタリングを行ってください。質問や追加で記載したい項目があれば教えてください。