CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 変更はセマンティックに分類（Added / Changed / Fixed / Security 等）
- 各リリースには日付を付与

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-24
-----------------

Added
- 初期リリース。KabuSys のコア機能を多数追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用（設定: PAPER_TRADING_SQLITE_PATH または Settings.paper_sqlite_path）。
    - BrokerClientFactory を用いて環境に応じたブローカークライアント（Mock を含む）を生成。
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag によるグレースフルな停止をサポート。
    - 実行中の PID を data/execution.pid に保存する仕組み（pid_file パス設定）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番用の sqlite_path を使用（監視データは一元化）。
    - data/stop_requested.flag による停止検知。
- 設定・環境管理
  - config.py: 環境変数の集中管理クラス Settings を追加。
    - デフォルトパス: DUCKDB_PATH=data/kabusys.duckdb、SQLITE_PATH=data/monitoring.db、PAPER_TRADING_SQLITE_PATH=data/paper_trading.db など。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - KABUSYS_ENV, LOG_LEVEL の検証ロジックを提供。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索し .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。.env.local は .env をオーバーライド。
    - settings インスタンスをモジュールレベルでエクスポート。
  - config_setup.py: 対話式 .env ウィザードを追加。
    - 主要な環境設定項目を対話的に入力・保存できる (.env 出力)。機密値はマスク表示。
    - 既存 .env の読み込み・再利用、エクスポート形式に対応。
  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML があればパースを実行）。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日分保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数による優先順位で設定解決。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度設定・CPU affinity ユーティリティを追加。
    - Windows/Linux/macOS を吸収し、"high" / "normal" / "low" の抽象レベルで優先度設定。
    - cpu_affinity を最初の N コアに固定する機能を提供（権限不足時は警告でスキップ）。
    - psutil を利用し、例外や未対応 OS を安全にハンドリング。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順・タイブレークに signal_rank を利用してトップ N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用し、既存保有と売却予定銘柄を考慮して候補を除外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に基づく投下資金乗数（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告の上 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算を実装。
    - 単元 (lot_size) 切り上げ/切り下げロジック、per-position と aggregate cap（available_cash）を尊重するスケーリング、cost_buffer を使った保守的コスト見積り、残差に基づく追加配分ロジックを実装。
- 研究モジュール
  - research/factor_research.py: DuckDB を使ったファクター計算基盤を追加（モメンタム / MA200 dev / ATR / 出来高指標 等を実装予定の基礎）。
- ツール
  - tools/paper_verification_report.py: ペーパートレード結果検証レポート生成ツールを追加。
    - CLI: --from / --to / --db オプションをサポート。
    - 指標: 稼働率（uptime, system_status テーブル）、注文成功率・送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（avg/max/P95）。
    - デフォルトの合否基準: upt >= 99.0%、fill_rate >= 90.0%、send_rate >= 95.0%、P95 latency <= 200 ms。
    - P95 の計算はサンプル値のソートとパーセンタイル算出（空データは N/A）。
- その他
  - __init__.py によりパッケージバージョン __version__ = "0.1.0" を定義。

Changed
- 初期リリースにおける設計仕様をコード化:
  - 監視は本番監視 DB を使用する旨を明確化（run_monitoring.py）。
  - ExecutionEngine は paper_trading の際 DB を完全分離する仕様（run_execution.py）。
  - .env の自動読み込み順序を明確化（OS 環境 > .env.local > .env）、.env.local はオーバーライド可能。

Fixed
- （リリース時点で既知のバグ修正は特に無し。初期実装部分は例外処理とフォールバックを多めに実装し安全性を確保。）

Notes / Implementation details
- .env パーサは以下をサポート:
  - export KEY=val 形式の行を扱える。
  - シングル／ダブルクォート内のバックスラッシュエスケープを解釈。
  - クォートなし値では '#' がコメント開始（直前がスペース/タブ の場合）として扱われる。
  - 読み込み時は既存 OS 環境変数を保護するため protected セットを利用。
- ログ設定は既にハンドラが設定されている場合は古いハンドラを flush/close のうえ削除し再設定することで二重設定を防止。
- process_priority と logging_setup は権限不足や OS 非対応時に警告を出して安全にスキップする設計。
- validate_config は PyYAML 未インストール時に YAML 内容検証をスキップし警告を出す。
- ExecutionEngine の RiskManager は broker.get_available_cash() を初期ポートフォリオ値として利用する設計（現物キャッシュ連動）。

今後の予定（例）
- factor_research の完全実装（Value / Volatility / Liquidity 指標の SQL 実装）。
- Strategy/Execution の統合テスト、paper_trading シミュレーション精度向上。
- 個別銘柄毎の lot_size サポート（stocks マスタ導入）。
- ログフォーマットや監視メトリクスの拡張（外部監視統合、Prometheus 等）。

-----