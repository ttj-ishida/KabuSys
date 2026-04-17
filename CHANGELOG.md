# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

注意: 以下の履歴はリポジトリ内のソースコードを解析して推測したものであり、実際のコミット単位や作業履歴ではありません。

## Unreleased

- なし（初回リリース相当の内容を 0.1.0 として記録）

## [0.1.0] - 2026-04-17

初期公開リリース。システム全体の基本コンポーネント（設定管理、起動スクリプト、ポートフォリオ構築、リスク調整、ポジションサイズ計算、リサーチ用ファクター計算、ユーティリティ、ペーパートレード検証ツールなど）を提供します。

### Added
- 全体
  - パッケージ初期バージョンを定義（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - DuckDB / SQLite を利用するデータアクセス基盤の導入（各モジュールで接続を受け渡して利用）。
  - 実運用・ペーパートレードを分離する設計を導入（Settings, run_execution など）。

- 起動 / 実行スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading SQLite を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント抽象化。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てと実行フローを提供。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止、PID ファイル管理。
  - システム監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - stop フラグ検出、例外時のロギング、リソースクローズ処理を実装。

- 設定管理
  - Settings クラス（src/kabusys/config.py）を追加し、環境変数ベースの設定取得を提供。
    - 多数のプロパティ（J-Quants / kabu API 周り、DB パス、監視しきい値、環境識別など）を定義。
    - 環境名・ログレベルのバリデーション、PAPER_FILL_MODE の検査、paper_sqlite_path 等を提供。
    - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - OS 環境変数の上書き保護（protected）を考慮した .env ロードロジック。
    - .env パースはクォート・エスケープ・コメントを考慮した堅牢な実装。

  - 対話式環境設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を対話的に支援。
    - デフォルト値、選択肢表示、シークレットマスク表示、保存前確認を提供。
    - .env のテンプレート出力（_write_env）。

  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - 本番環境（live）向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定 & 重み算出（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で候補抽出（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等重配分とスコア加重配分（スコア全 0 の場合は等重でフォールバックし警告）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションに基づくセクター上限フィルタ（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック挙動。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（"risk_based","equal","score"）に基づく株数決定、lot_size（単元）丸め、per-stock 上限・aggregate cap（available_cash）によるスケーリング、cost_buffer を考慮した保守的見積り。
    - risk_based: 許容リスク率・損切り率からベース株数を算出。
    - スケーリング時の切り捨て / 端数調整ロジック（残余キャッシュで lot 単位の追加配分）を実装。

- リサーチ / ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily 参照で計算。データ不足時は None を返す。
    - calc_volatility: ATR(20)、相対 ATR、20日平均売買代金、出来高比率などを計算（トゥルーレンジの NULL 伝播制御、ウィンドウ行数チェックを実装）。
    - 大域定数で計算窓幅・スキャン期間を指定（例: MA200, ATR_DAYS 等）。
    - DuckDB SQL を活用した高速集計設計。

- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - set_process_priority(level): Windows / POSIX (Linux, Darwin, FreeBSD) を吸収してプロセス優先度を設定。権限不足時は警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定コアにプロセスをピン留め。未サポートや権限不足時は警告してスキップ。
    - run_monitoring と run_execution の起動時に high 優先度へ設定する呼び出しを追加。

- モニタリング / 検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等の指標を集計して PASS/FAIL 判定を行う。
    - デフォルト閾値を定義（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）。
    - 日付フィルタ、DB パス引数（--db）と環境変数 PAPER_TRADING_SQLITE_PATH に対応。
    - P95 計算のユーティリティと、テーブルが存在しない場合のフェールバック処理を実装。

- その他
  - monitoring_db 初期化呼び出しを run_execution と run_monitoring に追加して監視テーブル存在を保証（冪等）。
  - 停止フラグ / キルフラグの利用に関するファイルパス管理を導入（data/stop_requested.flag、data/execution.pid 等）。
  - ロギングを適切に出力する箇所（起動環境ログ、ポーリング開始ログ、例外ログなど）を整備。

### Changed
- なし（初期リリースのため変更履歴は主に追加）

### Fixed
- なし（初期リリース相当。コード内にエラーハンドリングや権限不足時のフォールバック対応多数を導入）

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数の取り扱い:
  - .env ファイルはデフォルトで自動ロードされるが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - config_setup の出力メッセージで .env を Git にコミットしない旨を明記。
  - シークレット項目（API トークン・パスワード）はウィザード表示時にマスクして表示。

---

もし別ブランチや将来のリリースでの差分（例: volatility クエリの未完部分、銘柄毎の lot_size 拡張、外部 API への接続詳細など）まで正確に反映したい場合は、該当する差分やコミットログ（git）を提供してください。