# Changelog

すべての重要な変更は Keep a Changelog 規約に従って記載します。  
<https://keepachangelog.com/ja/1.0.0/> を参照してください。

注意: この CHANGELOG は提示されたソースコードの内容から機能・動作を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース

### Added
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。
  - モジュール公開 API を __all__ で整備。

- 設定・初期化
  - Settings クラスを導入し、環境変数ベースで各種設定を取得（J-Quants / kabu API / DB パス /監視閾値 等）。
  - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を読み込む。OS 環境変数は保護）。
  - .env パースの強化:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント処理などをサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加（項目定義、既存 .env 読み込み、シークレットマスク、保存確認を含む）。

- 設定検証
  - validate_config CLI を追加。必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスや config/*.yaml の存在チェック、PyYAML の有無に応じた YAML パース検証、本番環境（live）向けのガードチェックを実装。
  - --strict オプションで警告を FAIL 扱いにできる。

- 実行（Execution）ランナー
  - run_execution 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager のデフォルト設定（max_position_pct 等）と initial_portfolio_value を broker.get_available_cash() から取得。
    - エンジンはスレッドで実行し、data/stop_requested.flag の検知で停止、PID ファイルパスをサポート。

- 監視（Monitoring）ランナー
  - run_monitoring 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する仕様を明記。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - data/stop_requested.flag を監視してループを終了。例外時はログ出力して次のポーリングへ継続。

- モニタリング DB 初期化
  - init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等な初期化）。

- ユーティリティ
  - process_priority ユーティリティを追加:
    - set_process_priority(level) — Windows と POSIX を吸収してプロセス優先度 (high/normal/low) を設定。権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) — プロセスを最初の N コアにピン留め（未対応例/権限不足は警告でスキップ）。
  - 複数 OS を考慮した堅牢な実装（psutil 使用、例外ハンドリング）。

- ポートフォリオ構築（Portfolio）
  - portfolio_builder:
    - select_candidates — BUY シグナルをスコア降順でソートして上位 N 件を返す（タイブレーク: signal_rank）。
    - calc_equal_weights — 等分配を返す。
    - calc_score_weights — スコア比率で重みを計算。全スコアが 0 の場合は等分配にフォールバックし警告を出力。
  - risk_adjustment:
    - apply_sector_cap — 既存保有のセクター別時価を計算し、1 セクター上限を超過している場合は当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。sell_codes により当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier — 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 にフォールバック（警告を出力）。
  - position_sizing:
    - calc_position_sizes — allocation_method ("risk_based" / "equal" / "score") に対応した発注株数算出。lot_size（単元）で丸め、max_position_pct / max_utilization / cost_buffer に基づく per-position および aggregate 上限処理、投下資金が available_cash を超える場合のスケールダウン（端数処理は fractional remainder に基づく再配分）を実装。
    - 価格欠損時のスキップやログ出力などの堅牢性処理を含む。

- 研究用ファクター計算（Research）
  - factor_research モジュールを追加（DuckDB 接続を受け取り SQL ベースで計算）。
    - calc_momentum — mom_1m / mom_3m / mom_6m / ma200_dev を計算。必要行数不足時は None を返す。
    - calc_volatility — ATR, 相対 ATR, 20日平均売買代金, 出来高比率 等を計算（設計上、prices_daily テーブルのみ参照）。
    - 各種計算窓（1M/3M/6M/MA200/ATR 等）の定数を明記し、スキャン範囲のバッファを考慮。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH デフォルト: data/paper_trading.db）に対する検証レポートを生成。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシ 等を算出し、しきい値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を出力。
    - 日付フィルタ (--from / --to) / --db オプションをサポート。DB がない場合はエラー表示。
    - SQL の実行失敗（テーブル未作成等）に備えた例外ハンドリング。

### Changed
- 設計方針として、ポートフォリオ計算やファクター計算は「DB 参照なし」ではなく DuckDB や引数で渡されたマップだけを利用する点を文書化（副作用なしの純粋関数群として実装）。

### Fixed
- （初版のため既知の修正履歴なし。コード内に防御的実装（例外ハンドリング、値チェック、ログ出力）を多数含むことで堅牢性を確保。）

### Security
- .env ファイルは生成時に Git へのコミット禁止を明記（config_setup のテンプレートに注意文を追加）。

---

注記:
- ここに記載した機能や挙動は提示されたソースコードから推測したものです。実際のランタイム挙動や他ファイル（例: monitoring_db, SystemMonitor, ExecutionEngine, BrokerClientFactory 等）の実装詳細に依存する部分は省略あるいは要約しています。