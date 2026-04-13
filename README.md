# KabuSys

日本株自動売買システムの軽量コアライブラリ（ドキュメント用抜粋）。  
この README はリポジトリ内の主要スクリプト・モジュールの使い方、設定、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を備えたモジュール群です。

- ファクター計算（momentum / volatility / value 等）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- 実行（ExecutionEngine）周りの注文管理、リコンシリエーション
- 監視（System / Trade / Risk モニタリング、LINE 通知、kill-switch）
- AI 補助（ニュースセンチメント / レジーム判定：OpenAI を使用）
- Paper Trading 用の検証ツール・レポート出力
- Streamlit ベースの監視ダッシュボード

設計方針の一部：
- DuckDB / SQLite をデータ層に使い、研究・本番データを分離可能
- 外部 API（ブローカー・OpenAI）は抽象化されフェイルセーフ設計
- 多くの処理は副作用を最小化した純粋関数として実装

---

## 主な機能一覧

- kabusys.research
  - calc_momentum / calc_volatility / calc_value：DuckDB を用いたファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量解析・IC 計算

- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights：候補選定 / 重み化
  - calc_position_sizes：株数（発注数量）計算
  - apply_sector_cap / calc_regime_multiplier：セクター上限・レジーム補正

- kabusys.execution
  - OrderManager / Reconciler / ExecutionEngine（起動スクリプト経由で動作）
  - BrokerClientFactory により本番 / mock ブローカーを切替可能（paper_trading）

- kabusys.monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard
  - AlertManager：LINE 通知（クールダウン付き）
  - KillSwitch：kill.flag による ExecutionEngine 停止指示
  - streamlit_dashboard：監視ダッシュボード（Streamlit）

- kabusys.ai
  - news_nlp.score_news：ニュースを LLM でセンチメント評価して ai_scores に保存
  - regime_detector.score_regime：ETF MA とマクロニュースで市場レジーム判定

- ツール
  - kabusys.tools.paper_verification_report：Paper Trading の検証レポート出力

---

## 前提 / 依存パッケージ

主に次のパッケージが必要になります（環境により追加）：

- python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- その他：標準ライブラリ（sqlite3, logging, datetime 等）

インストール例（pip）:
```
pip install duckdb psutil requests openai streamlit
```

requirements.txt がある場合はそちらを使用してください。

---

## セットアップ手順

1. リポジトリを取得して Python 環境を用意する
2. 依存パッケージをインストール（上記参照）
3. データディレクトリを作る（任意）
```
mkdir -p data
```
4. 環境変数 / .env を準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（ただし OS 環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
     - KABU_API_PASSWORD — 必須（kabuステーション）
     - OPENAI_API_KEY — OpenAI 利用時に必要
     - KABUSYS_ENV — 環境（development | paper_trading | live）デフォルト: development
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — PaperTrading 用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH — ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH — kill.flag パス（デフォルト: data/kill.flag）
     - PAPER_FILL_MODE — PaperTrading の fill モード（instant, partial, never, reject）

例 .env 抜粋:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## 実行方法（使い方）

以下はパッケージをソースのまま実行する方法（パッケージインストールしている場合は同様に -m で実行可能）。

- 監視ループ（SystemMonitor 単体起動）
```
python -m kabusys.run_monitoring
```
説明:
- 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。1 未満や不正値は 60 秒にフォールバック。
- Monitoring は実行環境に関係なくプロダクションの sqlite_path を使用して監視ログを記録します。
- 起動時にプロセス優先度を "high" に設定しようとします（プラットフォーム依存で失敗する場合あり）。

- 実行エンジン（注文実行）の起動
```
python -m kabusys.run_execution
```
説明:
- `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用して paper_trading 用 DB（デフォルト: data/paper_trading.db）に記録します。本番 DB と分離されます。
- 起動時にプロセス優先度を "high" に設定します。
- 各種依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine）を組み立てて実行します。

- Streamlit ダッシュボード（監視）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
説明:
- 監視用 SQLite を読み取り専用で開き、ダッシュボードを表示します。
- 監視ループ（run_monitoring）を先に起動してデータを蓄積してください。

- Paper Trading 検証レポート
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
出力:
- 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を行います。
- デフォルト DB は `data/paper_trading.db`。環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可能。

- AI 関連（ニュースセンチメント / レジーム判定）
  - ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI の API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。
  - API 呼び出しはリトライやフェイルセーフ処理を備えています（失敗時は安全なデフォルトで継続）。

---

## 主要な設定（環境変数）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: PaperTrading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行制御用ファイルパス
- OPENAI_API_KEY: OpenAI を利用する際に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）用

自動的に .env / .env.local をプロジェクトルートから読み込みます（OS 環境変数優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 内の主なファイル・モジュールと短い説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数読み込み・Settings クラス（.env 自動ロード、各種設定プロパティ）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替あり）

  - ai/
    - news_nlp.py — raw_news を LLM（OpenAI）でセンチメントして ai_scores に書き込む
    - regime_detector.py — ma200 とマクロニュースで市場レジーム判定
    - __init__.py

  - monitoring/
    - monitoring_db.py — SQLite テーブル定義と抽象化（MonitoringDB）
    - system_monitor.py — CPU/Memory/Disk・プロセス・データ鮮度監視
    - trade_monitor.py — 滞留注文・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — LINE Push 通知（クールダウン管理）
    - kill_switch.py — kill.flag による停止信号の書き込み
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
    - __init__.py

  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
    - __init__.py

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注数量計算（リスクベース等）
    - risk_adjustment.py — セクター上限、レジーム乗数
    - __init__.py

  - execution/
    - order_manager.py — 注文状態遷移管理（OrderManager）
    - reconciler.py — 起動時リコンシリエーション（Order / ポジション突合）
    - （その他：broker_factory, execution_engine, order_repository などが想定されます）

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール
    - __init__.py

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

（実際のリポジトリでは data/, docs/ 等のディレクトリが存在する場合があります）

---

## 運用上の注意 / ヒント

- monitoring のログ・テーブルは環境にかかわらず `Settings.sqlite_path` に記録されます（監視は本番 DB を参照する想定）。
- Paper Trading は本番 DB と明確に分離され、`KABUSYS_ENV=paper_trading` では `PAPER_TRADING_SQLITE_PATH` を使用します。
- OpenAI API 呼び出しは通信失敗や 5xx に対してバックオフ／リトライを行いますが、API キー未設定時は例外を投げます。テスト時はモック可能な設計です（内部関数を patch）。
- process priority / cpu affinity はプラットフォーム依存（psutil 経由）。権限不足で設定できない場合は警告ログを出してスキップします。
- DB スキーマの簡易マイグレーション（カラム追加等）ロジックを一部持っていますが、本格運用時はマイグレーション戦略を整備してください。

---

必要であれば、各モジュールの API 仕様や ExecutionEngine / Broker API の詳細、ユニットテストの実行方法、CI 設定などの追加ドキュメントも作成できます。どの部分の詳細が要りますか？