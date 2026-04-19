# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

なお以下の内容は提示されたコードベースから推測してまとめたもので、実際のコミット履歴ではありません。

### Unreleased
- （現在のコードベースに対する未リリースのメモはありません）

---

## [0.1.0] - 2026-04-19
初回リリース相当の機能セット。一通りの実行・監視・設定・ポートフォリオ構築・ユーティリティ群を備えた基本的な日本株自動売買フレームワーク。

### Added
- 基本パッケージ情報
  - kabusys パッケージ初期バージョンを定義（src/kabusys/__init__.py, __version__ = "0.1.0"）。

- 実行関連
  - Execution エントリスクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine 起動ロジックを実装。
    - KABUSYS_ENV=paper_trading 時に paper_trading 用の SQLite（data/paper_trading.db 等）を使用する分離設計。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の取り扱いを実装。
    - スレッドでエンジンを非同期実行・監視するループを実装。

- 監視関連
  - Monitoring エントリスクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを起動。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔の上書きが可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する（意図的な挙動）。
    - stop フラグ検知でループを優雅に終了する実装。

- 設定管理
  - Settings クラスを提供（src/kabusys/config.py）。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 必須/オプションの環境変数アクセスラッパー（J-Quants, kabuAPI, DB パス, 各種しきい値等）。
    - KABUSYS_ENV, LOG_LEVEL のバリデーションや convenience プロパティ（is_live/is_paper/is_dev）。
    - PAPER_FILL_MODE のバリデーションや paper_sqlite_path のサポート。

  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話的に .env を作成 / 更新するウィザード。
    - デフォルト値、選択肢、シークレット項目のマスク表示、保存確認を実装。
    - .env ファイルの読み書きロジックを提供。

  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数や KABUSYS_ENV、ログレベル、DB パスの存在チェック。
    - config/*.yaml の存在・YAML パース検査（PyYAML が未インストールの場合は警告）。
    - 本番環境向けの追加ガード（LINE 通知設定, KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を失敗扱いにできる。

- ユーティリティ
  - ロギングセットアップユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR 等の解決ルールを実装。
    - 既存ハンドラのクリア処理やファイルハンドラ作成失敗時のフォールバックを実装。

  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差異を吸収して set_process_priority("high"|"normal"|"low") を提供。
    - set_cpu_affinity(cpu_count) によるコア固定（利用環境に応じてスキップ可能）。
    - psutil の権限エラー等を寛容に扱う。

- データ基盤連携
  - DuckDB および SQLite の接続を各種スクリプトで使用（monitoring、execution、research など）。
  - 監視用 DB 初期化呼び出し（init_monitoring_db）を実行開始時に呼ぶ位置を統一。

- ポートフォリオ構築（純粋関数モジュール）
  - 選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順＋タイブレークで候補選定
    - calc_equal_weights / calc_score_weights: 重み計算（スコアが全て 0 の場合は等分にフォールバック）

  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中を検出して新規候補から除外（"unknown" は除外対象外）
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック

  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の配分方式をサポート
    - lot_size（単元）に合わせた丸め、per-stock 上限・aggregate cap（利用可能現金）によるスケーリング
    - cost_buffer を用いた手数料/スリッページ考慮、残差処理で lot 単位の追加配分ロジックを実装

  - パッケージエクスポート（src/kabusys/portfolio/__init__.py）を整備

- ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - システム稼働率、注文成功率、送信率、API レイテンシ（平均・最大・P95）の集計。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義・判定。
    - コマンドラインから期間指定（--from / --to）および DB パス指定（--db）をサポート。
    - データ欠損時の耐性（テーブル未存在時に OperationalError を捕捉して N/A 扱い）を実装。

- リサーチ（部分実装）
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity を想定した関数・定数を定義。
    - calc_momentum のヘッダ・設計方針を含む実装の先頭が存在（ファイルは提示コードで途中まで）。

### Changed
- なし（初回リリースのため明示的な「変更」はなし）

### Fixed
- なし（初期状態のため明示的な修正履歴はなし）

### Notes / その他
- 停止制御
  - 複数スクリプトで data/stop_requested.flag を用いた外部停止トリガーを採用。Execution と Monitoring の両方で検知ロジックが実装されている。

- セキュリティ / 運用
  - .env はウィザードで生成する際に「絶対に Git にコミットしないこと」を README 的に明記。機密値は対話時にマスク表示。
  - 本番運用（KABUSYS_ENV=live）時の注意点や通知設定不足に対する警告を validate_config で出す仕組みがある。

- エラー耐性
  - Logging / Process Priority / DB 接続等でのパーミッショントラブルやハンドラ作成失敗を許容し、フォールバックして稼働し続けるように実装されている。

---

今後の更新候補（推奨）
- research.factor_research の未完実装の完成とユニットテスト追加
- CLI 用の entry_points（setup.cfg/pyproject）整備
- 単体テスト（portfolio, position_sizing, risk_adjustment, config parser）の追加
- ドキュメント（使い方、運用手順、環境構築手順）の整備

もし特定ファイルの差分コミット単位でより詳細な CHANGELOG を作成したい場合、コミット履歴や変更の意図（どの変更をバージョンに含めたいか）を教えてください。