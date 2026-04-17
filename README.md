# KabuSys — 日本株自動売買システム

このリポジトリは、Japan-equity 自動売買（注文管理・監視・検証・リサーチ・AI 補助）を目的とした軽量なフレームワーク実装です。  
ここに含まれるコードは、発注エンジン（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築ロジック・リサーチ / ファクター計算・ニュース NLP（OpenAI）連携などの主要機能を含みます。

---

## 主な機能一覧

- Execution
  - 発注ワークフロー（OrderManager / ExecutionEngine）
  - ブローカー抽象化（モック/実ブローカー切替、paper_trading モード）
  - 再起動時のリコンシリエーション（Reconciler）
  - 注文履歴・ポジション管理（OrderRepository）

- Monitoring
  - システムヘルス（CPU/メモリ/ディスク/プロセス）監視（SystemMonitor）
  - 注文滞留・約定異常の検出（TradeMonitor）
  - ドローダウン・ポジション上限監視とアラート（RiskMonitor / KillSwitch）
  - LINE へのプッシュ通知（AlertManager）
  - 監視データの永続化（SQLite）
  - Streamlit ベースの監視ダッシュボード

- Portfolio & Risk
  - 候補選定 / ウェイト計算（等配分・スコア加重）
  - セクター集中制限、レジーム乗数
  - 株数決定（リスクベース／等配分）、単元丸め、投資上限調整

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB + prices_daily / raw_financials）
  - 将来リターン / IC（Information Coefficient）計算、統計サマリ

- AI（オプション）
  - ニュースのセンチメントスコアリング（OpenAI API）
  - 市場レジーム判定（MA200 とマクロニュースの LLM 補正）

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 必要条件（主な依存ライブラリ）

- Python 3.9+
- duckdb
- psutil
- requests
- openai (AI 機能を使う場合)
- streamlit (ダッシュボード利用時)
- sqlite3（標準ライブラリ）
- その他：パッケージの依存関係は pyproject.toml / requirements.txt を参照してください（本 README はコードから推測した要件を記載しています）。

例（インストール例）:
```bash
python -m pip install -r requirements.txt
# または個別に
python -m pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローンして移動
```bash
git clone <repo-url>
cd <repo-dir>
```

2. 依存パッケージをインストール
```bash
python -m pip install -r requirements.txt
# 開発環境として編集可能インストールする場合
python -m pip install -e .
```

3. 環境変数設定
- プロジェクトルートに `.env` / `.env.local` を置くことで自動ロードします（デフォルトで OS 環境 > .env.local > .env の順）。
- 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

推奨の `.env`（例）
```
KABUSYS_ENV=development         # development | paper_trading | live
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...             # AI 機能を使う場合に必須
LINE_CHANNEL_ACCESS_TOKEN=...  # アラート送信に必要（任意）
LINE_USER_ID=...               # アラート送信先（任意）
PAPER_FILL_MODE=instant        # paper_trading 用（instant|partial|never|reject）
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
```

4. データディレクトリ
- デフォルトの DB 等は `data/` 下に保存されます。必要に応じてディレクトリ作成と権限を確認してください。
```bash
mkdir -p data
```

---

## 使い方（主要スクリプト）

※ 実行パスはプロジェクトの Python パッケージ構成次第です。パッケージがインストールされていなければ、`PYTHONPATH=src` を付けて実行してください。

共通:
- パッケージとしてインストール済み: `python -m kabusys.<module>`
- ソース直下で実行: `PYTHONPATH=src python -m kabusys.<module>`

1. 監視ループ起動（Monitoring）
- スクリプト: src/kabusys/run_monitoring.py
- 説明: SystemMonitor をポーリングし監視ログを SQLite に永続化する。MONITOR_POLL_INTERVAL 環境変数で間隔（秒）を指定可能（デフォルト 60 秒）。
- 実行例:
```bash
# パッケージインストール済みの場合
python -m kabusys.run_monitoring

