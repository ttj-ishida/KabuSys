# Changelog

すべての変更は Keep a Changelog の形式に従い記載します。  
ドキュメント整備・初期実装の記録として、実装内容はコードベースから推測して要約しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- なし

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ構成を実装
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 設定管理
  - .env ファイルまたは環境変数から設定を読み込む `kabusys.config.Settings` を実装。
  - プロジェクトルートの自動検出機能: `.git` または `pyproject.toml` を起点に探索し、自動で .env を読み込む（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
  - .env パーサーは以下をサポート:
    - `export KEY=val` 形式
    - シングル/ダブルクォート + バックスラッシュエスケープ処理
    - コメント扱いのルール（クォートなしの inline コメントは直前が空白/タブの場合に認識）
  - 必須項目取得用ヘルパー `_require()` を提供（未設定時は ValueError）。

- 設定ウィザード CLI
  - `kabusys.config_setup`:
    - インタラクティブな .env 作成 / 更新ウィザードを提供。
    - 項目: KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LINE_*（任意）など。
    - シークレット入力のマスク表示、既存値の再利用、保存確認、.env ファイル書き出し機能を実装。

- 設定検証 CLI
  - `kabusys.validate_config`:
    - .env および config/*.yaml（存在すれば）の基本的な妥当性チェックを実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、PyYAML があれば YAML のパース検証を実施。
    - `--strict` オプションで警告をエラー扱いにできる。

- 実行スクリプト
  - `run_execution.py`:
    - ExecutionEngine を起動する CLI スクリプトを実装。
    - プロセス優先度を "high" に設定（`kabusys.utils.process_priority.set_process_priority` を利用）。
    - DB 接続:
      - 本番/開発: `SQLITE_PATH`（デフォルト: data/monitoring.db）
      - Paper Trading 時は専用 DB (`PAPER_TRADING_SQLITE_PATH` または default data/paper_trading.db) を使用して本番 DB と分離。
    - ブローカークライアント生成（`BrokerClientFactory.create(settings)`、paper_trading の場合は MockBrokerClient 利用想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）を監視し、安全に停止。PID ファイル管理（data/execution.pid）に対応。

  - `run_monitoring.py`:
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（<=0 や非整数）の場合は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用する実装（監視用 DB 初期化を保証する `init_monitoring_db` 呼び出し）。
    - 停止フラグ（data/stop_requested.flag）でループを抜けて終了。
    - KeyboardInterrupt を捕捉して適切に終了処理を行う。

- 監視 DB 初期化
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を利用して、monitoring 用テーブルが存在することを保証（冪等）。

- ロギング
  - `kabusys.utils.logging_setup.setup_logging` を実装:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定。
    - ディレクトリ自動作成、ファイルローテーション（30日保持）。
    - ログレベル解決順: 関数引数 > 環境変数 `LOG_LEVEL` > デフォルト "INFO"。
    - ログ出力先ディレクトリは引数 > 環境変数 `LOG_DIR` > デフォルト "logs/"。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority`:
    - Windows / POSIX の差分を吸収してプロセス優先度を設定（high/normal/low）。
    - CPU affinity 設定機能 `set_cpu_affinity` を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築モジュール（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`（score 降順、タイブレークに signal_rank）。
    - 重み算出: 等金額 `calc_equal_weights`、スコア加重 `calc_score_weights`（全スコアが 0 の場合は等配分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap`（既存保有を考慮して新規候補を除外。unknown セクターは制限対象外）。
    - レジーム乗数 `calc_regime_multiplier`（"bull"=1.0, "neutral"=0.7, "bear"=0.3。未知レジームは警告して 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - ポジションサイズ算出 `calc_position_sizes`（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - risk_based: 損切り幅・risk_pct を用いた理論株数計算、単元株（lot_size）で丸め。
    - aggregate cap（available_cash を超える場合）のスケーリング処理を実装。スケーリング後は残余キャッシュを用いて端数分を lot_size 単位で再配分（再現性のため tie-breaker に code を使用）。
    - max_position_pct（1銘柄上限）や cost_buffer（手数料・スリッページ見積り）に対応。
    - 入力が不十分な銘柄（価格欠損など）はスキップ。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research`:
    - モメンタム（1M/3M/6M）、MA200乖離、ATR（20日）、出来高/流動性等のファクター計算モジュールを設計。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計方針を明示。
    - （注）ファイル末尾で実装途中の痕跡（未完の行）があり、一部未実装の可能性あり。

- ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用の検証レポート生成スクリプトを実装。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg / max / P95）
    - デフォルト DB: `PAPER_TRADING_SQLITE_PATH` 環境変数または data/paper_trading.db。
    - 判定基準（デフォルト閾値）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - レポートは標準出力に整形して表示。期間フィルタ（--from / --to）対応。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- （特に無し）

## 注意事項 / 既知の制約・ TODO
- research/factor_research.py の実装が途中で切れている箇所（ファイル末尾に未完の行）があります。ファクター計算の完全実装は今後の作業が必要です。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合の扱いに TODO コメントあり。将来的に前日終値や取得原価を用いるフォールバックの検討が示されている。
  - lot_size は現状グローバル固定（関数引数）で、将来的に銘柄別単元対応を想定した拡張予定あり。
- .env 自動ロード機能は便利だが、OS 環境変数を保護するため `.env.local` の上書き時にも OS 環境変数は保護される実装になっている点に注意（protected set を使用）。
- `run_monitoring` は「監視は環境にかかわらず本番 sqlite_path を使用する」実装になっています。意図的な仕様だが運用で注意が必要です。
- process priority / cpu affinity の設定は権限不足や未対応 OS の場合は警告を出してスキップする設計。
- 実行スクリプトは停止フラグ（data/stop_requested.flag）および PID ファイルを用いてプロセス管理を行うが、運用手順（フラグ作成／削除）を運用ドキュメントに明記することを推奨します。

---

この CHANGELOG はコード内容から推測して記載しています。実際のリリースノートには追加の運用上の注意、インストール手順、移行手順、既知のバグ修正履歴などを含めることを推奨します。