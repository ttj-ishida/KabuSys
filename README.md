# KabuSys

日本株向け自動売買システムのコアライブラリ群（モニタリング、実行エンジン、ポートフォリオ構築、リサーチ、AI 補助など）。  
このリポジトリはライブラリ + 実行スクリプト群を含み、ローカル開発・ペーパートレード・本番運用まで想定しています。

注意: README はこのコードベースの公開ソースから導出した情報に基づき作成しています。

## 概要
KabuSys は次の機能を持つ Python ベースのシステムです。

- 実行エンジン（ExecutionEngine）による注文管理・リスク管理・ブローカ連携
- 監視コンポーネント（System/Trade/Risk Monitor）による稼働監視とアラート / Kill Switch
- ペーパートレード用の分離 DB（data/paper_trading.db）対応
- DuckDB を用いたファクター計算・リサーチモジュール（momentum/value/volatility 等）
- ニュース NLP（OpenAI）を用いた銘柄センチメント評価と市場レジーム判定
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証、検証レポート生成）

## 主な機能一覧
- 起動スクリプト
  - run_execution.py: 実行エンジン（本番 or paper_trading）
  - run_monitoring.py: SystemMonitor のポーリングループ
- 設定管理
  - config_setup.py: .env 対話式ウィザード（.env 作成/更新）
  - validate_config.py: 起動前の設定検証 CLI
  - Settings クラス: 環境変数・既定値の一元管理
- 監視（monitoring）
  - system_monitor: CPU/メモリ/Disk・データ鮮度・実行プロセス監視
  - trade_monitor / risk_monitor / monitoring_engine / kill_switch
  - monitoring_db: SQLite に監視ログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- 実行（execution）
  - ExecutionEngine（起動/セッション管理）
  - OrderManager / OrderRepository / RiskManager / Reconciler / BrokerClientFactory（ブローカ差替え対応）
- 研究・分析（research）
  - factor_research: momentum / volatility / value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC（スピアマン）等
- ポートフォリオ（portfolio）
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- AI（ai）
  - news_nlp: OpenAI を用いたニュースごとのセンチメント付与と ai_scores への書込み
  - regime_detector: ETF とマクロニュースを合成した市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート出力

## 必須 / 推奨環境
- Python 3.10 以降（型ヒントで | 演算子を使用しているため）
- 推奨パッケージ（例: pip でインストール）
  - duckdb
  - psutil
  - openai
  - pyyaml（config の YAML 検証を有効にする場合）
- SQLite（標準ライブラリで利用）
- ネットワーク接続（本番で OpenAI / ブローカ API を使用する場合）

例:
```
pip install duckdb psutil openai pyyaml
```

（requirements.txt はリポジトリに含まれていない想定のため、必要パッケージを手動で用意してください）

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン / コピー
2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb psutil openai pyyaml
   ```
4. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードは J-Quants トークン、kabu API パスワード、KABUSYS_ENV（development / paper_trading / live）などを作成します。
   - .env は絶対に Git にコミットしないでください（ウィザードのヘッダにも警告あり）。
5. 設定検証（起動前確認）
   ```
   python -m kabusys.validate_config
   ```
   - --strict を付けると警告も失敗扱いになります。

## 使い方（主要 CLI / API）
- 実行エンジン起動（モードは KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録します。
  - 実行中に data/stop_requested.flag を作成すると起動中のエンジンを停止させる仕組みがあります。
  - 実行時に PID ファイル（data/execution.pid）を出力します。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path、デフォルト data/monitoring.db）を使用します。
  - 停止は data/stop_requested.flag を立てることで伝播します。

- .env の対話式作成 / 更新
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI スコアリング（ライブラリ呼び出し例）
  - ニュース NLP（ai_scores へ書き込み）
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```
  - レジーム判定
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```

- 研究モジュールの利用例（DuckDB 接続を渡して呼び出す）
  ```py
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, target_date=date(2026,4,1))
  vol = calc_volatility(conn, target_date=date(2026,4,1))
  ```

## 主要な環境変数（主なもの）
- 必須（運用時）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用モード:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DB パス:
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 時の専用 DB、デフォルト: data/paper_trading.db)
- ロギング:
  - LOG_LEVEL (デフォルト: INFO)
  - LOG_DIR (デフォルト: logs/)
- Kill Switch / 制御:
  - KILL_FLAG_CLEAR_ON_START (0/1。production では 0 推奨)
  - MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
- OpenAI:
  - OPENAI_API_KEY（ai.news_nlp / regime_detector で使用可能）

（config_setup により .env を生成できます）

## ログ
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
- デフォルト: stdout と logs/<app_name>.log（日次ローテーション、30日保持）
- LOG_DIR 環境変数で保存先を変更可能

## ファイル / ディレクトリ構成
（抜粋・主要ファイル）
- src/kabusys/
  - __init__.py
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - config.py                      — Settings / .env 自動ロードロジック
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - utils/
    - logging_setup.py             — ログ設定
    - process_priority.py          — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py             — SQLite テーブル初期化・永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (実装あり)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - data/ (実行時生成想定)
    - monitoring.db (デフォルト SQLite)
    - paper_trading.db (paper_trading 用 DB)
    - execution.pid / stop_requested.flag / kill.flag

（実際のリポジトリに応じて若干の追加ファイル/ディレクトリが存在する可能性があります）

## 運用上の注意
- .env は機微な API キーを含むため絶対に Git にコミットしないでください。
- 本番運用時は KABUSYS_ENV=live に設定し、KILL_FLAG_CLEAR_ON_START は 0 にしてください。
- Monitoring は監視用 SQLite（SQLITE_PATH）を参照します。monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用する設計です（監視と発注 DB を混同しないように注意）。
- OpenAI API を使う処理（news_nlp、regime_detector）は API のレート制限やエラーを考慮してリトライ・フェイルセーフが入っていますが、APIキーやコストを考慮して運用してください。
- プロセス優先度や CPU affinity の設定はプラットフォーム依存で失敗する場合があり、その場合はログに警告が出ます。

## 開発 / テストのヒント
- DuckDB の接続を渡して research モジュールを手動で試せます（prices_daily 等のテーブルが必要）。
- validate_config は YAML がインストールされている場合に config/*.yaml のパース検証も行います。
- 単体で監視ループを一度だけ回したい場合は MonitoringEngine.run_once を利用できます（テスト用）。

---

この README はリポジトリ内のソースコードドキュメントを要約したものです。個別モジュールの詳細は各ソースファイルの docstring / コメントを参照してください。追加で README に載せたい内容（例: サンプル .env、詳しい起動例、デプロイ手順等）があれば教えてください。