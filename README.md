# KabuSys

日本株向け自動売買システムのリポジトリ（読み取り専用の README）。  
この README はコードベースを元に作成しています。

## プロジェクト概要
KabuSys は日本株の自動売買を想定したモジュール群です。  
主な目的は以下のとおりです。

- 発注 / リスク管理を担う ExecutionEngine（本番・ペーパートレード対応）
- システム稼働監視 / アラート / Kill Switch を提供する Monitoring
- ポートフォリオ構築（銘柄選定・配分・サイズ決定・セクター制御）
- リサーチ用ファクター計算・特徴量解析（DuckDB を利用）
- ニュース NLP / レジーム判定（OpenAI を用いたスコアリング）
- ペーパートレード結果検証ツール 等

設計方針として、DB（SQLite / DuckDB）や外部 API へのアクセスを明確に分離し、テストしやすい純粋関数群と永続化層を分離しています。

---

## 主な機能一覧
- Execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアントの抽象化（Mock 対応）
  - 注文管理・リスク制御・照合（reconciler / risk_manager 等）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - TradeMonitor：注文滞留・約定異常検出（trade_logs）
  - RiskMonitor：ドローダウン・ポジション上限監視／Kill Switch 連携
  - MonitoringEngine：ポーリングループ、アラート送出
- Portfolio
  - 銘柄候補選定、等金額/スコア加重の重み算出
  - ポジションサイズ計算（単元丸め、資金制約、aggregate cap）
  - セクター制限・レジーム乗数
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリ
- AI
  - ニュースセンチメントスコア（OpenAI GPT 系）
  - 市場レジーム判定（テクニカル + マクロ NLP 合成）
- Tools
  - Paper Trading 検証レポート生成スクリプト
- 設定関連
  - 対話式 .env ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

---

## 必要条件（概略）
- Python 3.9+
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - pyyaml（config ファイル検証時に任意）
- SQLite（標準ライブラリで可）
- （任意）kabuステーション API クライアント／J-Quants の認証情報

（プロジェクトに requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順（例）
1. リポジトリをクローン / 展開
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)
3. 必要パッケージのインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt があればそれを使う）
4. 初期設定（.env 作成）
   - 対話式ウィザードを実行して .env を生成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に直接 .env を作成
5. 設定検証
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict
6. データディレクトリの作成
   - デフォルトでは `data/` や `logs/` を使用します。自動作成されますが、権限等に注意してください。
7. （ペーパートレード運用）PAPER_TRADING_SQLITE_PATH の確認または設定
   - デフォルト: data/paper_trading.db（ペーパートレードは本番 DB と分離）

---

## 主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN (J-Quants)
  - KABU_API_PASSWORD (kabuステーション)
- 運用・挙動
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading 時の約定振る舞い（instant|partial|never|reject）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1、本番は 0 推奨）
- 自動 .env 読み込み
  - デフォルトでプロジェクトルートの `.env` と `.env.local` を自動読み込みします。
  - 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（コマンド例）

- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - ログは logs/execution.log に出力されます（設定に従う）
  - ExecutionEngine は data/execution.pid を使用し、data/stop_requested.flag / data/kill.flag を監視します

- Monitoring を起動（ポーリング）
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能
  - python -m kabusys.run_monitoring
  - 監視ループは stop_requested.flag を検知すると停止します

- .env 対話ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI / リサーチ機能（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - research モジュール例:
    - kabusys.research.calc_momentum(duckdb_conn, date(2026,4,1))

---

## 運用・開発上の注意点
- Kill Switch / 停止フラグ
  - KillSwitch は data/kill.flag を書き込んで ExecutionEngine の停止を促します（明示的な安全装置）。
  - 初期設定で本番は KILL_FLAG_CLEAR_ON_START=0 を推奨（起動時に誤ってクリアされないように）。
- ペーパートレードの分離
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、DB は paper_trading.db に記録されます（本番 DB から完全分離）。
- ログ
  - logs/ 以下に日次ローテーションでログが出力されます（TimedRotatingFileHandler）。
  - 標準出力は stdout を使用（cron 等でのログ集約に配慮）。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、必要に応じてカラム追加マイグレーションを行います（例: peak_value, latency_ms）。
- 自動ロード
  - config モジュールはプロジェクトルートを .git / pyproject.toml から検出して .env を自動読み込みします。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 権限・優先度
  - 起動スクリプトはプロセス優先度を上げる試みを行います（psutil を使用）。権限が不足すると警告を出してスキップされます。

---

## 主要ファイル / ディレクトリ構成
プロジェクトの主な構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                     — 実行時に使うファイル群（data/*.db, *.pid, *.flag）

（注）上記はコードベースの代表的なファイル群です。細かいファイルはソースツリーを参照してください。

---

## 開発者向けメモ
- テストの容易さを考慮し、純粋関数（portfolio, research 等）と副作用ありの永続化層（monitoring_db 等）を分離しています。
- OpenAI 呼び出しはリトライ・JSON パース耐性などを備え、API キー未設定時は適切に失敗します（値渡し or 環境変数で指定）。
- DuckDB 接続は分析処理（research / ai）で利用します。データテーブル（prices_daily / raw_financials / raw_news 等）が前提です。

---

この README はコード内のドキュメント文字列と実装に基づいて作成しました。詳細な設定内容や運用フロー、systemd / container 化などは運用ポリシーに合わせて別途ドキュメント化してください。