# ソース直下で
PYTHONPATH=src python -m kabusys.run_monitoring
```
- 停止: プロジェクトルートの `data/stop_requested.flag` を作成するとループが検知して終了します。

2. 実行エンジン起動（Execution）
- スクリプト: src/kabusys/run_execution.py
- 説明: ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い `data/paper_trading.db` を使用して本番 DB と完全分離します。起動時に `data/execution.pid` を作成します。停止は `data/stop_requested.flag` を作成すると検知して安全停止します。
- 実行例:
```bash
python -m kabusys.run_execution
# Paper trading モードで起動する例
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

3. Streamlit ダッシュボード（監視の可視化）
- スクリプト: src/kabusys/monitoring/streamlit_dashboard.py
- 起動方法:
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- DB が読み取り専用で開かれます（Uri + ?mode=ro）。

4. Paper Trading 検証レポート
- スクリプト: src/kabusys/tools/paper_verification_report.py
- 使い方:
```bash
# デフォルト DB (data/paper_trading.db) を使用
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB パスを直接指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```
- 出力: 稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）などの指標をコンソールに表示し PASS/FAIL を判定します。

5. AI 機能
- news_nlp.score_news / regime_detector.score_regime は OpenAI API キーが必要（環境変数 `OPENAI_API_KEY` または関数引数で指定）。
- 失敗時はフェイルセーフ（スコア 0 など）で継続する実装方針ですが、API キー未指定時は例外を投げます。

---

## 設定と環境変数（主要なもの）

- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須のプロパティ参照あり）
- KABU_API_PASSWORD: kabu ステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- PAPER_FILL_MODE: paper_trading での約定挙動（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 DB（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill.flag のパス（Settings を参照）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索して .env / .env.local を読み込みます。
- OS 環境変数は保護され、.env で上書きされない設定（.env.local は上書き可能）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings 管理（.env 自動ロード機能）
  - run_monitoring.py               — SystemMonitor ポーリングループ起動
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite テーブル初期化 & MonitoringDB 書き込み API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他ブローカー / engine / repository 関連)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py

（上記は主要ファイルの一覧です。実際のリポジトリにはさらに execution 用の broker_*、order_repository 等が含まれます。）

---

## 運用上の注意 / トラブルシュート

- DB ファイルが存在しない場合
  - run_monitoring / run_execution は必要なテーブルを自動で作成します（init_monitoring_db）。
  - Streamlit ダッシュボードは監視 DB が存在しない・開けないとエラーを表示します。

- OpenAI API
  - API キーが未設定のまま AI 機能（news_nlp / regime_detector）を呼ぶと例外が発生します。環境変数 `OPENAI_API_KEY` を設定してください。
  - レート制限や一時エラーは内部でリトライ処理がありますが、最終的に失敗すると該当日のスコアは取得されない場合があります。

- プロセス優先度設定
  - 起動スクリプトは最初にプロセス優先度を "high" にしようとします（psutil を使用）。権限不足だと警告が出ますが処理は継続します。

- 停止フラグ
  - `data/stop_requested.flag` を作成すると run_monitoring / run_execution が検知して安全に停止します。
  - Execution を強制停止したい場合は `KillSwitch` により `data/kill.flag` が書き込まれることがあり、これを監視して ExecutionEngine を停止します（kill.flag は起動時にクリアする設定も可能）。

---

## 開発者向けメモ

- 単体関数群（portfolio, research 等）は副作用のない純粋関数設計になっており、ユニットテストが書きやすくなっています。
- DuckDB を使ったファクター計算は SQL ベースで実装しており、prices_daily / raw_financials のスキーマに依存します。
- monitoring_db.init_monitoring_db は冪等で、既存 DB に対するマイグレーション処理（カラム追加）を含みます。

---

必要であれば、README に含める詳細な .env.example や systemd などのサービス化手順、Dockerfile / docker-compose 設定のサンプル、テスト実行方法を追加で作成します。どの情報が欲しいか教えてください。