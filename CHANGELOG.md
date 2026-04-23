# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
慣例: "Added/Changed/Fixed/Removed" に分類しています。

## [Unreleased]

- ドキュメント化のみの調整や軽微な内部リファクタがあればここに記載します。

---

## [0.1.0] - 2026-04-23

初回公開リリース。日本株自動売買フレームワーク「KabuSys」の基盤機能を実装します。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。
  - DuckDB / SQLite を用いたデータ処理・永続化の基盤を実装。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 停止はプロジェクト直下 data/stop_requested.flag を検知して行う。
    - Monitoring は実行環境にかかわらず本番用の sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading SQLite（`data/paper_trading.db`）を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検知でエンジン停止処理を実行。
    - 実行中は PID ファイル（data/execution.pid）を利用。
- 設定管理
  - config.py
    - 環境変数の読み込み/管理を実装。
    - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env パースで以下をサポート:
      - export KEY=val 形式
      - シングル/ダブルクォート内のバックスラッシュエスケープ
      - クォートなし値におけるコメント認識（直前がスペース/タブの場合のみ）
    - 設定値の検証（enum 値チェック、PAPER_FILL_MODE の許容値など）。
    - 各種パス・閾値・フラグ（DUCKDB_PATH/SQLITE_PATH/PAPER_TRADING_SQLITE_PATH/PID_FILE_PATH/KILL_FLAG_* 等）をプロパティで提供。
  - config_setup.py
    - 対話式 .env 設定ウィザードを追加（`python -m kabusys.config_setup`）。
    - 既存 .env 読み込み・マスク表示・選択肢・デフォルトをサポートし、最終的に .env を安全に書き出す。
  - validate_config.py
    - 起動前チェック用 CLI を追加（`python -m kabusys.validate_config`）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML が導入されていればパース検証を実施）など。
    - `--strict` オプションで警告も失敗扱いにできる。
- ポートフォリオ構築（純関数）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコア全てが 0 の場合は等金額配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（既存保有比率が閾値を超えるセクターの新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。
    - allocation_method = "risk_based" / "equal" / "score" をサポート。
    - 単元株丸め（lot_size）、per-position 上限・aggregate cap のスケールダウン、cost_buffer（手数料/スリッページの保守見積）を考慮。
    - スケールダウン時の残差処理（fractional remainder に基づく追加配分）を実装。
- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日分保存）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - プロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX を吸収し、psutil を利用して nice / priority class と CPU affinity を設定。権限不足や未対応 OS は警告でスキップ。
- ツール / レポート
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加（`python -m kabusys.tools.paper_verification_report`）。
    - 稼働率、注文成功率（Fill）、送信率（Sent）、リスク却下数、API レイテンシ（avg/max/P95）を集計して PASS/FAIL を判定。
    - 閾値（稼働率 99%、Fill 90%、Send 95%、P95 latency 200 ms）をデフォルトで提供。日付フィルタ --from / --to、DB 指定 --db をサポート。

### Changed
- logging: 既存ハンドラをクリアしてから再設定することで二重ハンドラ登録を防止。
- .env の自動読み込み:
  - OS 環境変数を保護する仕組み（protected set）を導入し、.env.local の上書き時に OS 環境変数が上書きされないようにした。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テストなどで利用）。

### Fixed
- 環境変数パーサー:
  - export プレフィックス、クォート内のバックスラッシュエスケープ、クォートなし値のインラインコメント処理などを正しく処理するように改善。
- run_execution/run_monitoring:
  - 停止フラグの検知と安全な終了処理（接続クローズ等）を明確化。
  - run_monitoring のポーリングで check_once() の例外をキャッチしてループ継続するように変更（単一例外で監視が停止しないようにする）。

### Removed
- 該当なし（初回リリース）。

### Notes / Known limitations
- research/factor_research.py はモジュール骨格と設計方針が記載され、モメンタム計算関数開始部が存在しますが一部未完（続きの実装が必要）。
- position_sizing の価格フォールバック（price が欠損した場合の処理）は TODO コメントで将来の改善を示しています。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム非対応時に警告を出して安全にスキップしますが、環境依存の挙動に注意してください。
- Paper Trading 関連は paper_sqlite_path による DB 分離で本番 DB と独立しているが、運用時は .env の設定と DB ファイルのバックアップ方針に注意してください。

---

もし変更内容の項目追加や詳細化（例: 各モジュールのパラメータ説明や CLI 使用例）をご希望であれば、その点を指定してください。必要に応じて日付やリリースノートのフォーマットを調整します。