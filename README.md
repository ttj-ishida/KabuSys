# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・ポジション決定、リサーチ（ファクター計算）、AI を用いたニューススコアリングなどの機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買のエンジンおよび補助ツール群を提供します。主な目的は以下です。

- 売買シグナルに基づく自動発注と発注管理
- システム稼働・注文・リスク監視（Kill Switch 等の安全機構）
- DuckDB / SQLite を用いたデータ分析・ログ永続化
- ファクター計算や特徴量探索などのリサーチ用ユーティリティ
- OpenAI を利用したニュースセンチメント評価やレジーム判定（オプション）
- ペーパートレード用の分離された DB／モックブローカー

---

## 機能一覧

- Execution
  - ExecutionEngine による発注セッション管理（本番 / ペーパートレード対応）
  - Broker クライアントファクトリ（環境に応じて実ブローカー or Mock を切替）
  - OrderManager / Reconciler / RiskManager による注文・リスク管理
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス生存確認
  - TradeMonitor: 注文滞留・異常約定などの監視（trade_logs 参照）
  - RiskMonitor: ドローダウンやポジション上限の監視、ダッシュボード更新
  - MonitoringEngine: 各 Monitor を束ねるポーリングループ、KillSwitch の実行
- Data / Research
  - DuckDB を利用したファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン計算 / IC 計算 / 統計サマリー等の分析ユーティリティ
- Portfolio construction
  - 候補選定、等配分・スコア配分、リスクベースのポジションサイジング
  - セクターキャップ、レジーム乗数等の調整
- AI
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント集計（ai_scores）
  - マクロニュース＋ETF MA による市場レジーム判定
  - API 呼び出しは冗長性（バックオフ等）を考慮
- Tools
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading の検証レポート生成スクリプト

---

## 必要依存パッケージ（代表例）

本リポジトリの主要依存ライブラリ（環境に応じて適宜バージョン指定してください）:

- Python 3.10+（型ヒントの構文に | を使用）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config YAML 検証を行う場合、任意）

requirements.txt は含まれていないため、仮想環境を作成してから必要なパッケージをインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境の作成・有効化
3. 依存パッケージをインストール（上記参照）
4. 環境変数設定
   - 推奨: 対話式ウィザードを使って .env を作成
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env を手動作成（例は下記参照）
5. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
   ```
6. データディレクトリ（logs / data 等）と DB パスの確認。起動スクリプトが自動作成する場合もあるがパーミッション等に注意。

.env の最低必須項目（例）
```
# 実行環境
KABUSYS_ENV=development

# 必須
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password

# データベース
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# ログ
LOG_LEVEL=INFO

# OpenAI（AI 機能を利用する場合）
OPENAI_API_KEY=sk-...
```

注意:
- ペーパートレード時は KABUSYS_ENV=paper_trading に設定すると MockBrokerClient が利用され、データは paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に分離して記録されます。
- .env の自動読み込み機構はデフォルトで有効（プロジェクトルートが検出できる場合）。テスト等で自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 実行方法（主要コマンド）

- ExecutionEngine（発注エンジン）を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBroker を用い、記録先 DB は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）になります。
  - 起動前に data/kill.flag をクリアしたい場合は `Settings.kill_flag_clear_on_start` が 1 にしておくと自動クリアされます（本番環境では推奨されません）。

- Monitoring（監視ループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト: 60）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視用 DB の共通利用を想定）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` で指定、無指定時は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db が使われます。

- AI 系関数の例（Python REPL 等から）
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
  ```
  または
  ```py
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,4,1), api_key="sk-...")
  ```

---

## 停止 / Kill Switch

- 実行中の ExecutionEngine を安全に停止するには、監視側が `kill.flag` を書き込むことで停止シグナルを送出します（KillSwitch 機能）。
  - kill.flag のデフォルトパスは Settings.kill_flag_path（デフォルト: data/kill.flag）。
  - kill.flag が存在すると ExecutionEngine は起動を停止するか、実行中セッションを停止します（実装に依存）。
- 手動で強制停止したい場合はプロセスに SIGINT（Ctrl+C）等を送ります。
- run_execution/run_monitoring には stop_requested.flag という停止フラグファイルも利用されています（data/stop_requested.flag）。このファイルを作成するとループを抜けます。

---

## 設定可能な主な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB、デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/...)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数)
- KILL_FLAG_CLEAR_ON_START (0/1 本番では 0 推奨)

詳しくは `kabusys.config.Settings` のプロパティを参照してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を基準）

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env 自動読み込みと Settings クラス
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - __init__.py
    - logging_setup.py            — ログ出力設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py            — monitoring 用 SQLite 永続化層
    - system_monitor.py           — システム状態・データ鮮度監視
    - trade_monitor.py            — （存在）注文監視（ファイルでは一部のみ抜粋）
    - risk_monitor.py             — ドローダウン / ポジション上限監視
    - kill_switch.py              — kill.flag 書き込みユーティリティ
    - monitoring_engine.py        — 監視エンジン（各監視を束ねる）
    - alert_manager.py            — （存在）アラート送信の抽象（LINE 等）
  - execution/
    - execution_engine.py         — ExecutionEngine（主処理: run_session 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py          — ファクター計算（momentum/value/volatility）
    - feature_exploration.py      — 将来リターン / IC / 統計
    - __init__.py
  - ai/
    - news_nlp.py                 — ニュースセンチメント（OpenAI 経由）
    - regime_detector.py          — 市場レジーム判定
    - __init__.py

（注）リストはこのコードベースから抜粋した主要コンポーネントです。細かい補助モジュールやテストコードは省略しています。

---

## 開発メモ / 注意事項

- 本プロジェクトは本番発注リスクを伴います。実行前に必ず設定（特に KABUSYS_ENV、API キー、パス）を確認してください。
- .env は絶対にリポジトリにコミットしないでください。
- AI 機能は外部 API（OpenAI）を使用するため、APIキーやコストに注意してください。API 呼び出しは再試行・バックオフが組み込まれていますが、失敗時のフォールバック（スコア=0 等）が実装されています。
- DuckDB/SQLite のスキーマはモジュール内でマイグレーション処理を行う箇所がありますが、本番移行時はバックアップと検証を行ってください。
- ログは `logs/<app_name>.log` に日次ローテーションで保存されます（デフォルト 30 日分保持）。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

必要であれば、README に以下を追加できます:
- 各モジュール（ExecutionEngine / MonitoringEngine / AI）の設計図（シーケンスやデータフロー）
- API（関数）リファレンス
- 開発用テスト手順やユニットテストの実行方法

どの情報を追加したいか教えてください。