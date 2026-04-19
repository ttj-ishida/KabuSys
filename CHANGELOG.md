# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。バージョン番号は PEP-440 に従います。

なお、この CHANGELOG はコードベース（src/kabusys 以下）から推測して作成しています。実装上の挙動や既知の制約も併記しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19

### Added
- 基本パッケージ初期実装を追加
  - パッケージメタ情報
    - src/kabusys/__init__.py にバージョン `0.1.0` を設定。
  - 実行用スクリプト
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
      - 停止はプロジェクトの data/stop_requested.flag を監視して行う。
      - Monitoring は KABUSYS_ENV に関わらず本番の sqlite_path を使用する実装。
      - sqlite3 と DuckDB の接続を確立し、監視用 DB 初期化を行う。
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading DB（data/paper_trading.db）を使用し、MockBrokerClient を利用する設計（本番 DB と分離）。
      - 停止フラグ・PID 管理を行い、別スレッドでエンジンを実行・監視する。
  - 設定管理
    - src/kabusys/config.py
      - .env 自動ロード（プロジェクトルートの検出を .git / pyproject.toml で行う）。
      - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
      - .env のパースは引用符・エスケープ・インラインコメントに対応する堅牢な実装。
      - Settings クラスを提供し、J-Quants / kabuAPI / DB パス / 監視しきい値 / 環境種別 等のプロパティを公開。
      - PAPER_FILL_MODE のバリデーション、paper_sqlite_path 等のプロパティを実装。
  - 設定関連 CLI
    - src/kabusys/config_setup.py
      - .env を対話式に生成・更新するウィザードを実装。
      - デフォルト値・選択肢・シークレット入力・保存確認まで対応。
    - src/kabusys/validate_config.py
      - 起動前に .env および config/*.yaml の検証を行う CLI を実装。
      - 必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML があれば）を実施。
      - `--strict` オプションで警告も失敗扱いにできる。
  - ロギング・プロセスユーティリティ
    - src/kabusys/utils/logging_setup.py
      - 統一的なロギング設定ユーティリティを追加。
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
      - LOG_DIR／LOG_LEVEL の環境変数を参照し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続。
    - src/kabusys/utils/process_priority.py
      - プラットフォーム差分（Windows / POSIX）を吸収したプロセス優先度設定を提供（psutil を使用）。
      - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。失敗時は警告を出してスキップ。
  - Portfolio 構築関連（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア合計が 0 の場合は等配分へフォールバックし警告を出す。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。
      - unknown セクターは制限対象外として扱う仕様。
      - 未知レジームは 1.0 にフォールバックし警告を出す。
    - src/kabusys/portfolio/position_sizing.py
      - allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算を実装。
      - lot_size（単元株）単位で丸め、per-position 上限・aggregate cap（available_cash を超える場合のスケーリング）を実装。
      - cost_buffer による保守的見積りと、端数配分（fractional remainder）に基づく追加配分ロジックを実装。
    - src/kabusys/portfolio/__init__.py で上記関数群をエクスポート。
  - 分析・検証ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 用検証レポートを生成する CLI を追加。
      - 稼働率、注文成功率（fill rate）、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を行う（閾値はソースに定義）。
      - SQLite DB（PAPER_TRADING_SQLITE_PATH または指定パス）から trade_logs / system_status / risk_logs を参照。
  - リサーチ（ファクター計算）初期実装
    - src/kabusys/research/factor_research.py
      - Momentum などのファクター計算方針と定数を定義。DuckDB 接続を受け取り prices_daily 等を参照して計算する設計（実装の一部が含まれている）。
  - その他ユーティリティ
    - src/kabusys/utils/__init__.py、tools パッケージ初期化ファイルなどを追加。

### Changed
- 初期リリースにつき該当なし（新規追加のみ）。

### Fixed
- 初期リリースにつき該当なし。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

## 既知の制約・注意事項（Implementation notes / Gotchas）
- run_monitoring.py は Monitoring 用 DB に常に Settings.sqlite_path（「本番」監視 DB）を使う実装になっており、KABUSYS_ENV の値に依存しません。テストや paper_trading と本番監視 DB を分離したい場合は運用上の注意が必要です。
- config.py の自動 .env ロードはプロジェクトルートが検出できない場合はスキップされます。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env パーサはシングル/ダブルクォートとバックスラッシュエスケープに対応していますが、極端に複雑な構文（複数行値など）は想定していません。
- position_sizing の price 欠損時の扱いに TODO があり、現状 price が 0.0 の場合には当該銘柄はスキップされるためエクスポージャーや配分が過少見積りされる可能性があります。将来的に前日終値等のフォールバックを検討する旨が記載されています。
- calc_regime_multiplier は未知レジームを 1.0 にフォールバックします。戦略実装側で regime が "bear" のとき BUY シグナルを生成しない設計になっているため、乗数は追加の安全弁として機能します。
- logging_setup はログディレクトリ作成に失敗した場合はファイル出力を行わず、コンソール出力のみで継続します（エラーメッセージは stderr/ログに出力）。
- process_priority/set_cpu_affinity は psutil の権限に依存します。権限不足や未対応 OS の場合は警告を出してスキップします。

---

もしリリースノートの粒度（モジュールごと、CLI ごと、内部アルゴリズムの詳細など）を変更したい場合や、日本語表現をより簡潔／詳細に調整したい場合は指示してください。