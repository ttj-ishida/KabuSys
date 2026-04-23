CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。
フォーマットの目的は履歴を分かりやすく保つことです。

[Unreleased]
-------------

- なし（開発中の変更はここに記載します）

[0.1.0] - 2026-04-23
-------------------

Added
- パッケージ初回公開: KabuSys v0.1.0
  - 日本株自動売買システムの基盤モジュール群を追加。
- 実行 / 監視関連スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV による paper_trading モード対応:
      - paper_trading の場合は paper_sqlite_path（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成（MockBrokerClient を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をバックグラウンドスレッドで起動。
    - 停止制御: data/stop_requested.flag および PID ファイル管理（data/execution.pid）。
    - RiskManager にデフォルトの RiskConfig を設定（max_position_pct, max_utilization 等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
    - 監視用 DB は環境に関わらず production の sqlite_path を使用して監視テーブルを保証。
    - 停止フラグ（data/stop_requested.flag）検知で優雅に終了。例外時はログを出して次ポーリングへ継続。
- 設定管理
  - config.py
    - 環境変数 / .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。
    - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env / .env.local の読み込みロジック（.env.local は上書き、OS 環境変数は保護）。
    - Settings クラスを提供: 各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL, 監視しきい値など）。
    - PAPER_FILL_MODE の検証（"instant", "partial", "never", "reject" のみ許容）。
- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を追加。
    - 秘密値はマスク表示、選択肢・デフォルト提示、最終確認後に .env を書き込み。
  - validate_config.py
    - 起動前チェックツールを追加 (.env と config/*.yaml の整合性チェック)。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL 検証、DB パスと YAML ファイル存在確認、live 環境時のガード（LINE 設定や Kill Switch の注意喚起）。
    - --strict モードで警告を FAIL 扱いにできる。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを提供。
    - LOG_DIR / LOG_LEVEL の環境変数解決、既存ハンドラのクリア、ファイルハンドラ作成失敗時のフォールバックを実装。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する set_process_priority を実装。
    - CPU affinity を設定する set_cpu_affinity を実装（psutil を使用、例外は警告にフォールバック）。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等分配にフォールバックして警告ログを出力。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を実装（当日売却予定を除外可能）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear、未知レジームはフォールバック）。
    - apply_sector_cap 内に価格欠損時の取り扱いについての TODO コメントを記載。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（risk_based / equal / score の allocation_method）。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した算出と aggregate cap によるスケーリングを実装。
    - スケーリング時の端数配分アルゴリズム（fractional remainder を基に lot_size 単位で追加）を実装。
- リサーチ / ファクター計算（骨格）
  - research/factor_research.py
    - モメンタム・ボラティリティ等の計算方針と定数を実装（calc_momentum の実装開始を含む）。DuckDB を入力として想定。
    - 設計方針として DuckDB 上の prices_daily / raw_financials のみ参照する点を明記。
    - （注）モジュール末尾で calc_momentum の実装が途中で切れていることをコメントとして明記。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出して PASS/FAIL を判定するロジックを実装。
    - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。
    - 判定閾値を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）。
- パッケージ初期化
  - __init__.py に __version__ = "0.1.0" を追加し、主要サブパッケージを __all__ に宣言。

Changed
- 新規リリースのため多数のモジュールを初期配置（詳細は Added を参照）。

Fixed
- なし（初回リリース）。

Security
- 環境変数の .env を Git に決してコミットしない旨を config_setup のヘッダに明記。

Notes / Known issues
- research/factor_research.py の calc_momentum 実装が途中で切れている（未完）。今後のリリースで完成予定。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0 等）した場合にエクスポージャー評価が過少見積りされる可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討。
- .env 自動ロードはプロジェクトルートが検出できない場合スキップされる点に注意（配布後の挙動を考慮）。
- process_priority / set_cpu_affinity は権限不足や未対応 OS では警告にフォールバックする（安全設計）。
- run_monitoring は監視 DB に対して常に production sqlite_path を使用する（環境に依存しない仕様）。

開発者向けメモ
- CLI: validate_config / config_setup / tools.paper_verification_report はそれぞれ python -m kabusys.validate_config 等で実行可能。
- ログ: setup_logging() を各起動スクリプト最初に呼ぶことで stdout と日次ローテーションファイルへの統一的な出力が得られる。
- 停止制御: data/stop_requested.flag および data/execution.pid を使った簡易的なデーモン制御を採用。

--- 

今後の予定（例）
- factor_research の完成とテスト追加
- テストカバレッジ向上（ユニットテスト、CI）
- price フォールバックロジックの実装（apply_sector_cap の TODO 対応）
- ExecutionEngine / SystemMonitor のさらなる堅牢化とモニタリング指標拡充

------------------------------------------------------------
この CHANGELOG はソースコメント・実装内容から推測して作成しています。実際のコミット履歴に基づく厳密な変更履歴が必要な場合は Git 履歴の整備を推奨します。