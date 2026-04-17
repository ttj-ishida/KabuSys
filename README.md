# KabuSys

日本株向け自動売買フレームワーク（モジュール群）のリポジトリ用 README。  
以下はリポジトリ内ソースコード（src/kabusys 以下）に基づいた説明です。

注意: 実際の運用・本番発注を行う前に、.env の設定・validate_config による検証を必ず行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な責務は以下のとおりです。

- ExecutionEngine による発注ロジック（本番 / ペーパートレード対応）
- Monitoring 系（システム稼働・注文監視・リスク監視）と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限など）
- リサーチ機能（ファクター計算、特徴量探索、将来リターン・IC 計算）
- AI 補助（ニュースの NLP によるセンチメントスコア、レジーム判定）
- 運用支援ツール（.env ウィザード・設定検証・Paper Trading 検証レポート生成）

設計方針の一例：
- DB（DuckDB / SQLite）や外部 API 呼び出しは用途に応じ分離（Paper Trading は専用 SQLite を使用）
- 時間参照はルックアヘッドバイアスを避ける設計（date.today()/datetime.today() 依存を排除）
- フェイルセーフ（API 失敗時のフォールバック）や冪等性を意識

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注エンジン）
  - BrokerClientFactory（本番 / モックの切替）
  - OrderRepository / OrderManager / RiskManager / Reconciler

- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク・プロセス・データ鮮度）
  - TradeMonitor（滞留注文・約定異常価格検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件で data/kill.flag を書き込む）
  - MonitoringEngine（各 Monitor の巡回・アラート送信）
  - MonitoringDB（SQLite を使った監視ログ永続化）

- Portfolio construction
  - 候補選定、スコア/等分配重み、セクターキャップ、レジーム乗数
  - ポジションサイズ計算（単元株丸め、リスクベース、aggregate cap）

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - Forward returns / IC / ファクター統計サマリー

- AI（OpenAI ベース）
  - news_nlp: raw_news をバッチし LLM で銘柄ごとにセンチメントを算出 → ai_scores に書込
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM 評価を合成して market_regime 登録

- ツール
  - config_setup: .env を対話式に作成/更新
  - validate_config: 環境変数・config/*.yaml の存在チェックと簡易検証
  - tools.paper_verification_report: Paper Trading データから検証レポート生成

---

## 前提・依存パッケージ

必須（主にコードで直接 import されているもの）：
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使用する場合）
- sqlite3（標準ライブラリ）
- （オプション）PyYAML — validate_config が config/*.yaml をパースして検証する場合に使用

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai
# PyYAML を使う場合:
pip install pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を用意する
2. 依存パッケージをインストール（上記参照）
3. .env を作成
   - 対話式に作る: python -m kabusys.config_setup
   - 手動で作る: ルートに `.env` を作成し、最低限次の必須変数を設定
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - (任意) OPENAI_API_KEY=... （AI機能使用時）
   - デフォルトファイルパス:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱いになります
5. データディレクトリ作成
   - デフォルトでは `data/` を利用します。必要に応じて作成してください。

---

## 実行方法（主要コマンド）

- Execution エンジンの起動（通常はプロダクションまたはペーパートレード）
  - python -m kabusys.run_execution
  - 動作ポイント:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - エンジンは PID ファイル（デフォルト data/execution.pid）を扱います。
    - 停止は kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）や stop_requested.flag の検出で行います。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 特記事項:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - 監視処理は monitoring DB（Settings.sqlite_path）に書き込みます（monitoring は環境にかかわらず本番 sqlite_path を使用）。
    - 停止フラグファイル（data/stop_requested.flag）検出でループを終了します。

- 設定ウィザード（.env 作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - これは環境変数と config/*.yaml の簡易チェックを行います（PyYAML 未導入時は YAML 検証をスキップします）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能。デフォルトは data/paper_trading.db

- AI 関連
  - news_nlp.score_news / regime_detector.score_regime を呼び出して運用する。OpenAI API を使うため OPENAI_API_KEY が必要です（関数呼び出しで api_key を渡すことも可能）。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (default: development) — valid: development, paper_trading, live
- LOG_LEVEL (default: INFO)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading 時の fill 動作: instant | partial | never | reject)
- OPENAI_API_KEY (AI 機能利用時)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数)
- KILL_FLAG_CLEAR_ON_START (0|1) — ExecutionEngine 起動時に kill.flag を自動クリアするか

---

## 運用上の注意点

- Paper Trading は本番 DB と完全に分離されます。KABUSYS_ENV=paper_trading を使用すると paper_trading 専用 SQLite に記録されます。
- Monitoring は常に Settings.sqlite_path（本番監視 DB）を使用するため、モニタリング DB の場所は慎重に設定してください。
- Kill Switch（data/kill.flag）を使用すると ExecutionEngine を停止できます。KILL_FLAG_CLEAR_ON_START を本番で 1 にすると危険です（本番では 0 推奨）。
- OpenAI の呼び出しはレート制限やネットワーク障害に対してリトライ／フォールバックの実装がありますが、API キー漏洩やコスト管理には注意してください。
- .env は機密情報を含むため Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。

---

## ディレクトリ構成（src/kabusys 以下の主なファイル／モジュール）

- kabusys/
  - __init__.py (バージョン定義)
  - config.py (Settings クラス、.env の自動読み込み / パース)
  - config_setup.py (.env 対話式ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - utils/
    - process_priority.py (プロセス優先度 / CPU affinity 設定ユーティリティ)
  - execution/  (発注関連コンポーネント)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
  - monitoring/
    - monitoring_db.py (SQLite 永続化層)
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py (候補選定・重み付け)
    - position_sizing.py (株数決定・資金配分)
    - risk_adjustment.py (セクターキャップ・レジーム乗数)
  - data/ (データパイプライン・DuckDB 関連; get_last_price_date 等)
  - research/
    - factor_research.py (ファクター計算)
    - feature_exploration.py (forward returns, IC, 統計)
  - ai/
    - news_nlp.py (ニュース NLP -> ai_scores 書込)
    - regime_detector.py (市場レジーム判定)
  - tools/
    - paper_verification_report.py (ペーパートレード検証レポート)
  - その他: config/*.yaml 想定（system_config.yaml 等）

---

## 例: 最小 .env（参考）

.env.example 的な最小例（実運用では必ず自分の値に置き換えてください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
KILL_FLAG_CLEAR_ON_START=0
```

---

## トラブルシュート / よくある確認ポイント

- validate_config を実行してエラーや警告を確認してください。
- run_execution を起動してもすぐ終了する場合:
  - data/stop_requested.flag が存在していないか確認
  - PID ファイル / kill.flag を確認
- AI 機能（news_nlp / regime_detector）が動かない場合:
  - OPENAI_API_KEY が設定されているか
  - openai ライブラリがインストールされているか
- DuckDB / SQLite のパスが正しいか、親ディレクトリが存在するかを validate_config でチェック可能

---

この README はソースコードの主要な動作と使い方の概要を説明しています。実運用・開発の際は各モジュールの docstring やソース（特に設定項目や関数の挙動）を参照してください。必要であれば、より詳細な運用手順・アーキテクチャ図・DB スキーマ説明を追加できます。必要な場合は指示してください。