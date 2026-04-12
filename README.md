# KabuSys

日本株向け自動売買システム「KabuSys」のコードベース（抜粋）用 README。  
この README はリポジトリ内の主な機能・起動方法・設定・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。主な責務は以下の通りです。

- 注文作成・送信・状態管理（Execution）
- 監視（Monitoring）：プロセス監視、データ鮮度、注文滞留・約定異常検出、リスク（ドローダウン・ポジション上限）監視、Kill Switch
- ポートフォリオ構築（候補選定・配分・リスク補正・株数決定）
- リサーチ（ファクター計算、特徴量探索、IC計算）
- AI 補助（ニュースのセンチメント評価、レジーム判定。OpenAI API を利用）
- ユーティリティ（プロセス優先度設定、Streamlit ダッシュボード、紙取引検証レポート作成など）

設計方針として「本番 DB とテスト（paper_trading） DB の隔離」「外部 API 呼出しは明示的に扱う」「ルックアヘッドバイアスの回避」などが採用されています。

---

## 主な機能一覧

- Execution
  - OrderManager, Reconciler, RiskManager（リスク制御）などによる安全な注文処理フロー
  - paper_trading モードで MockBroker を使い、本番 DB と完全分離して検証可能
- Monitoring
  - SystemMonitor: CPU/メモリ/Disk、プロセス存在、データ鮮度監視
  - TradeMonitor: 滞留注文検出、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション数制限監視（ダッシュボード更新、risk_logs 書込み）
  - KillSwitch: フラグファイルで ExecutionEngine 停止要求を出す
  - AlertManager: LINE に通知（任意設定）
  - Streamlit ベースの監視ダッシュボード
- Portfolio
  - 候補抽出、等配分 / スコア配分、リスク調整（セクターキャップ、レジーム乗数）、株数計算（lot 単位、aggregate cap）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - forward returns、IC（Spearman）計算、統計サマリ
- AI
  - news_nlp: raw_news を OpenAI に送って銘柄別センチメントを ai_scores に書き込み
  - regime_detector: ma200 とマクロニュースの LLM センチメントを合成して日次レジーム判定を行い market_regime に書き込み
- ツール
  - paper_verification_report: Paper Trading の検証レポート出力（稼働率・注文成功率・レイテンシ等）
- 設定
  - Settings クラスで環境変数／.env 読み込みを統一的に管理（自動読み込みを搭載）

---

## 要件（想定）

リポジトリに requirements.txt は含まれていませんが、実行に必要な代表的パッケージは次の通りです。

- Python 3.9+（型アノテーションと一部モダン API を使用）
- duckdb
- psutil
- requests
- openai（OpenAI SDK）
- streamlit（ダッシュボードを利用する場合）

インストール例:
```bash
python -m pip install duckdb psutil requests openai streamlit
```

（実際のプロジェクトでは requirements.txt / poetry / pipenv 等で固定してください）

---

## 環境変数（主要）

以下はコード中で参照される主要な環境変数です。必須項目は Settings._require() により未設定で例外が出ます。

必須（実稼働時）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

OpenAI / LINE 等（任意）:
- OPENAI_API_KEY (AI 機能を使う場合必須)
- LINE_CHANNEL_ACCESS_TOKEN (AlertManager 用)
- LINE_USER_ID

システム設定:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、Execution は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒間隔（デフォルト 60）
- PAPER_FILL_MODE: paper_trading でのモック約定モード（instant|partial|never|reject）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、本番: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / など

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` と `.env.local` を自動で読み込みます（OS 環境変数を上書きしない / .env.local は上書き可）。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして Python 仮想環境を作成
```bash
git clone <repo>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil requests openai streamlit
```

2. 環境変数を設定（.env を作る例）
```
# .env (例)
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

3. データディレクトリを作る
```bash
mkdir -p data
```

