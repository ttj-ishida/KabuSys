# KabuSys

日本株向けの自動売買システムのコードベース（抜粋）。本リポジトリはトレード実行・監視・ポートフォリオ構築・リサーチ・AI（ニュースNLP / レジーム判定）などのコンポーネントを含みます。

以下はこのコードベースの概要、機能、セットアップと起動方法、ディレクトリ構成の簡潔な README です。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムで、主に次の機能を提供します：

- 実際のブローカーまたはモックブローカーを用いた注文の作成・送信・同期（ExecutionEngine）
- システム稼働状況・注文の監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築ロジック（候補選定、重み付け、ポジションサイズ決定、セクター制限 等）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー）と特徴量解析（IC 等）
- ニュースを LLM に通して銘柄ごとのセンチメントスコアを生成（OpenAI 使用）
- 市場レジーム判定（MA とマクロニュースの LLM スコアの合成）
- 開発／検証用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）

設計上、DB は SQLite（監視・paper trading 用）および DuckDB（時系列/リサーチ向け）を使用します。環境変数 / .env による設定をサポートしています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - Broker クライアントの切り替え（本番 / paper_trading＝モック）
  - リコンシリエーション（再起動後の注文・ポジション同期）
  - リスク管理（Rate limit / マックスポジション / ドローダウン制御 等）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス生存・データ鮮度チェック）
  - TradeMonitor（滞留注文／約定異常価格検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（フラグファイルによる ExecutionEngine 停止）
  - AlertManager（LINE Push による通知）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio
  - 候補選定、等金額／スコア加重配分、リスクベースのポジションサイズ計算
  - セクターキャップ適用・レジーム乗数
- Research
  - DuckDB を使ったファクター計算（momentum/volatility/value）
  - 将来リターン計算、IC 計算、ファクター統計サマリ
- AI
  - news_nlp: raw_news を LLM（OpenAI）で評価して ai_scores テーブルに書き込み
  - regime_detector: MA200 とマクロニュース LLM を合成して market_regime を書き込み
- Tools
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）

---

## 必要な依存（代表例）

（プロジェクトに付属の requirements.txt がない場合の例）
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
# または requirements.txt があれば:
# pip install -r requirements.txt
```

---

## 環境設定（.env）

設定は環境変数またはプロジェクトルートに置かれた `.env` / `.env.local` を通じて行います。自動ロードはデフォルトで有効です（必要なら `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化）。

主な環境変数（抜粋）:

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
- PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject）

.env 例ファイル（プロジェクト側に `.env.example` を置く想定）。必須変数は Settings モジュール経由で検証されます（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD が設定されていないと例外になる箇所があります）。

---

## セットアップ手順（ローカル）

1. リポジトリをクローンし、作業環境を用意
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil requests openai streamlit
   ```

2. .env を作成
   - プロジェクトルートに `.env` を置き、必要な値を設定します（.env.example を参照）。
   - 自動ロードが不要なら `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. データディレクトリの作成（必要に応じて）
   ```bash
   mkdir -p data
   # DuckDB / SQLite ファイルは起動時に自動作成されます
   ```

---

## 使い方

以下は各主要スクリプト／エントリポイントの起動例です。

### 監視ループ（Monitoring）

- スクリプト: src/kabusys/run_monitoring.py
- 説明: SystemMonitor をポーリングし、監視データを監視用 SQLite に記録します。MONITOR_POLL_INTERVAL 環境変数で間隔（秒）を変更可能。Monitoring は環境にかかわらず本番 sqlite_path を使用します。

起動:
```bash
python -m kabusys.run_monitoring
# または MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

注意:
- 起動直後にプロセス優先度を "high" に試みます（psutil を使用）。権限により失敗することがありますが、ログに警告が出ます。
- PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）を参照します。

### 実行エンジン（Execution）

- スクリプト: src/kabusys/run_execution.py
- 説明: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 DB（data/paper_trading.db）に記録します。

起動（本番相当）:
```bash
KABUSYS_ENV=live python -m kabusys.run_execution
```

起動（Paper Trading / モック）:
```bash
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

