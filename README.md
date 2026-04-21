README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコードベースです。本プロジェクトは以下の主要領域を含みます。

- 実行エンジン（ExecutionEngine）: 発注・リスク管理・再整合を担うランタイム
- 監視（Monitoring）: システム稼働性・注文状況・リスク指標の定期チェックとアラート
- ポートフォリオ構築（Portfolio）: 候補選定・重み付け・ポジションサイズ計算
- リサーチ（Research）: ファクター計算・特徴量解析・将来リターン計算
- AI 補助（AI）: ニュース NLP によるセンチメント評価、レジーム判定
- 開発ツール群: .env ウィザード、設定検証、Paper Trading レポート生成 等

主要な設計方針
- 本番とペーパートレードの DB を分離（paper_trading モード）
- ルックアヘッドバイアスを避ける（date/時間の参照に注意）
- フェイルセーフ（API 失敗時は安全側にフォールバック）
- ロギング・PID/Kill Switch による運用管理を重視

機能一覧
--------
- 実行（run_execution.py）
  - 実際のブローカークライアントまたは MockBrokerClient（KABUSYS_ENV=paper_trading）
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine 起動
  - 停止フラグ（data/stop_requested.flag）検出によるグレースフル終了
- 監視（run_monitoring.py / monitoring/*）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリング
  - kill.flag 書き込みによる ExecutionEngine 停止トリガ（KillSwitch）
  - 監視結果の永続化（SQLite）
- ポートフォリオ構築（portfolio/*）
  - シグナルの並び替え・候補選定（select_candidates）
  - 等金額・スコア加重の重み計算（calc_equal_weights / calc_score_weights）
  - 単元株丸め・リスクベース・等のポジションサイズ計算（calc_position_sizes）
  - セクター上限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- リサーチ（research/*）
  - momentum, volatility, value 等のファクター計算（DuckDB を利用）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI（ai/*）
  - ニュース記事を LLM（OpenAI）で評価して ai_scores に書き込む（news_nlp.score_news）
  - マクロニュース + ETF ma200 による市場レジーム判定（regime_detector.score_regime）
- ユーティリティ
  - .env 対話式作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - 統一ロギング設定（utils/logging_setup.py）
  - プロセス優先度設定・CPU affinity（utils/process_priority.py）

セットアップ手順
--------------
1. リポジトリをクローン／展開
   - プロジェクトルート直下に src/ がある想定です（例: src/kabusys/...）。

2. Python 仮想環境を作成・有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 必須: duckdb, psutil, openai
   - 開発/オプション: PyYAML（validate_config の YAML 検証用）
   - 例（pip）:
     - pip install duckdb psutil openai PyYAML

4. .env を作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに .env を直接配置
   - 重要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他の主な環境変数（デフォルト値は括弧内）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - LOG_LEVEL (INFO)
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE ("instant"|"partial"|"never"|"reject") — デフォルト: instant

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラーにしたい場合:
     - python -m kabusys.validate_config --strict

6. ログディレクトリ
   - デフォルト: logs/
   - 環境変数 LOG_DIR で変更可
   - ログは日次ローテートされ、 logs/<app_name>.log に出力されます

使い方
------
起動 / 停止の基本

- ExecutionEngine（取引エンジン）を起動
  - python -m kabusys.run_execution
  - 起動時に data/execution.pid に PID を書き込みます（実行スクリプトが担当）
  - 停止: data/stop_requested.flag を作成すると監視ループが検知して Graceful 停止します
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます

- Monitoring（監視ループ）を起動
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で設定可能（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は実行環境にかかわらず本番用 sqlite_path（SQLITE_PATH）を使用して監視テーブルを管理します
  - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループを終了します

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能の呼び出し（ライブラリ関数）
  - news NLP（ニュースセンチメントを ai_scores に書く）
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - 注: OpenAI API キーは api_key 引数または OPENAI_API_KEY 環境変数で指定

運用上のファイル・フラグ
- data/stop_requested.flag
  - run_monitoring / run_execution が参照する「停止要求フラグ」。存在するとプロセスは順次停止します
- data/kill.flag
  - KillSwitch が書き込むファイル。ExecutionEngine を停止するためのフラグ（存在する場合は再書き込みしない）
- data/execution.pid
  - 実行中エンジンの PID を格納
- DB
  - DuckDB: data/kabusys.duckdb（デフォルト）
  - SQLite（monitoring）: data/monitoring.db（デフォルト）
  - SQLite（paper_trading）: data/paper_trading.db（paper_trading 時の分離 DB）

依存関係（主な Python パッケージ）
- duckdb
- psutil
- openai
- PyYAML（オプション: validate_config の YAML 検証）
- 標準ライブラリ: sqlite3, logging, argparse, datetime 等

ディレクトリ構成
----------------
（src/kabusys 以下の主要ファイル・ディレクトリ）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数・設定管理
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 起動前の設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py        (実装ファイルがある前提)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py        (実装ファイルがある前提)
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - execution/                 (ExecutionEngine 周りのモジュール群、ファクトリ等)
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/                (上記)
    - research/                  (上記)
    - portfolio/                 (上記)

（その他）
- .env.example（プロジェクトルートに存在する場合あり）
- config/*.yaml（システム設定ファイル。validate_config で検証対象）

運用上の注意・トラブルシューティング
----------------------------------
- ログが出力されない／ファイル作成に失敗する場合:
  - LOG_DIR 環境変数が正しいか、プロセスに書き込み権限があるか確認
- OpenAI 呼び出しエラー:
  - OPENAI_API_KEY が設定されているか（config_setup で設定可）
  - レート制限や接続断を考慮し、AI 関連はリトライとフォールバック実装が入っています
- データ鮮度／DuckDB クエリの問題:
  - DuckDB ファイルが存在しない・テーブルがない場合、research/ai の一部処理は失敗するのでデータ投入が必要
- 本番運用（KABUSYS_ENV=live）の際は
  - validate_config で警告を厳密にチェック
  - KILL_FLAG_CLEAR_ON_START は 0 を推奨（自動クリアは危険）
  - LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を確認

貢献・拡張
----------
- モジュールは比較的独立しており、AI 部分のモデル切り替え、ブローカークライアント追加、ポジションサイズ戦略の差し替えが容易です
- 新しい設定項目を追加する際は config.py と config_setup.py、.env.example、validate_config.py を更新してください

ライセンス
---------
（プロジェクトのライセンス情報をここに記載してください）

お問い合わせ
------------
（プロジェクト保守者や連絡先、Issue の立て方などをここに記載してください）

以上。README の内容はコードベース内のコメントと実装に基づいて作成しています。必要に応じて環境依存の運用手順（systemd ユニット、コンテナ化、CI 設定など）を追記してください。