4. （必要に応じて）DuckDB や SQLite のテーブルは実行時に自動で作成・マイグレーションされます。monitoring 用のテーブルは init_monitoring_db() により作成されます。

---

## 実行方法（主要なスクリプト）

- 監視ループ（SystemMonitor 単体でポーリング）
  - デフォルトは本番 sqlite_path（KABUSYS_ENV にかかわらず production 相当の monitoring DB を使用）
```bash
python -m kabusys.run_monitoring
# ポーリング間隔を変える例
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- 実行エンジン（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）
```bash
# 本番・開発モード
python -m kabusys.run_execution

# Paper trading モード（専用 DB に記録）
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

- Streamlit 監視ダッシュボード（読み取り専用で SQLite を開く）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポート（コマンドライン）
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示する場合
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- AI 機能（プログラムから呼び出す例）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - 両関数は api_key 引数または環境変数 OPENAI_API_KEY を参照します。

---

## 主要な設定挙動（注意点）

- Monitoring は常に Settings.sqlite_path（本番用）を使用します。つまり監視ログは KABUSYS_ENV に依らず本番監視 DB に書き込まれます（run_monitoring の実装上の仕様）。
- Execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。
- .env 読み込みは自動で行われますが、テスト等で自動読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE の有効値は "instant" / "partial" / "never" / "reject" です。無効値を設定すると例外になります。
- MONITOR_POLL_INTERVAL は run_monitoring のポーリング間隔。0 以下や不正値はデフォルト（60秒）にフォールバックします。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — Settings クラス（環境変数・.env 読み込み）
- execution/
  - order_manager.py — 注文作成・送信の外向き API（Order Manager）
  - reconciler.py — 起動時の注文・ポジション再突合（リコンシリエーション）
  - (※ 他に broker_factory, execution_engine, order_repository, risk_manager 等が想定されます)
- monitoring/
  - monitoring_db.py — SQLite テーブル作成・永続化 API（MonitoringDB）
  - system_monitor.py — CPU/メモリ/disk/process/data freshness 監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン／ポジション上限監視
  - kill_switch.py — kill.flag による ExecutionEngine 停止要求
  - alert_manager.py — LINE 通知送信
  - monitoring_engine.py — 各モニタの束ね（run / run_once）
  - streamlit_dashboard.py — Streamlit 監視ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算（等配分・スコア配分）
  - position_sizing.py — 株数決定・上限・aggregate cap
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value 等のファクター算出（DuckDB 経由）
  - feature_exploration.py — forward returns, IC, 統計サマリ
- ai/
  - news_nlp.py — ニュースを LLM に投げて銘柄別スコアを ai_scores テーブルへ書込む
  - regime_detector.py — MA200 とマクロニュースを用いて market regime を算出・書込
- tools/
  - paper_verification_report.py — Paper trading の検証レポート生成
- utils/
  - process_priority.py — プラットフォーム差分を吸収したプロセス優先度 / CPU affinity 設定

---

## 運用メモ / 実務上の注意

- 本システムは取引に関わるため、実稼働時は設定・権限・API キー管理・DB のバックアップ・監査ログに十分注意してください。
- OpenAI やブローカー API の呼び出しはコストとレート制限があるため、本番環境では適切に制御してください（リトライ・バックオフ・部分失敗時のフェイルセーフ等を実装済み）。
- streamlit ダッシュボードは DB を読み取り専用で開く仕組み（URI に mode=ro を付加）ですが、DB ファイルのロック状態や接続制限に留意してください。
- paper_trading モードを使うときは PAPER_TRADING_SQLITE_PATH により本番 DB と完全に分離していることを確認してください。

---

この README はコードベースの概要を把握するためのドキュメントです。さらに詳細な設計仕様（StrategyModel.md / PortfolioConstruction.md 等）や実際の Broker 接続実装、requirements 単体の lock ファイルは別途参照してください。質問や追加で欲しいドキュメント（API リファレンス、運用手順、デプロイ手順など）があれば教えてください。