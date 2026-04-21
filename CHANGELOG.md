CHANGELOG
=========

すべての重要な変更を「Keep a Changelog」スタイルで日本語にて記録します。  
この履歴はコードベースの内容から推測して作成しています。

フォーマット:
- 変更はセマンティックバージョニング準拠で記載しています。
- 各リリースに対して Added / Changed / Fixed / その他 を列挙しています。

Unreleased
----------
- なし

[0.1.0] - 2026-04-21
--------------------
Initial release — 基本機能の実装を含む初回リリースとして推測される変更点。

Added
- 全体
  - パッケージ初期版を追加。パッケージバージョンは __version__ = "0.1.0"。
  - 共通設定・環境変数管理モジュールを追加（kabusys.config）。
    - プロジェクトルートの自動検出（.git または pyproject.toml）。
    - .env / .env.local の自動読み込み（OS環境変数を保護）。
    - .env のパース機能（コメント、export プレフィックス、クォート/エスケープに対応）。
    - Settings クラスにより各種設定値（DBパス、API トークン、環境種別、監視閾値など）をプロパティとして提供。
- 起動スクリプト / ランタイム
  - 実行エンジン起動スクリプト（run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper DB（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成。
    - ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler の組み立てと実行ループ。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止機構。
  - 監視ループ起動スクリプト（run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず監視用 sqlite_path（本番用パス）を使用してデータを記録。
    - SystemMonitor.check_once の定期実行、例外ハンドリング、停止フラグ検知を実装。
    - 起動時にプロセス優先度を "high" に設定。
- 設定・検証ツール
  - config_setup.py：対話式 .env 作成ウィザードを追加（項目定義・既存 .env 読み込み・保存）。
  - validate_config.py：起動前の設定検証 CLI を追加（必須環境変数、DBパス、config/*.yaml の存在とパース、KABUSYS_ENV ガード等）。--strict オプションで警告を FAIL 扱いに可能。
- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup: 統一的ログ初期化ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（30 日保持）を設定。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップしてコンソールのみ）。
    - 既存ハンドラのクリーンアップ（重複設定防止）。
  - utils.process_priority: プロセス優先度設定（Windows / POSIX を吸収）と CPU affinity 設定ユーティリティを追加。
    - set_process_priority("high"|"normal"|"low")
    - set_cpu_affinity(n)
    - 権限不足や未対応 OS では安全にフォールバックして警告を出す実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定・重み計算関数を追加。
    - select_candidates（スコア降順、signal_rank を用いたタイブレーク）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重、全スコア0 の場合は等金額にフォールバック）
  - portfolio.risk_adjustment:
    - apply_sector_cap（セクター集中制限により候補除外）
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数）
  - portfolio.position_sizing:
    - calc_position_sizes（allocation_method: risk_based / equal / score をサポート）
    - 単元株丸め（lot_size）、max_position_pct、max_utilization、コストバッファ、aggregate cap（投下資金超過時のスケーリング）を実装
- 研究・分析ツール
  - research.factor_research: ファクター計算モジュールを追加（モメンタム、MA200乖離、ATR、流動性等の算出方針を実装）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を用いて計算（外部 API へはアクセスしない方針）。
- 運用ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）等を算出して判定（PASS/FAIL）。
    - デフォルト DB パス / コマンドライン引数で期間フィルタ指定可能。
    - P95 計算、日付フィルタ生成、欠損時の N/A 対応を実装。

Changed
- （初回リリース推測のため該当なし）

Fixed
- （初回リリース推測のため該当なし）

Notes / 推測上の動作・設計上の補足
- 設定関連は OS 環境変数を優先しつつ .env/.env.local を補完する設計。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを抑止可能。
- run_execution/run_monitoring は起動時にプロセス優先度を上げる設計。権限不足時は警告を出してフォールバック。
- Paper Trading モードでは発注等をモック・分離 DB に記録することで本番 DB への影響を避ける。
- ログは stdout に出力されるため、cron/Task Scheduler 等で起動した場合のリダイレクト運用を想定。
- 一部 TODO コメントあり（価格欠損時のフォールバックや個別 lot_size の将来的拡張など）。

今後の改善提案（コードからの推測）
- research.factor_research の完全実装とユニットテストの追加。
- ログローテーション失敗時や DB 作成権限がない場合の詳細な運用ドキュメント追記。
- position_sizing の銘柄別単元対応、price フォールバック（前日終値等）の実装。
- validate_config で YAML パース時の詳細なエラー箇所表示（行番号等）の強化。

参考: 主なコマンド例（コード内ドキュメントより）
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

もし、差分（コミット履歴）や実際のリリース日付がわかれば、より正確な CHANGELOG を作成できます。必要であればその情報を提供してください。