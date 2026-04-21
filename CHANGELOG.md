# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-21
初回リリース

### Added
- 全体
  - 初期リリース。自動売買システム KabuSys のコアユーティリティ・ランナー・ポートフォリオ構築ロジック・確認ツール群を実装。
  - パッケージバージョンを `__version__ = "0.1.0"` に設定（src/kabusys/__init__.py）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite DB を使用し（data/paper_trading.db がデフォルト）、MockBrokerClient を利用できるよう設計。
    - エンジンの PID 管理（data/execution.pid）や停止フラグ（data/stop_requested.flag）をサポート。停止フラグ検知でエンジンの停止を行う。
  - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ存在時にループを終了。
    - 監視は環境に依らず本番用の sqlite_path を使用する設計。

- 設定管理・補助 CLI
  - 設定読み込み・管理モジュールを追加（src/kabusys/config.py）。
    - .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml で検出）。`.env` と `.env.local` の優先順をサポート。
    - 複雑な .env パース（export 形式、クォート中のエスケープ、インラインコメント取り扱い）に対応。
    - 設定アクセス用 `Settings` クラスを提供（多くのプロパティ: DB パス、KABUSYS_ENV、LOG_LEVEL、paper_fill_mode など）。
    - `paper_fill_mode` の妥当性検査（"instant"|"partial"|"never"|"reject"）を実装。
    - `paper_sqlite_path`、`pid_file_path`、閾値設定（CPU/MEM/DISK）等のプロパティを実装。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - .env および config/*.yaml の存在・基本的妥当性を検査。
    - PyYAML が無ければ YAML 検証をスキップして警告出力。
    - `--strict` オプションで警告も失敗扱いにできる。
  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式に .env を生成／更新するウィザード。シークレット入力のマスク、選択肢提示、既存値の再利用などをサポート。

- ロギング・プロセス管理ユーティリティ
  - ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 世代保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR / 引数での上書きに対応。
  - プロセス優先度・CPU アフィニティユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX (Linux/Mac/FreeBSD) の差分を吸収して `set_process_priority(level)` を提供（high/normal/low）。
    - `set_cpu_affinity(cpu_count)` でプロセスを最初の N コアに固定可能。権限不足などは警告でスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定、重み計算（等金額・スコア加重）を追加（src/kabusys/portfolio/portfolio_builder.py）。
    - スコア同点時のタイブレークルール（signal_rank）を実装。
    - スコア全 0 の場合は等金額配分にフォールバック（警告ログ）。
  - セクター集中制限・レジーム乗数を追加（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存ポジション比率が閾値を超えるセクターの新規候補除外ロジック。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear）を実装。未知レジームは 1.0 でフォールバック（警告）。
  - ポジションサイズ計算を追加（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の割当方式に対応。
    - 単元株（lot_size）丸め、1銘柄上限・投下資金上限 (max_utilization)・コストバッファを考慮したスケーリング処理を実装。
    - aggregate cap 超過時のスケールダウンと残差処理（lot 単位での追加配分）を実装。
  - portfolio パッケージのエクスポートを整備（src/kabusys/portfolio/__init__.py）。

- リサーチ/ファクター計算（骨格）
  - DuckDB を使ったファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - モメンタム・MA・ATR・流動性などの定義と計算方針を実装（関数 calc_momentum を含むがファイル末尾は途中まで実装）。
    - DuckDB 接続を受け取る設計で、prices_daily/raw_financials テーブルのみを参照する方針。

- ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、レイテンシ指標 (avg/max/P95) を集計して PASS/FAIL 判定を出力。
    - 日付フィルタ (--from / --to) と DB 指定 (--db / 環境変数 PAPER_TRADING_SQLITE_PATH) に対応。
    - データが無い場合のフォールバックや SQLite の OperationalError を考慮した堅牢な集計処理。

- 監視 DB 初期化
  - init_monitoring_db を利用して監視テーブルを起動時に保証（run_monitoring/run_execution で使用）。

### Changed
- ログ出力
  - すべての起動スクリプト・ユーティリティに共通の logging_setup を導入し、ログの一元化とファイルローテーションを実現（run_* スクリプトが setup_logging を呼び出すようになっている）。

- DB 分離
  - paper_trading 環境向けに paper_sqlite_path を導入し、ペーパートレードの記録を本番 DB から分離（run_execution で切替実装）。

### Fixed
- .env パースの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなど、.env の多様な記法に対応することで設定読み込みの誤解釈を防止（src/kabusys/config.py）。

### Notes / Implementation details
- 停止制御
  - いずれの長時間プロセス（監視・実行）もプロジェクトルートの data/stop_requested.flag を監視してグレースフルに停止。
- 権限や環境差
  - process priority / cpu affinity の設定は権限やプラットフォームにより失敗する可能性があるため、失敗時は警告ログを出して処理を継続する実装。
- 設定検証
  - validate_config は必須環境変数の未設定・プレースホルダ値・KABUSYS_ENV の妥当性・ログレベル・DB パスの親ディレクトリ存在確認・config/*.yaml の存在とパース検証（PyYAML がある場合）を実施する。
- ログ出力先
  - 標準出力は stdout を使用（stderr ではない）。cron 等で stdout/stderr を統合して扱う運用を想定。
- 未完実装
  - research/factor_research.py の一部（calc_momentum の実装途中）が残っているため、ファクター計算の完全実装は今後の作業対象。

### Removed
- 該当なし（初回リリースのため削除はなし）。

---

今後の予定（例）
- factor_research の完全実装と単体テスト整備
- ExecutionEngine / BrokerClient の詳細実装・モックの充実
- config ファイル (config/*.yaml) の生成スクリプトとデフォルトテンプレートの同梱
- 単体テスト・統合テストの追加と CI 設定

（必要に応じて日付や追加説明を更新してください。）