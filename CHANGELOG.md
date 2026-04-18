# Keep a Changelog — CHANGELOG.md
（フォーマット: Keep a Changelog 準拠）
※ コードベースから推測して作成しています。

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- 開発用 CLI / 起動スクリプトを追加
  - 実行エンジン起動: `src/kabusys/run_execution.py`
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite DB を使用（デフォルト: data/paper_trading.db）。
    - Broker クライアントをファクトリ経由で生成、ExecutionEngine をスレッドで実行し停止フラグを監視。
    - 起動前に監視テーブルの存在を保証（init_monitoring_db 呼び出し）。
  - 監視ループ起動: `src/kabusys/run_monitoring.py`
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
  - 設定検証 CLI: `src/kabusys/validate_config.py`
    - .env や config/*.yaml の存在・基礎的な妥当性チェックを実行。
    - `--strict` オプションで警告も FAIL 扱いにできる。
  - 環境設定ウィザード: `src/kabusys/config_setup.py`
    - 対話式で .env を作成・更新するウィザードを提供。
    - J-Quants / kabu API / DB パス等のテンプレ項目を収集・保存。
  - Paper Trading 検証レポート生成ツール: `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード DB から稼働率、注文成功率、送信率、レイテンシ等の指標を集計してレポート出力。
    - デフォルト閾値（稼働率 99%、Fill 90% 等）に基づく PASS/FAIL 判定を実装。

- ポートフォリオ構築関連の純関数群を追加（DB 非依存）
  - 候補選定 / 重み計算: `src/kabusys/portfolio/portfolio_builder.py`
    - select_candidates, calc_equal_weights, calc_score_weights を提供。
    - スコアが全て 0 の場合は等分配へフォールバックし警告を出す。
  - セクター集中制限・レジーム調整: `src/kabusys/portfolio/risk_adjustment.py`
    - apply_sector_cap（既存保有を考慮したセクター上限フィルタ）。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に対応する乗数）。
  - 株数算出・リスク制限・単元丸め: `src/kabusys/portfolio/position_sizing.py`
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）単位で丸め、aggregate cap を満たすためのスケーリングと残差配分ロジックを実装。

- ユーティリティ
  - ログ設定ユーティリティ: `src/kabusys/utils/logging_setup.py`
    - stdout への StreamHandler と 日次ローテート FileHandler（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル・ログディレクトリは引数／環境変数で上書き可能。
  - プロセス優先度・CPU affinity 設定ユーティリティ: `src/kabusys/utils/process_priority.py`
    - Windows / POSIX の差分を吸収して優先度設定（high/normal/low）をサポート。
    - CPU affinity を最初の N コアに固定するヘルパーを提供。権限不足時は警告でスキップ。

- 環境設定ロード・管理
  - `.env` 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）
    - 読み込み順: OS 環境 > .env.local（上書き） > .env（未設定のみセット）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - `.env` パーサ実装強化
    - export プレフィックス対応、クォート（シングル/ダブル）内のエスケープ処理、インラインコメント処理に対応。
  - Settings クラス（`src/kabusys/config.py`）で各種環境変数をラップして提供
    - DB パス、Paper Trading 設定、監視閾値、PID/kill flag パス、LOG_LEVEL、env 判定（is_live/is_paper/is_dev）など。

- データベース関連
  - DuckDB 接続を想定した設計（duckdb パスを Settings で管理）。
  - 監視テーブルの初期化を行う init_monitoring_db 呼び出しを起動スクリプトで行う（冪等処理）。

### Changed
- ロギングの出力先を標準エラーではなく標準出力（stdout）に統一
  - cron や外部スケジューラでのリダイレクト運用を想定。

- run_monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する設計で明示。

### Fixed
- .env 読み込みの堅牢化（読み込み失敗時は警告を出して継続）。
- プロセス優先度設定・CPU affinity の失敗を警告で扱い、起動失敗としないフォールバックを実装。

### Notes
- research モジュール（`src/kabusys/research/factor_research.py`）はファクター計算の骨組みが含まれ、DuckDB を利用した実装予定（未完の箇所あり）。

---

## [0.1.0] - 2026-04-18

初期リリース — 基本機能の提供:
- 上記「Added」項目の大半を含む初期公開版。
- パッケージメタデータ: `__version__ = "0.1.0"`

### Highlights
- 自動売買システムの基盤となる以下のコンポーネントを実装:
  - 実行エンジン起動・監視ループ・Paper Trading 分離。
  - 環境設定ウィザードと検証ツール（CLI）。
  - ポートフォリオ構築群（候補選定、重み、ポジションサイズ、セクター制限、レジーム乗数）。
  - ロギング・プロセス優先度ユーティリティ。
  - Paper Trading 向け検証レポート生成ツール。

### Breaking Changes
- なし（初期リリース）。

---

過去のリリースや将来の変更はここに追記します。質問や修正点があればお知らせください。