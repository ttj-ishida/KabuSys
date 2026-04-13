# KabuSys — README

KabuSys は日本株の自動売買および運用リサーチ用ライブラリ/ツール群です。本リポジトリは取引エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、AI（ニュースセンチメント / レジーム判定）などを含みます。

主な設計方針
- 本番・ペーパー（検証）環境の分離（環境変数 KABUSYS_ENV）
- DuckDB を分析用途、SQLite を監視・注文ログに利用
- 外部 API 呼び出し（kabuステーション、J-Quants、OpenAI 等）は抽象化して安全に扱う
- 自動監視・アラート（LINE）・kill flag による安全停止機構
- ルックアヘッドバイアス対策（日時参照の扱いに注意）

---

## 機能一覧（ハイライト）

- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / paper_trading モードの切替（データベースを分離）
  - ブローカークライアント生成、OrderManager / RiskManager / Reconciler の組み立て
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常価格検知
  - RiskMonitor: ドローダウン・ポジション上限監視
  - MonitoringEngine: 各モニタのポーリングとアラート送信、kill switch 評価
  - Streamlit ダッシュボード（監視用）
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み計算、単元株丸め、セクター制限、レジーム乗数
- Research（リサーチ）
  - ファクター計算 (momentum / volatility / value)
  - 将来リターン計算、IC（スピアマン）・統計サマリ
- AI（ニュースNLP / レジーム判定）
  - OpenAI を用いたニュースの銘柄別センチメント算出（ai.news_nlp）
  - ETF + マクロニュースを用いた日次レジーム判定（ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）
  - 監視 DB を参照する Streamlit ダッシュボード

---

## セットアップ手順

前提:
- Python 3.9+（コードは typing | None 等を利用）
- SQLite は標準ライブラリ
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード使用時)

例: 仮想環境作成とインストール
```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

環境変数の設定
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境優先）。
- 自動読み込みを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。

主要な環境変数（代表例）
- KABUSYS_ENV: environment（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants 用トークン（必須とする機能あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須とする機能あり）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（例: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用

ファイル・ディレクトリの準備
```bash
mkdir -p data
# DuckDB/SQLite の初期化は run_monitoring/run_execution が自動で行います
```

---

## 使い方（主要コマンド例）

前提として、プロジェクトルート（pyproject.toml または .git がある場所）で実行することを推奨します。パッケージがインストール済であれば python -m kabusys.<module> の形式で実行できます。ソースツリー直下からは PYTHONPATH を通すか `python -m` を用いて実行してください。

1. 監視ループの起動
```bash
# デフォルトは monitoring.db を使用（Settings.sqlite_path）
python -m kabusys.run_monitoring
# ポーリング間隔を環境変数で上書き（秒）
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
- MONITOR_POLL_INTERVAL が 1 未満や不正な値の場合、デフォルト 60 秒が使われます。
- run_monitoring は Settings に依らず「本番の sqlite_path」を監視 DB として使います（設計上の注意）。

2. ExecutionEngine（発注エンジン）起動
```bash
# 本番モード（KABUSYS_ENV=live）
export KABUSYS_ENV=live
python -m kabusys.run_execution

# Paper Trading（検証）モード: MockBroker を使用し data/paper_trading.db に記録
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```
- paper_trading の場合、データベースが paper_trading.db に分離されます（本番 DB とは完全分離）。
- エンジン起動時に pid ファイルが作成され、監視側はこの pid を参照します。

3. Paper Trading 検証レポート（CSV ではなく標準出力）
```bash
# module 形式で実行
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# もしくは DB を直接指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

4. Streamlit 監視ダッシュボード
```bash
# 監視 DB を読み取り専用で開く例（起動方法はスクリプト内にも記載）
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

5. AI 機能（プログラムから呼ぶ）
- ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key)
- レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)
- これらは CLI ではなくライブラリ関数として提供されます。OpenAI API キー（OPENAI_API_KEY または引数）を必ず用意してください。

---

## 主要コンセプト / 注意点

- 環境分離
  - KABUSYS_ENV により挙動が変わります（development / paper_trading / live）。
  - paper_trading は MockBrokerClient を使い、紙上での挙動検証を行います。

- データベース
  - DuckDB: 時系列価格 / 財務データなどの分析用（デフォルト data/kabusys.duckdb）
  - SQLite（monitoring.db）: 監視ログ、trade_logs、positions、risk_logs、dashboard 等（デフォルト data/monitoring.db）
  - Paper Trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading）

- kill.flag による停止
  - KillSwitch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine 側は起動時に kill.flag のクリア設定（Settings.kill_flag_clear_on_start）を確認できます。

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を起点）を探索して `.env` / `.env.local` をロードします。
  - OS 環境変数は保護され、.env.local は上書き用に優先されます。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- ロギング / 優先度
  - 起動スクリプトは set_process_priority("high") を呼び出しプロセス優先度を試みます。プラットフォーム依存の失敗は警告ログに留めます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                        — 環境変数 / 設定読み込みロジック
- run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
- run_execution.py                 — ExecutionEngine 起動スクリプト

- ai/
  - news_nlp.py                     — ニュースセンチメント（OpenAI）
  - regime_detector.py              — レジーム判定（ETF MA + LLM）
  - __init__.py

- monitoring/
  - monitoring_db.py                — SQLite スキーマ / 永続化 API
  - system_monitor.py               — システム状態・データ鮮度監視
  - trade_monitor.py                — 注文滞留・約定異常監視
  - risk_monitor.py                 — ドローダウン・ポジション上限監視
  - kill_switch.py                  — kill.flag ロジック
  - alert_manager.py                — LINE 通知ラッパ
  - monitoring_engine.py            — 各 Monitor の統合ループ
  - streamlit_dashboard.py          — Streamlit ダッシュボード

- execution/
  - order_manager.py
  - order_repository.py
  - execution_engine.py
  - reconciler.py
  - broker_factory.py
  - ...（注文 / ブローカー関連）

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- tools/
  - paper_verification_report.py
  - __init__.py

- utils/
  - process_priority.py
  - __init__.py

data/
- (default DB ファイルや pid / flag を格納)
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - kill.flag

---

## トラブルシューティング（よくある項目）

- DB が見つからない / 読み込み不可
  - monitoring 用 Streamlit は readonly uri を用いて開きます。起動前に monitoring DB が作成されているか、または MonitoringEngine を起動して自動作成してください。

- OpenAI API 関連
  - OPENAI_API_KEY が未設定だと ai.* の呼び出しは ValueError を送出します。テストではモック化してください。
  - レート制限や一時エラーはリトライ実装がありますが、環境・鍵の制限に注意してください。

- psutil 権限エラー
  - set_process_priority / set_cpu_affinity の実行は権限不足で失敗することがあります。失敗時は警告ログが出力され、処理は継続します。

---

必要に応じて README の補足（インストール方法、CI、デプロイ手順、より詳細な使用例や API ドキュメント）を追加できます。特定の部分（例: ExecutionEngine の設定、OrderRepository スキーマ、外部ブローカー実装方法）について詳述が必要でしたらその点を指定してください。