# Changelog

すべての注目すべき変更はこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、以下は与えられたコードベースの内容から推測して作成したリリースノートです。

## [Unreleased]

特になし。

## [0.1.0] - 2026-04-18

初回リリース。自動売買システム KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、監視・検証ツール群を追加。

### Added
- 全体
  - パッケージ初期公開。バージョン情報を `src/kabusys/__init__.py` にて `0.1.0` として定義。
- 起動スクリプト
  - `run_execution.py` を追加。ExecutionEngine の起動スクリプトを提供。
    - KABUSYS_ENV が `paper_trading` の場合、paper 用専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - エンジン PID 管理、停止フラグ（data/stop_requested.flag）による安全停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定。
  - `run_monitoring.py` を追加。SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用。
    - 停止フラグ検知で安全終了。
- 設定・検証関連
  - `config.py` を追加。
    - プロジェクトルートを自動検出して `.env` / `.env.local` を安全に読み込む自動ロード機能（無効化オプションあり）。
    - `.env` パースロジックは export 構文、シングル/ダブルクォート、エスケープ、行内コメントに対応。
    - `Settings` クラスを提供し、各種設定値（API トークン・DB パス・閾値等）をプロパティとして取得できるように。
    - Paper Trading 用の設定（`paper_sqlite_path`, `paper_fill_mode` 等）や env 値の検証を実装。
  - `config_setup.py` を追加。
    - 対話式ウィザードで `.env` の初期作成・更新を支援。各項目の説明、既存値の再利用、秘密値のマスク表示等をサポート。
  - `validate_config.py` を追加。
    - 起動前チェック CLI。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml 存在・パース（PyYAML がインストールされている場合）を検査。
    - `--strict` オプションで警告を失敗扱いにできる。
    - 本番（live）環境向けの追加ガード（LINE 通知設定・Kill Switch の自動クリアフラグ警告等）を実装。
- ポートフォリオ構築（純関数群）
  - `portfolio/portfolio_builder.py`
    - BUY シグナルの候補選択 (`select_candidates`) と重み付け関数（等分配 `calc_equal_weights`、スコア加重 `calc_score_weights`）を追加。
    - スコアが全て 0 の場合のフォールバックやタイブレーク方針を明記。
  - `portfolio/risk_adjustment.py`
    - セクター集中抑制 (`apply_sector_cap`) とマーケットレジームに応じた乗数計算 (`calc_regime_multiplier`) を追加。
    - 不明セクターは除外対象としない等の挙動を明示。
  - `portfolio/position_sizing.py`
    - 銘柄ごとの発注株数を計算する `calc_position_sizes` を追加。
    - リスクベース / 等配分 / スコア配分の複数方式、単元株（lot_size）丸め、aggregate cap（利用可能現金でスケールダウン）を実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的見積りを実装。
  - `portfolio/__init__.py` で上記機能をエクスポート。
- ユーティリティ
  - `utils/logging_setup.py`
    - 一貫したログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定する。
    - LOG_DIR 環境変数／引数でログ出力先を変更可能。ディレクトリ作成失敗時はファイル出力を自動的に無効化。
  - `utils/process_priority.py`
    - Windows / POSIX を吸収するプロセス優先度設定（`set_process_priority`）および CPU affinity 設定（`set_cpu_affinity`）を追加。
    - アクセス権限不足等に対する安全なフォールバック（警告出力）を実装。
- 監視・検証ツール
  - `monitoring` 初期化ロジックを利用する起動スクリプトからの DB 初期化（`init_monitoring_db` を呼ぶ）をサポート（冪等）。
  - `tools/paper_verification_report.py`
    - Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率（Fill Rate）、送信率、レイテンシ（平均・最大・P95）などを集計して PASS/FAIL 判定を出力。
    - 日付フィルタ (--from / --to)、DB パス (--db) の指定をサポート。デフォルト DB は `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。
- リサーチ
  - `research/factor_research.py`（ファクター計算モジュール）を追加（モメンタム・ボラティリティ等の計算を意図した設計）。DuckDB を利用して prices_daily / raw_financials を参照する想定。注: ファイルは一部未完（末尾で切れている）。

### Changed
- なし（初回リリースのため該当なし）

### Fixed
- なし（初回リリースのため該当なし）

### Security
- なし

### Notes / Implementation details
- DB 分離: Paper Trading は専用 SQLite を使用することで本番 DB と完全分離する設計（`Settings.paper_sqlite_path`、`run_execution.py` の接続ロジック）。
- ログ: コンソール出力は stdout を使用（cron 等で stdout/stderr をまとめた場合に扱いやすくするため）。
- 環境自動読み込み: `.env` 自動ロードはプロジェクトルートが検出できるときのみ実行され、OS 環境変数は `.env` によって上書きされない（保護）。
- 安全停止: 実行／監視プロセスは project-root/data/stop_requested.flag（または設定されたパス）を確認して安全に停止する。ExecutionEngine は停止時に engine.stop() を呼びスレッドを正常終了させる。
- エラーハンドリング: 監視ループ内で monitor.check_once() が例外を投げてもループ継続し、ログに例外トレースを残す実装。

---

既知の制限・TODO（コードコメントより推測）
- `research/factor_research.py` は途中で切れている（未完）。実際のファクター計算ロジック全体は実装継続が必要。
- `position_sizing.calc_position_sizes` の価格欠損時の取り扱いや単元株の銘柄別対応（lot_size の銘柄別化）は将来的な改善対象としてコメントあり。
- セクターエクスポージャ算出で price が 0 の場合の過少見積りへの対処（フォールバック価格利用）は将来の拡張候補。

もし特定のファイルや機能について、より詳細なリリースノートや変更点（理由、影響範囲、移行手順など）を出力したい場合は対象を指定してください。