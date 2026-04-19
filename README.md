KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコードベースです。
本リポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクターリサーチ、
AI（ニュースセンチメント／レジーム判定）など、実運用／研究で必要な主要コンポーネントを含みます。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレードモードを切替可能（KABUSYS_ENV）。
  - ブローカークライアント抽象化（実ブローカー / MockBroker）。
  - 注文履歴・ポジション管理、リスク管理（最大比率・サーキットブレーカー等）。
- Monitoring（監視）
  - システムリソース監視（CPU/メモリ/ディスク）、データ鮮度チェック、約定や滞留注文の監視。
  - Kill Switch（閾値超過時に停止フラグを書き込み ExecutionEngine を停止）。
  - 監視ログは SQLite（monitoring.db）に永続化。
- Portfolio construction
  - 候補選定（スコア順）、等金額／スコア加重、リスクベースのポジションサイズ計算。
  - セクター上限適用・レジーム乗数（bull/neutral/bear）。
- Research（DuckDB を用いたファクター計算）
  - モメンタム / バリュー / ボラティリティ等のファクター計算。
  - 将来リターン・IC（Information Coefficient）計算、特徴量解析ユーティリティ。
- AI モジュール
  - ニュースを OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores に書き込み。
  - マクロニュース + ETF MA 乖離で市場レジームを判定し保存。
- ユーティリティ
  - 環境設定ウィザード（.env の対話式作成）、設定検証 CLI、ログ設定、プロセス優先度設定など。
- 運用補助
  - Paper Trading の検証レポート生成スクリプト（paper_verification_report）。

セットアップ
----------
1. Python（推奨: 3.10+）を用意。
2. 仮想環境を作成して有効化。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（requirements.txt がある場合はそれを利用）。
   - pip install duckdb psutil openai
   - 追加で YAML の検証を行う場合は PyYAML をインストール: pip install pyyaml
   ※ プロジェクトに requirements.txt が無い場合は上記ライブラリを参考にしてください。
4. .env を作成（推奨: 対話式ウィザードを利用）
   - python -m kabusys.config_setup
   - 作成後、設定を検証: python -m kabusys.validate_config
5. デフォルトのデータディレクトリを作成（必要に応じて）
   - mkdir -p data logs

重要な環境変数（主なもの）
- KABUSYS_ENV: execution モード ["development" | "paper_trading" | "live"]（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードでの約定挙動 ("instant"|"partial"|"never"|"reject")（デフォルト: "instant"）
- LOG_LEVEL / LOG_DIR: ログレベル / ログディレクトリ
- KILL_FLAG_CLEAR_ON_START: 本番での kill.flag 自動クリア (0/1)
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（起動・運用）
-------------------
- 環境ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）になる
- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 停止: プロジェクトルートの data/stop_requested.flag を作成すると監視ループが終了
- 発注エンジン（Execution）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、データは data/paper_trading.db に記録され本番 DB と分離される
  - 停止: data/stop_requested.flag を作成するとエンジンに停止シグナルが送られる（Kill Switch とは別に明示停止）
- Kill Switch（監視による自動停止）
  - 監視側が閾値を超えると data/kill.flag を書き込み、ExecutionEngine を停止するロジックがあります
  - KillSwitch の作成・削除は kill_switch モジュールで行います
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --db path/to/db --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

ログ
----
- ログは logs/<app_name>.log に日次ローテートで保存されます（デフォルト logs/）
- setup_logging() を全スクリプトが使用しており、標準出力（stdout）にも出力されます

プログラム API（簡単な紹介）
---------------------------
- kabusys.config.Settings / settings: 環境変数を型付きで取得するユーティリティ
- kabusys.monitoring.MonitoringEngine: 各 Monitor をまとめて実行するランナー
- kabusys.ai.score_news(conn, date, api_key=None): ニュースセンチメントを算出して ai_scores に書き込む
- kabusys.ai.regime_detector.score_regime(conn, date, api_key=None): 市場レジーム判定を行い market_regime に保存
- kabusys.research: calc_momentum / calc_volatility / calc_value 等のファクター計算
- kabusys.portfolio: 候補選定・重み計算・ポジションサイズ決定など

