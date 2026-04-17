CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

※ リリース日はコードベースから推測した作成日を使用しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- パッケージ初期公開: KabuSys v0.1.0
  - 日本株向け自動売買システムの基礎モジュール群を追加。

- 設定管理
  - Settings クラスを追加し、環境変数経由で各種設定（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 等）を提供。
  - 自動 .env ロード機能を実装（プロジェクトルートに基づき .env, .env.local を読み込み、OS環境変数を保護）。
  - .env パーサを実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - KILL_FLAG_CLEAR_ON_START 等の運用用フラグを環境変数で制御可能。

- 設定支援 CLI / 検証
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援（シークレット項目は表示をマスク、書き込みテンプレートを生成）。
  - validate_config: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV、DBパス、config/*.yaml の存在／パース（PyYAML 未導入時は警告）や本番環境向けガードを検証。--strict オプションで警告も失敗扱いに。

- 実行 / 監視用スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper 専用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と完全分離。
    - エンジン用 PID ファイル管理、停止フラグ（data/stop_requested.flag）による制御、スレッドでの実行監視を実装。
    - 起動時に init_monitoring_db を呼び出し監視テーブルの存在を保証（冪等）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（意図的な運用仕様）。
    - 停止フラグ検知で安全にループを抜け、DB 接続をクローズする。

- モニタリング DB 初期化
  - init_monitoring_db（監視用テーブルを作成するユーティリティ）を組み込み、run 系スクリプトで利用。

- プロセス制御ユーティリティ
  - utils.process_priority に set_process_priority と set_cpu_affinity を追加。
    - Windows / POSIX（Linux/macOS/FreeBSD）差分を吸収して優先度（high/normal/low）や CPU affinity を設定。
    - 権限不足や未対応 OS・機能未実装時には警告ログを出力して安全にスキップ。

- ポートフォリオ構成（純粋関数群）
  - portfolio モジュールを追加:
    - portfolio_builder: select_candidates（スコア降順で上位 N 選択）、calc_equal_weights、calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
    - risk_adjustment: apply_sector_cap（既存保有を基にセクター集中を抑制して候補をフィルタ）、calc_regime_multiplier（レジームに応じた投下資金乗数、未知レジームはフォールバックで 1.0）。
    - position_sizing: calc_position_sizes（allocation_method="risk_based" | "equal" | "score" をサポート）。単元株丸め(lot_size)、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap（スケールダウン）アルゴリズムを実装。

- 研究（Factor 計算）
  - research.factor_research を追加:
    - calc_momentum: 1M/3M/6M リターンおよび 200 日移動平均乖離率を DuckDB の prices_daily テーブルから計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金や出来高比率等の指標を計算。
    - DuckDB 接続を受け取り SQL ＋ Python で計算する設計（外部 API へはアクセスしない）。

- Paper Trading 検証レポート
  - tools.paper_verification_report を追加:
    - paper_trading DB（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、P95 レイテンシ等の集計を行い、PASS/FAIL 判定を出力。
    - 閾値はソース内定数で定義（稼働率 99%、成功率 90% 等）。
    - --from / --to / --db 引数で期間および DB を指定可能。

Changed
- ロギングと初期化順序の設計
  - run 系スクリプトは起動直後にプロセス優先度を上げる（set_process_priority("high")）ようにして、重要処理の優先度を確保。

Fixed
- なし（初回公開）

Notes / その他
- セキュリティ/運用
  - .env ファイルは生成スクリプトの注意書きに従い Git にコミットしないことを明記。
  - validate_config は本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE トークン未設定警告や KILL_FLAG_CLEAR_ON_START の注意）を実装。

- 既知の制約 / TODO（コード中注記）
  - apply_sector_cap の price 欠損時の取り扱いや、position_sizing の将来的な lot_size の銘柄別対応など、拡張の余地を残す設計上の注記あり。
  - research.factor_research の SQL は営業日ベースの窓長を想定しており、データ欠損時は None を返す挙動をとる。

References
- RFC: Keep a Changelog — https://keepachangelog.com/en/1.0.0/

---