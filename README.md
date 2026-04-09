# KabuSys

日本株の自動売買 / 研究 / 監視を目的としたモジュール群のコレクションです。  
（本リポジトリはライブラリ的なコンポーネント群を含み、実際の運用ではブローカー クライアントや外部設定を組み合わせて利用します。）

主な設計方針：
- 各コンポーネントはできるだけ副作用を減らし、純粋関数や DB 接続を注入する形で実装。
- ルックアヘッドバイアス対策やフェイルセーフ（API失敗時のフォールバック）を考慮。
- DuckDB / SQLite を利用したローカル DB ベースのデータ処理・永続化。
- OpenAI（gpt-4o-mini 等）を利用したニュース NLP / レジーム判定機能を提供（API キー任意）。

---

## 目次
- プロジェクト概要
- 機能一覧
- 必要条件・依存関係
- セットアップ手順
- 使い方（主要 API と実行例）
- .env / 環境変数について
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株の量的リサーチ、ポートフォリオ構築、発注エンジン、監視・アラート、AI ベースのニュースセンチメント解析などを包含するコンポーネント群です。個々のモジュールは単独で使用できるように設計されており、実運用ではブローカー実装（Protocol 準拠）や外部サービス（LINE / OpenAI）を接続して利用します。

---

## 機能一覧
- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート基準）
  - settings オブジェクトによる型付きアクセス（例: settings.duckdb_path）
- ポートフォリオ構築（純粋関数）
  - 候補選定、等金額・スコア加重の重み計算
  - セクター集中制限、レジーム乗数適用
  - 株数（単元）決定、リスクベース配分と資金スケーリング
- リサーチ / ファクター計算
  - モメンタム（1M/3M/6M、MA200乖離）
  - ボラティリティ（20日 ATR）、流動性指標
  - バリュー（PER、ROE）計算
  - 将来リターン計算、IC（Spearman）や統計サマリ
- AI（OpenAI）連携
  - ニュースのセンチメント解析（銘柄別 ai_score 書き込み）
  - マクロニュース + ETF MA200 で市場レジーム判定（bull/neutral/bear）
  - 再試行・JSON バリデーション・スコアクリッピング等のフォールバック処理
- 実行・発注関連
  - OrderManager / ExecutionEngine：信号を受けて発注、状態遷移管理、再同期間機能
  - Reconciler：起動時の注文・ポジション照合
- 監視・アラート
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE push）
  - Streamlit ベースの簡易ダッシュボード

---

## 必要条件・依存関係
- Python >= 3.10
- 主な Python パッケージ（例）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (ダッシュボード用)
- 標準ライブラリ: sqlite3, logging, datetime, pathlib など

インストール例（適宜仮想環境を推奨）:
```
pip install duckdb openai requests psutil streamlit
```
または requirements.txt を用意している場合は:
```
pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. Python 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール（上記参照）
4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動的に読み込まれます（デフォルトで有効）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
5. 監視 DB 初期化（MonitoringDB）
   - SQLite コネクションを作成して `init_monitoring_db(conn)` を呼び出すことで必要テーブルを作成します。
   - 例（Python）:
     ```py
     import sqlite3
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()
     ```

---

## 使い方（主要 API と実行例）

- 設定の参照
  ```py
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.line_channel_access_token)
  ```

- ポートフォリオ構築（候補選定と重み）
  ```py
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights
  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  ```

- 株数算出（position sizing）
  ```py
  from kabusys.portfolio import calc_position_sizes
  sizes = calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices)
  ```

- ファクター計算（DuckDB 接続を渡す）
  ```py
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

- ニュース NLP スコアリング（OpenAI API キー必要）
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- レジーム判定
  ```py
  from kabusys.ai.regime_detector import score_regime
  count = score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監視ダッシュボード（Streamlit）
  起動コマンド（簡易）:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  引数 `--db` で SQLite DB パスを指定（デフォルト data/monitoring.db）。

- ExecutionEngine（実行エンジン）
  - ExecutionEngine は BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続などを注入して使用します。実環境では Broker クライアント実装やシグナル生成 / portfolio_targets テーブルの准备が必要です。
  - 実行フロー:
    1. 起動時に Reconciler（任意）で注文/ポジションの同期
    2. PID ファイルの書き込み（settings.pid_file_path）
    3. 指定時刻（デフォルト 8:50）にシグナル読み込み→発注（Gate チェックあり）
    4. WebSocket push を適宜ドレイン（9:10〜15:30）
    5. セッション終了時に PID 削除

---

## .env / 環境変数について
- 自動ロード動作:
  - 起動時にプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を探索し、`$ROOT/.env` をまず読み込み（既存 OS 環境変数を上書きしない）、その後 `$ROOT/.env.local` を上書きモードで読み込みます。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
  - 読み込み優先順位: OS 環境 > .env.local > .env
- 主な環境変数（代表例）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - OPENAI_API_KEY (AI 機能を使う場合)
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (AlertManager / LINE 通知)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_FILL_MODE (instant|partial|never|reject)
  - PAPER_TRADING_SQLITE_PATH
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (1 で起動時に kill.flag を自動クリア)
  - LOG_LEVEL, KABUSYS_ENV（development|paper_trading|live）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視閾値）

.gitignore や .env.example を参考に、秘密情報（API キーやパスワード）は .env.local / CI シークレット等で管理してください。

---

## 注意点 / 実運用上の注意
- OpenAI API を用いる機能は API キーの料金やレートリミットに注意。モジュール内にリトライ・バックオフ実装があるものの、商用利用前に負荷試験・コスト評価を行ってください。
- ExecutionEngine を本番で動かす場合は BrokerAPIProtocol 準拠の安定したブローカークライアント実装が必要です（本リポジトリは Protocol とロジックを提供）。
- kill.flag / PID ファイル等を用いた停止制御があるため、ファイルパスの権限や永続ボリュームを適切に設定してください。
- DuckDB / SQLite のデータ整合性に注意。バックアップ・定期メンテナンスを推奨します。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP スコアリング
    - regime_detector.py            — 市場レジーム判定
  - portfolio/
    - __init__.py
    - portfolio_builder.py          — 候補選定 / 重み計算
    - position_sizing.py            — 株数決定 / スケーリング
    - risk_adjustment.py            — セクターキャップ / レジーム乗数
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Volatility / Value
    - feature_exploration.py        — 将来リターン / IC / 統計
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite スキーマ & MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py                 — Broker API protocol / 型 / 例外
    - order_manager.py
    - order_repository.py (参照あり)
    - order_record.py (参照あり)
    - reconciler.py
    - execution_engine.py
    - risk_manager.py (参照あり)
  - research, data, その他の補助モジュール（stats, pipeline 等） — 一部モジュールから参照

---

## 貢献 / 開発
- 新しい Broker 実装は `BrokerAPIProtocol` を満たす形で追加してください。
- AI 関連の呼び出しは `_call_openai_api` をテストでモックする設計になっています（ユニットテスト容易化）。
- .env の取り扱いは config._parse_env_line 等で細かくパースされます。特殊な引用やコメントルールに従ってください。

---

README の情報はコードベースの主要機能に基づいて作成しています。必要であれば、利用シナリオ別の具体的なセットアップ手順（例: ExecutionEngine の起動スクリプト、Broker 実装サンプル、DuckDB の初期データ投入スクリプト）を追加します。どの部分を優先して追加しましょうか？