監視・管理関連ファイル
- 起動停止フラグ: data/stop_requested.flag（run_monitoring/run_execution が監視）
- Kill Switch フラグ: data/kill.flag（監視が書き込む）
- PID ファイル: data/execution.pid（ExecutionEngine で使用）

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py               — 環境変数/.env の自動読み込みと Settings クラス
- config_setup.py         — .env 対話式ウィザード
- validate_config.py      — 起動前の設定検証 CLI
- run_monitoring.py       — Monitoring のポーリングループ起動スクリプト
- run_execution.py        — ExecutionEngine 起動スクリプト

サブモジュール:
- ai/
  - news_nlp.py           — ニュースを OpenAI でスコアリングして ai_scores に保存
  - regime_detector.py    — ETF MA とマクロニュースでレジーム判定
- monitoring/
  - monitoring_db.py      — SQLite 監視 DB の初期化・CRUD（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py     — システムリソース・データ鮮度・プロセス監視
  - trade_monitor.py      — （省略したが注文関連監視ロジックが入る）
  - risk_monitor.py       — ドローダウン・ポジション上限監視
  - kill_switch.py        — Kill Switch（flag ファイル作成）
  - monitoring_engine.py  — 各 Monitor を束ねるランナー
  - alert_manager.py      — 通知（LINE など）管理（実装参照）
- execution/
  - execution_engine.py   — ExecutionEngine 本体（セッション管理）
  - order_manager.py      — 注文管理
  - order_repository.py   — 発注ログリポジトリ
  - broker_factory.py     — ブローカークライアント生成
  - reconciler.py         — 注文整合性チェック
  - risk_manager.py       — 実行時リスク管理
- portfolio/
  - portfolio_builder.py  — 候補選定・重み計算
  - position_sizing.py    — 株数決定・制約処理
  - risk_adjustment.py    — セクターキャップ・レジーム乗数
- research/
  - factor_research.py    — ファクター計算実装（DuckDB）
  - feature_exploration.py— 将来リターン・IC・統計要約
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- utils/
  - logging_setup.py      — ログ設定ユーティリティ
  - process_priority.py   — プロセス優先度 / CPU affinity 設定

注意事項 / 運用メモ
------------------
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup.py でも注意喚起あり）。
- Monitoring の DB 初期化・マイグレーションは monitoring_db.init_monitoring_db にて行われます。既存テーブルにカラムが足りない場合は自動で追加する処理があります。
- run_monitoring は MONITOR_POLL_INTERVAL（秒）でポーリング。値が不正な場合はデフォルト 60 秒にフォールバックします。
- ExecutionEngine は KABUSYS_ENV=paper_trading のとき専用の paper DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- OpenAI を利用する機能は API キーが必要です。API のエラーやレート制限はリトライ・フェイルセーフの実装あり（ログを確認してください）。
- 本番環境（KABUSYS_ENV=live）の設定は慎重に行ってください。validate_config に本番向けガード（LINE 設定確認や kill flag の自動クリア設定チェック）があります。

貢献 / 拡張
-----------
- ファクターの追加、ポートフォリオ割当アルゴリズムの改良、ブローカークライアント実装（実ブローカー接続）などが主要な拡張ポイントです。
- テスト追加（ユニットテスト／統合テスト）を強く推奨します（特に注文ロジック・リスク管理部分）。

ライセンス
----------
（リポジトリに明示されていない場合はプロジェクト管理者に確認してください）

以上。README に含めたい追加情報（例: 実行例ログ、詳細アーキテクチャ図、requirements.txt の内容等）があれば教えてください。必要に応じて追記します。