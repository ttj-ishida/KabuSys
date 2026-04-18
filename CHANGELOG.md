# Changelog

すべての重要な変更点をここに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

フォーマット:
- すべての変更はセクションごとに分類（Added, Changed, Fixed, ...）
- 日付は YYYY-MM-DD 形式

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーションの初期実装を追加。
  - パッケージメタ情報: `src/kabusys/__init__.py` にバージョン `0.1.0` を追加。
- 起動スクリプト
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知処理の実装。
    - 監視用 DB は環境に依存せず production 相当の `sqlite_path` を使用して初期化。
  - `src/kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite（`data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderManager / RiskManager / Reconciler の組立、ExecutionEngine の起動/停止ロジックを実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を利用する制御ロジックを実装。
- 設定管理・ウィザード・検証
  - `src/kabusys/config.py`
    - 環境変数読み込み・管理クラス `Settings` を実装。各種設定プロパティ（DB パス、API トークン、環境種別、各種閾値など）を提供。
    - プロジェクトルート自動検出（.git または pyproject.toml）を実装し、`.env` / `.env.local` の自動読み込みを行う（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - `.env` パースロジックはクォート・エスケープ・コメント等に対応し堅牢化。
  - `src/kabusys/config_setup.py`
    - 対話式 .env 作成/更新ウィザードを実装。典型的な環境変数項目（KABUSYS_ENV、J-Quants トークン、kabu API パスワード、DB パス、LINE 設定等）をサポート。
  - `src/kabusys/validate_config.py`
    - 起動前設定検証 CLI を追加。必須環境変数・KABUSYS_ENV 値・ログレベル・DB パス・config/*.yaml の存在などを検査。`--strict` オプションで警告を失敗扱いにできる。
- ポートフォリオ構成（純関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定 (`select_candidates`)、等分配 (`calc_equal_weights`)、スコア重み (`calc_score_weights`) を実装。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中上限フィルタ (`apply_sector_cap`) とマーケットレジーム乗数 (`calc_regime_multiplier`) を実装。
  - `src/kabusys/portfolio/position_sizing.py`
    - 発注株数算出ロジック (`calc_position_sizes`) を実装。`risk_based` / `equal` / `score` の配分方式、単元株丸め、aggregate cap のスケールダウン、cost_buffer の考慮などを含む。
  - `src/kabusys/portfolio/__init__.py` でモジュールエクスポートを提供。
- ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - 全体共通のロギング設定ユーティリティを実装。stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日バックアップ）をルートロガーに設定。既存ハンドラのクリアやログディレクトリ作成失敗時のフォールバックを実装。
  - `src/kabusys/utils/process_priority.py`
    - プラットフォーム非依存のプロセス優先度設定ユーティリティを実装（Windows / POSIX の差分吸収）。`set_process_priority` と `set_cpu_affinity` を提供し、権限不足時や未対応 OS では警告ログを出して安全にスキップする。
- ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード検証用レポート生成ツールを追加。system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（P95）を算出し PASS/FAIL 判定を行う。閾値はソース内で定義（稼働率 99%、成功率 90% 等）。
- リサーチ
  - `src/kabusys/research/factor_research.py`
    - ファクター計算モジュールを追加（Momentum 等の計算方針と定数を実装）。DuckDB を使って prices_daily / raw_financials を参照する設計。Momentum 計算関数の骨格を実装（実装が途中の箇所あり）。

### Changed
- ロギングの挙動を明示化
  - コンソール出力は stdout を使用（stderr ではない）。これにより cron 等からのリダイレクト時の取り扱いを統一。
- .env 自動読み込みの順序と保護
  - 自動読み込みの優先順位を OS 環境変数 > .env.local > .env とし、OS 環境変数を保護するため上書き禁止（protected）を実装。
- Execution / Monitoring の DB 初期化
  - 起動時に監視テーブルを一貫して作成するため `init_monitoring_db` を呼び出す（冪等性を確保）。

### Fixed
- 環境変数パースの堅牢化
  - `_parse_env_line` でクォート内のバックスラッシュエスケープや行内コメント処理を適切に処理するよう修正。不正な .env 行を安全に無視するようにした。
- ポジション算出の端数処理と集約上限ロジックの安定化
  - `calc_position_sizes` のスケーリング処理において残余キャッシュを用いた lot_size 単位での再配分ロジックを実装し、順序の再現性を確保。

### Documentation
- 各モジュールに docstring を追加し、関数仕様・引数・返り値・注意事項（TODO・将来拡張案等）を明記。
- config_setup ウィザードの使用説明や validate_config の使い方をソース内に記載。

### Security
- API トークン等のシークレットは `.env` に格納する設計（README 等で .env をコミットしない旨を明示）。config_setup にシークレットマスク表示を実装。

### Known issues / Notes
- `research/factor_research.py` の Momentum 計算実装は途中（ソース末尾で切れている）。今後のリリースで完了予定。
- 一部のファイル・関数は本番環境（live）に切り替えた際の追加運用ガード（LINE 通知設定の未設定警告や KILL_FLAG_CLEAR_ON_START の危険性に関する注意喚起）は入れてあるが、運用時には config の見直しを推奨。
- `psutil` による優先度設定や CPU affinity は権限や OS に依存するため、アクセス権限不足時は警告ログを出してスキップする挙動となる。

---

開発に関する補足や次回リリース予定の改善点:
- research モジュールの完成（ファクター計算の最終化、正規化ユーティリティ連携）。
- ExecutionEngine / RiskManager の統合テストおよび BrokerClient のモック強化。
- ログ・メトリクス収集の拡張（Prometheus export など）。
- 単体テスト・CI の追加（現状はコード実装中心）。

（以上）