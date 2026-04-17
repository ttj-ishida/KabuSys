# Keep a Changelog
すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
安定したリリースはセマンティックバージョニングに従います。

## Unreleased
（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-17
初回リリース。

### Added
- 基本パッケージとバージョン情報を追加
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`

- 設定・環境変数管理
  - Settings クラスを実装（`src/kabusys/config.py`）
    - J-Quants / kabuステーション / LINE / DBパス 等のプロパティを提供
    - env 値の検証（`KABUSYS_ENV`, `LOG_LEVEL` 等）
    - Paper Trading 用の設定（`paper_sqlite_path`, `paper_fill_mode`）
    - PID / Kill Flag /閾値系（CPU/MEM/DISK）プロパティ
  - 自動 .env ロード機能を実装
    - プロジェクトルート（`.git` または `pyproject.toml`）を基準に `.env` / `.env.local` を読み込む
    - OS 環境変数を上書きしない保護機構を持つ
    - 自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート
  - .env パースの強化
    - export 形式、クォートされた値、インラインコメント（一定条件下）に対応

- 対話式設定ウィザード CLI
  - `src/kabusys/config_setup.py`
    - .env の初期作成・更新を支援するウィザード
    - 各種設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）
    - 保存時にテンプレートヘッダを付与（.env を誤ってコミットしないよう注意喚起）

- 設定検証ツール（CLI）
  - `src/kabusys/validate_config.py`
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認
    - DB パスの親ディレクトリ存在チェック
    - `config/*.yaml` の存在確認および PyYAML があればパース検証
    - 本番環境（live）向けの追加ガード（LINE 設定の有無、KILL_FLAG_CLEAR_ON_START の危険性）
    - `--strict` オプションで警告を失敗扱いにする機能

- 実行系エントリポイント
  - ExecutionEngine 起動スクリプト `src/kabusys/run_execution.py`
    - 起動時にプロセス優先度を設定
    - Paper Trading 環境では MockBrokerClient を使用し、Paper 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`）を利用して本番 DB と完全分離
    - duckdb 接続の初期化
    - BrokerClientFactory によるブローカークライアント生成
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の取り扱い
  - 監視ループ起動スクリプト `src/kabusys/run_monitoring.py`
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は環境に関わらず本番の sqlite_path を使用して監視データを記録
    - SystemMonitor を用いた単回チェック（check_once）のループ実装と例外耐性

- 監視 DB 初期化ユーティリティ
  - `init_monitoring_db` を呼び出して監視用テーブルの存在を保証（冪等）

- 実運用向けユーティリティ
  - プロセス優先度 / CPU affinity のユーティリティ `src/kabusys/utils/process_priority.py`
    - Windows と POSIX（Linux / macOS / FreeBSD）で差分を吸収
    - 優先度レベル: "high" / "normal" / "low"
    - CPU コア数に固定する API を提供（例外は警告でスキップ）

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナル選定（score 降順、タイブレークに signal_rank）、等配分・スコア配分の重み計算
  - `src/kabusys/portfolio/position_sizing.py`
    - allocation_method（risk_based / equal / score）に基づく発注株数計算
    - 単元株丸め、1銘柄上限、aggregate cap（利用可能現金に合わせてスケールダウン）、cost_buffer を考慮した保守的見積り
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限（apply_sector_cap）
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）
  - モジュールエクスポートを整備（`src/kabusys/portfolio/__init__.py`）

- リサーチ / ファクター計算
  - `src/kabusys/research/factor_research.py`
    - DuckDB 接続を使ったモメンタム / ボラティリティ等のファクター計算関数（例: calc_momentum, calc_volatility）
    - 200 日移動平均、1/3/6 ヶ月リターン、ATR、出来高/売買代金等を計算

- Paper Trading 検証レポート
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading の SQLite DB（デフォルト: data/paper_trading.db）から各種指標を集計してレポート出力
    - 指標:
      - 稼働率（uptime）
      - 注文成功率（fill rate）・送信率（send rate）
      - リスク却下数（risk_logs）
      - 平均 / 最大 / P95 レイテンシ（latency_ms）
    - P95 計算、期間フィルタ（--from / --to）、閾値による PASS/FAIL 判定
    - デフォルト閾値（例: 稼働率 >= 99%、P95 <= 200ms 等）を設定

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサーの堅牢性向上
  - シングル/ダブルクォート中のバックスラッシュエスケープと対応する閉じクォート検出に対応
  - export 形式やインラインコメントの扱いを改善

### Security
- .env ファイルは絶対に Git にコミットしないようドキュメントおよびウィザードに注意書きを追加

---

注記:
- 上記はソースコードの機能と実装から推測した初期リリースの主な変更点・機能一覧です。各モジュールはさらに詳細な内部仕様（Engine の振る舞い、RiskManager のパラメータ等）を含みます。必要であれば各コンポーネントごとの更に細かい変更ログ（関数リスト・引数説明・既知の制限事項）を作成します。