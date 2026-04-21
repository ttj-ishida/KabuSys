CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

フォーマット: 日本語
========================================

Unreleased
----------
（現時点の変更は未リリースです）

0.1.0 - 2026-04-21
-----------------
初回公開リリース。主要な追加・実装は以下のとおりです。

Added
- 基本コア & 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に paper_trading 専用 SQLite（data/paper_trading.db 等）を使用する分離設計。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - エンジンの PID 管理 (data/execution.pid) と停止フラグ (data/stop_requested.flag) による制御。
    - スレッド駆動で engine.run_session を実行し、停止フラグ検知で安全停止。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視 DB を一元化）。
    - 停止フラグファイルの検知、check_once 内例外の捕捉、KeyboardInterrupt のハンドリングを実装。

- 設定関連
  - config.py: 環境変数/.env 読み込みと Settings クラスを実装。
    - .env 自動読み込み (プロジェクトルートの .env、.env.local) を行う（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env のパース改良: export プレフィックス対応、クォート文字列のエスケープ対応、インラインコメント処理等に対応。
    - Settings に各種プロパティを実装（J-Quants トークン、kabu API、DuckDB/SQLite パス、paper_trading 用設定、監視閾値、環境判定等）。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START などの環境変数取り扱いを追加・検証。
  - config_setup.py: 対話式 .env 設定ウィザードを追加。
    - .env の初期作成・更新を対話式に支援。シークレット項目はマスク表示。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース確認（PyYAML 未インストール時はスキップ）等。
    - --strict オプションで警告を失敗扱いにするモードを実装。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（同点は signal_rank でブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバックし WARNING）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック。既存保有のセクターエクスポージャーに基づき新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear のマップ、未知レジームはフォールバック 1.0）。
  - portfolio.position_sizing
    - calc_position_sizes: 各銘柄の発注株数計算（allocation_method: risk_based / equal / score）。
      - 単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケーリング）を実装。
      - cost_buffer を考慮した保守的コスト見積り、残差処理により lot 単位で追加配分するアルゴリズムを実装。
      - 価格未取得時のスキップやログ出力を実装。

- ユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日分保持）をルートロガーに設定。
    - LOG_LEVEL/LOG_DIR の解決順と、ディレクトリ作成失敗時のフォールバック（ファイル出力無効）を実装。
  - utils.process_priority: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）間の差を吸収、権限不足等は警告でスキップ。

- モニタリング・DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run_* スクリプトから使用して監視テーブルの冪等初期化を保証（存在しない場合に作成）。

- tools
  - tools.paper_verification_report: Paper Trading 向け検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計。
    - PASS/FAIL 基準（稼働率 99% 以上、成立率 90% 以上、送信率 95% 以上、P95 レイテンシ <= 200 ms）を実装。
    - --from / --to / --db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数とも併用可能。

- research
  - research.factor_research: ファクター計算の骨組みを追加（モメンタム等の設計・定数定義、calc_momentum の実装開始）。
    - DuckDB の prices_daily/raw_financials を利用する設計方針を文書化。

Changed
- パッケージ初期化
  - __init__.py にてバージョンを "0.1.0" に設定し、主要サブパッケージ名を __all__ でエクスポート。

Fixed
- 環境変数パースと読み込みの堅牢性向上
  - export キーワード、クォート内のバックスラッシュエスケープ、インラインコメント処理等に対応。
  - .env 自動ロード時に OS 環境変数を保護するため protected set を導入。

- ロギング・ハンドラ設定の安全化
  - 既存ハンドラを flush/close した上で削除し、二重設定を防止。
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時にコンソール出力のみで継続するフォールバックを実装。

- process_priority のエラーハンドリング
  - 権限不足や未実装 API による例外をキャッチして警告にフォールバック。

Security
- なし（このリリースで特にセキュリティ修正は含まれていません）

Deprecated
- なし

Removed
- なし

Notes / Implementation details
- run_monitoring は監視用 DB として Settings.sqlite_path（"デフォルト: data/monitoring.db"）を常に使用します。これは Monitoring データを環境に依存せず一元化するための設計です。
- run_execution は paper_trading 時に paper_sqlite_path を使用して、本番 DB とは完全に隔離します（ペーパートレードの安全な再現性確保のため）。
- calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして警告を出すことで、分母ゼロによる問題を回避します。
- apply_sector_cap は "unknown" セクターを上限適用対象外とし、既知セクターのみで上限判定を行います（データ欠損時の過剰制限を避けるため）。
- .env 読み込みの自動化はプロジェクトルート検出に .git / pyproject.toml を使用するため、配布後も CWD に依存せずに動作します。

今後の TODO / 予定
- research.factor_research の関数群（Momentum / Value / Volatility / Liquidity）の完全実装。
- ブローカークライアントの詳細（MockBroker と実ブローカ間の抽象化）のテストとドキュメント整備。
- strategy / execution 周りの統合テストとエンドツーエンド検証スクリプト整備。
- 銘柄別単元情報（lot_size）を stocks マスタに持たせる拡張。

----------------------------------------
この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして使用する場合は、コミット履歴やリリース管理ポリシーに合わせて加筆・修正してください。