CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 基本アプリケーション構成
  - パッケージ初版をリリース（バージョン 0.1.0）。
  - モジュール群を追加: config, config_setup, validate_config, run_execution, run_monitoring, portfolio, research, utils, tools 等。

- 設定管理
  - Settings クラスを実装。環境変数経由で各種設定（J-Quants トークン、kabu API、DB パス、各種閾値など）を取得する。
  - 自動 .env 読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントルールを考慮）。

- 設定ウィザード CLI
  - config_setup: 対話式ウィザードで .env の初期作成・更新が可能。
  - 秘密情報は表示時にマスク、確認後に .env を安全に書き出し（書き込みテンプレートを含む）。
  - デフォルト値や選択肢をサポート。

- 設定検証 CLI
  - validate_config: 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証を実行。
  - --strict モードで警告も失敗扱いにできる。
  - 本番用の注意喚起（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定など）を実装。

- 実行 / 監視ランナー
  - run_execution: ExecutionEngine を起動するエントリポイントを実装。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ検知で安全に停止。
    - Execution 用 PID ファイル出力の取り扱い。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視データベース初期化（init_monitoring_db）を行い、duckdb と sqlite を接続して監視を行う。
    - 停止フラグファイル検知でループを終了。

- モニタリング DB 初期化
  - init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等に実行可能）。

- ポートフォリオ構築ロジック（純粋関数）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights, calc_score_weights（スコア合計が 0 の場合のフォールバックで等金額配分）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超える既存保有がある場合に該当セクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear）を返却。未知レジームは警告して 1.0 にフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の割付方式を実装。lot_size（単元株）で丸め、max_position_pct / max_utilization を考慮。
    - cost_buffer を加味した aggregate cap スケーリング、スケールダウン時の端数処理（残差に基づく追加配分）を実装。
    - 価格欠損時のスキップやログ出力を追加。

- リサーチ / ファクター計算
  - research.factor_research:
    - DuckDB 接続を受け、prices_daily / raw_financials を用いてモメンタム（1M/3M/6M、MA200乖離）やボラティリティ（ATR20 等）、流動性指標を計算する関数を実装。
    - データ不足時は None を返す設計。

- ユーティリティ
  - utils.process_priority:
    - Windows / POSIX（Linux, macOS, FreeBSD）両対応でプロセス優先度設定をサポート。権限不足や未実装要素は警告してスキップ。
    - set_cpu_affinity を実装（最初の N コアにプロセスをピン留め）。不許可時は警告。

- ツール
  - tools.paper_verification_report:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポートを標準出力に出力する CLI を実装。
    - 閾値判定（PASS/FAIL）を組み込み、データがない場合は N/A 表示。

Changed
- 監視用 DB の扱い
  - run_monitoring は KABUSYS_ENV に依らず「本番 sqlite_path」を使用するよう明示（監視は環境に依存しない設計）。
- 起動時のプロセス優先度
  - run_execution/run_monitoring の起動時に最初に set_process_priority("high") を呼び出すように統一。

Fixed
- ロバストネス向上
  - MONITOR_POLL_INTERVAL の値検証を追加。不正な整数や 0 以下が設定された場合にログ警告を出しデフォルトにフォールバックすることで time.sleep の ValueError を防止。
  - paper_verification_report で対象 DB が存在しない場合にエラーをわかりやすく表示して処理を中断するよう修正。
  - 集計系クエリの結果が NULL / 0 の場合に None や N/A を適切に扱うように変更（ゼロ除算や不適切な表示を回避）。
  - init_monitoring_db 呼び出しを複数箇所から行っても問題ない（冪等性の仮定）。

Known issues / TODO
- apply_sector_cap 内の価格欠損（price が 0.0 の場合）によりエクスポージャーが過少見積りされセクター除外が外れる可能性がある旨を TODO コメントで記載。将来的に前日終値や取得原価などのフォールバック価格を導入予定。
- position_sizing は現状で全銘柄共通の lot_size（デフォルト 100）を想定。将来的には銘柄別 lot_map に対応する予定（TODO コメントあり）。
- research.factor_research は prices_daily/raw_financials に依存する設計。外部データ欠落時の挙動は現状 None を返す仕様。

Security
- なし（このリリースで特別なセキュリティ修正は含まれません）。ただし .env ファイルは絶対に Git にコミットしないことを .env テンプレートに明記。

Notes
- 本 CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴や意図した変更点と差異がある可能性があります。必要であれば実際の Git 履歴・リリースノートに基づく修正を行ってください。