### Streamlit ダッシュボード（監視可視化）

- スクリプト: src/kabusys/monitoring/streamlit_dashboard.py
- 起動:
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- 読み取り専用で SQLite を開きます（DB が存在しない場合はエラー表示）。

### Paper Trading 検証レポート

- スクリプト: src/kabusys/tools/paper_verification_report.py
- 使用例:
```bash
# デフォルト DB (data/paper_trading.db) を使う
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB 指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```
- 出力: 指定期間の稼働率、注文成功率、送信率、レイテンシ（P95 など）に基づく PASS/FAIL 判定を標準出力へ表示します。

### AI モジュール（プログラムから呼ぶ）

- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続と target_date を与えてニュースセンチメントを ai_scores テーブルに書き込みます。
  - api_key を省略すると環境変数 OPENAI_API_KEY が使われます。

- regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジームの判定を行い market_regime テーブルへ保存します。

注意: OpenAI API を使うため、OPENAI_API_KEY を設定してください。API の失敗は基本的にフェイルセーフ（スコア 0.0 等で継続）ですが、キー未設定は例外になります。

---

## 重要な挙動・運用メモ

- Settings（src/kabusys/config.py）はプロジェクトルートの `.env` / `.env.local` を自動ロードします。CWD に依存せず __file__ の親階層から .git / pyproject.toml を探してプロジェクトルートを決定します。
- Monitoring は監視用 SQLite（settings.sqlite_path）を必ず使用します（KABUSYS_ENV に依存しない）。
- ExecutionEngine の paper_trading 環境は monitoring DB と完全に分離するよう paper_sqlite_path を使用します。
- KillSwitch は flag ファイル（デフォルト data/kill.flag）を書き込むことで ExecutionEngine 停止を促します。KillSwitch のトリガーはドローダウンやポジション上限超過などです。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存テーブルに対してカラム追加（例: peak_value, latency_ms）を行う処理が含まれ、冪等です。
- Process priority / CPU affinity 設定を行うユーティリティ（src/kabusys/utils/process_priority.py）を提供します。OS による差異は吸収しますが権限不足で失敗することがあります。

---

## ディレクトリ構成（抜粋）

以下は主要ファイルを抜粋したツリーです（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                        -- 環境変数・設定管理
  - run_monitoring.py                -- SystemMonitor ポーリング起動スクリプト
  - run_execution.py                 -- ExecutionEngine 起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュース NLP（OpenAI）処理
    - regime_detector.py             -- 市場レジーム判定（MA + マクロ） 
  - monitoring/
    - __init__.py
    - monitoring_db.py               -- SQLite 永続化層（テーブル初期化・CRUD）
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
    - (その他: broker_factory, execution_engine, order_repository 等は本ツリーの一部)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - data/ (想定データディレクトリ)
    - kabusys.duckdb (デフォルト DU CKDB_PATH)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)

（注: リポジトリ全体のファイルはここに示したもの以外も存在する想定です）

---

## 開発・デバッグのヒント

- ローカルで Paper Trading を使う場合は `KABUSYS_ENV=paper_trading` を設定してください。実トレードに繋がらないようモックブローカー & 別 DB を使います。
- monitoring の挙動を単発で確認したい場合は MonitoringEngine をテスト用に組み合わせて `run_once()` を呼ぶユニットテストが作りやすい設計です。
- OpenAI 呼び出し部分はテスト用に関数を差し替えられるよう設計されています（ユニットテストではモック化を推奨）。
- データ鮮度チェックは DuckDB の prices_daily テーブルの最終日付を参照します。リサーチ・ファクターの計算も DuckDB 上のテーブルを前提にしています。

---

## ライセンス・注意事項

- 本 README はコードに基づく概要説明です。実運用に際しては API キー管理・資金管理・レート制御・法令遵守等の運用上の配慮が必要です。
- 実トレードでの使用は自己責任でお願いします。

---

必要であれば、README に含める環境変数のサンプル（.env.example）や systemd / supervisor 用のサービス定義、docker-compose 例、依存関係をまとめた requirements.txt のテンプレート等も作成します。どれを追加しますか？