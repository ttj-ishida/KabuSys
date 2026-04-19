# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-19

初回リリース。本バージョンでは、自動売買システム「KabuSys」のコア機能（設定管理、実行・監視起動スクリプト、ポートフォリオ構築ユーティリティ、運用支援ツールなど）を実装しました。

### 追加
- 全体
  - パッケージの初期バージョンを追加（__version__ = 0.1.0）。
  - DuckDB / SQLite を組み合わせたデータ処理基盤を導入（設定でパス指定可能）。
- 設定 & 環境
  - Settings クラスによる環境変数ベースの設定取得を実装。
  - .env 自動ロード機構を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env ファイルのパース機能を強化（export プレフィックス、クォート、エスケープ、インラインコメント対応）。
  - config_setup.py: 対話式設定ウィザードを追加（.env の作成・更新を支援）。
  - validate_config.py: 起動前チェック CLI を実装（必須環境変数、DB パス、YAML 検証、ライブ環境向けガード等）。--strict オプションで警告を失敗扱いに可能。
- 実行・監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV により paper_trading と本番を分離（paper_trading は専用 SQLite を使用）。
    - BrokerClientFactory を利用して環境に応じたブローカークライアントを生成（モック/本物の切替）。
    - Engine をスレッドで実行、停止フラグ（data/stop_requested.flag）や PID ファイルの取り扱いを実装。
    - risk_manager の初期設定（デフォルト閾値）を組み込んだ例を含む。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知・例外耐性（check_once の例外はログ出力して次ループへ）を実装。
- ロギング & プロセス管理
  - utils.logging_setup.setup_logging を追加
    - stdout の StreamHandler と日次ローテートする TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル解決順や LOG_DIR / LOG_LEVEL の取り扱いを明示。
  - utils.process_priority を追加
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。
    - CPU affinity を設定する set_cpu_affinity を実装（最初の N コアに固定する機能）。
    - 許容できない環境では警告を出して安全にフォールバック。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのソート／上位選定。
    - calc_equal_weights / calc_score_weights: 重み付け（score が全て 0 の場合は等配分にフォールバックし警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（当日売却予定銘柄を除外可）。"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）。未知レジームはフォールバック 1.0（警告）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に基づく発注株数算出。
    - aggregate cap（available_cash を超える場合のスケーリング）と lot_size（単元株）考慮の実装。
    - cost_buffer による手数料・スリッページの保守的見積りを実装。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL を判定。
    - デフォルト閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 200 ms）を定義。
    - --from / --to / --db オプションに対応。
- リサーチ（下地）
  - research.factor_research: 定量ファクター算出モジュールの骨組みを追加（モメンタム等の計算を実装予定）。DuckDB 接続を受ける設計。

### 変更
- .env の自動読み込み動作を明確化
  - OS 環境変数が優先され、.env.local は .env を上書きする。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- 実行時の DB 接続方針
  - 監視プロセスは KABUSYS_ENV に関係なく sqlite_path（本番監視 DB）を使用して監視テーブルを初期化するように設計。
  - 実行エンジンは paper_trading 環境なら paper_sqlite_path（分離された DB）を使用。

### 修正（設計上の強化・安全策）
- .env 解析の堅牢性向上（クォート内エスケープ、インラインコメントの扱い、不正行のスキップ）。
- Execution 起動前に監視テーブルの存在を保証する init_monitoring_db を実行（冪等）。
- calc_score_weights におけるゼロスコア全体時のフォールバックとログ警告。
- run_monitoring と run_execution に停止フラグ検知ロジックを追加（運用上の Kill Switch）。

### 既知の制限 / 注意事項
- research.factor_research はファイル末尾で未完（calc_momentum の実装が途中で切れている）。今後デイリーのファクター計算ロジックを完成させる予定。
- apply_sector_cap における価格欠損（price_map に値がない or 0 の場合）の扱いは現状不十分（TODO コメントあり）。前日終値等のフォールバック未実装。
- position_sizing は現状全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_size 対応を検討。
- set_process_priority / set_cpu_affinity は実行環境の権限に依存する（AccessDenied の場合は警告を出してスキップ）。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップする挙動となるため、運用環境ではログディレクトリ書き込み権限を確認すること。
- paper_verification_report は SQLite 内の時刻を UTC として期間フィルタを構築する（現状の実装では ISO8601 UTC 文字列を使用）。ローカルタイムでの扱いに注意。

---

今後の予定:
- factor_research の完成（ファクター計算アルゴリズムの実装・テスト）。
- 単体テストの拡充、CI ワークフローの追加。
- ブローカークライアントのインタフェース強化とモックの整備。
- 銘柄毎の単元・手数料モデルを取り込んだ position_sizing の拡張。

（備考）この CHANGELOG はソースコードの内容と内コメントから推測して作成しています。実際のコミット履歴やリリースノートとは差異があり得ます。