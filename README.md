KabuSys — 日本株自動売買システム (README)
=========================================

概要
----
KabuSys は日本株の自動売買・研究・監視のための小規模フレームワークです。本リポジトリは以下の主要関心事を含みます。

- 実運用向けの ExecutionEngine（発注・リスク制御）
- System / Trade / Risk の監視（Monitoring）
- ポートフォリオ構築（銘柄選定・重み付け・株数算出）
- 研究用ファクター計算・特徴量探索（DuckDB を使用）
- AI を使ったニュース NLP（OpenAI）と市場レジーム判定
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

主な機能
--------
- 実行環境の分離:
  - KABUSYS_ENV により development / paper_trading / live を切替
  - paper_trading モードでは MockBrokerClient を使用し paper_trading.db に記録
- 監視:
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - Kill Switch によるフラグファイルでの Execution 停止制御
- ポートフォリオ構築:
  - 候補選定、等金額・スコア加重の重み計算、リスク制約（セクターキャップ、レジーム乗数）
  - position sizing（リスクベース・等配分など）／単元株への丸めと aggregate cap の制御
- リサーチ:
  - モメンタム・バリュー・ボラティリティ等のファクター計算（DuckDB）
  - 将来リターン・IC（Information Coefficient）や統計サマリー
- AI サービス:
  - ニュース記事から銘柄ごとのセンチメントスコアを生成（OpenAI API）
  - マクロニュースと ETF（1321）MA200 を組合せた市場レジーム判定
- 開発支援:
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 設定検証ツール（validate_config.py）
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report.py）

セットアップ手順
----------------
前提:
- Python 3.10+（型ヒントに | を使用）
- OS により追加パッケージ（psutil 等）のインストール権限が必要

1. リポジトリをクローン・作業ディレクトリへ移動

2. 依存パッケージをインストール（例: pip）
   - 最低限の依存例:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（設定検証で YAML 検証を行う場合）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. 環境変数 (.env) を用意
   - 対話式ウィザードで初期作成:
   ```
   python -m kabusys.config_setup
   ```
   - あるいは .env ファイルを手動作成（.env.example を参照）
   - 自動読み込み:
     - 起動時にプロジェクトルートに .env / .env.local があれば自動ロードされます。
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 設定を検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAIL とする
   ```

5. データディレクトリ等（通常は data/）を作成（必要に応じて）
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db

主要な環境変数 (よく使うもの)
------------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB; デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/...)
- MONITOR_POLL_INTERVAL (監視ループの秒間隔; デフォルト 60)
- PAPER_FILL_MODE (paper_trading の約定挙動: instant | partial | never | reject)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか; "1" でクリア)

使い方（実行例）
----------------

- 監視ループを起動（プロダクションの監視プロセス）
```
python -m kabusys.run_monitoring
# 環境変数でポーリング間隔を変更
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- Execution エンジンを起動（発注エンジン）
```
python -m kabusys.run_execution
```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading DB に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動を行いません。
  - Execution は data/execution.pid を使用して PID 管理を行います。

- 設定ウィザード（.env 作成）
```
python -m kabusys.config_setup
```

- 設定検証
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- Paper Trading 検証レポートの生成
```
python -m kabusys.tools.paper_verification_report
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```

- ライブラリとしての利用例（Python 内から）
```py
from kabusys.research import calc_momentum, calc_volatility, calc_value
# DuckDB 接続を渡して日次ファクターを計算
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
res = calc_momentum(conn, target_date=date(2026,4,15))
```

監視の停止 / Kill Switch
-----------------------
- ExecutionEngine の停止は data/kill.flag に理由を書き込むことで指示できます（KillSwitch がファイル存在を検出）。
- kill.flag を自動でクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定します（本番では 0 推奨）。
- 監視プロセスを終了させるにはプロジェクトルートの data/stop_requested.flag を作成します（run_monitoring/run_execution が検知して終了）。

ログ
---
- デフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日保持）。
- ログ出力は stdout とファイルの両方に行われます。LOG_DIR 環境変数で変更可能。

ディレクトリ構成（主なファイル / モジュール）
----------------------------------------
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・自動 .env ロード / Settings クラス
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite のスキーマ & 永続化操作
    - system_monitor.py       — システム状態 / データ鮮度監視
    - trade_monitor.py        — （trade に関する監視ロジック）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - monitoring_engine.py    — 各 Monitor を束ねる実行ループ
    - kill_switch.py          — kill.flag 書き込みと評価ロジック
    - alert_manager.py        — （通知・アラート発行用ラッパ、未列挙の実装）
  - execution/
    - execution_engine.py     — ExecutionEngine（発注ライフサイクル）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数算出・aggregate cap
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — momentum/value/volatility ファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py      — レジーム判定（MA200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成スクリプト

補足・運用上の注意
-----------------
- 環境変数の自動ロード順: OS env > .env.local > .env。自動ロードを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。
- 本番（KABUSYS_ENV=live）では LINE 通知等の設定と kill flag の取り扱いに十分注意してください。
- OpenAI を使う機能は API 呼び出しを含むため、API キー設定とコスト・レート制限に注意してください。
- DuckDB / SQLite はローカルファイル DB を使用します。バックアップや排他アクセス（複数プロセスからの同時書込）には配慮してください。
- process_priority.set_process_priority は OS に依存する権限が必要な場合があり、失敗時は警告が出てスキップされます。

ライセンス・バージョン
---------------------
- パッケージバージョン: src/kabusys/__version__ = 0.1.0
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

問い合わせ / 開発メモ
--------------------
- 開発者向け: 各モジュールは概ね「副作用を最小化」する設計（純関数群と DB 書込の分離）を心がけています。ユニットテストの追加、監視ルールの微調整、AI レスポンスの堅牢性向上が今後の改善候補です。

以上。必要であれば、セクションの追記（API リファレンス、コマンド例の詳細、Docker 化手順など）を追加します。