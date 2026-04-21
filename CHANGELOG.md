# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

最新: Unreleased

## [Unreleased]

### Added
- run_monitoring スクリプトによる SystemMonitor の常駐ポーリング起動処理。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
  - 停止フラグファイル（data/stop_requested.flag）検出で安全終了。
  - 監視は環境に関わらず本番用の SQLite パスを使用する挙動を明示。
- run_execution スクリプトによる ExecutionEngine 起動処理。
  - `KABUSYS_ENV=paper_trading` の場合は Mock ブローカーを使用し、paper_trading 用 DB に完全分離して記録。
  - 実行中は PID ファイル管理、停止フラグの監視・処理（停止時に engine.stop() を呼び出す）を実装。
- 環境設定関連 CLI：
  - config_setup: 対話式ウィザードで .env を作成・更新するツールを追加（シークレット入力のマスク表示、既存値の再利用）。
  - validate_config: .env や config/*.yaml の事前検証ツールを追加（必須環境変数チェック、パス存在チェック、YAML のパース検証や本番向けガードなど）。
- ポートフォリオ構築ライブラリ（純粋関数群）を追加:
  - portfolio_builder: 候補抽出（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。
  - position_sizing: ポジションサイズ計算（risk_based / equal / score）、lot 単位丸め、aggregate cap によるスケールダウン。
  - risk_adjustment: セクター上限の適用（apply_sector_cap）および市場レジーム乗数（calc_regime_multiplier）。
- 研究用モジュール:
  - research/factor_research: DuckDB を用いたモメンタム等のファクター計算のための基盤（関数群の骨格）。
- ツール:
  - tools/paper_verification_report: ペーパートレード検証レポートを生成する CLI（稼働率、注文成功率、レイテンシ等を集計、PASS/FAIL 判定）。
- ユーティリティ:
  - utils/logging_setup: stdout ストリーム + 日次ローテートファイルハンドラで一貫したログ設定を提供（ログディレクトリ作成失敗時はフォールバック）。
  - utils/process_priority: psutil を用いたクロスプラットフォームなプロセス優先度設定と CPU affinity 設定ユーティリティ。
- アプリケーション設定管理:
  - config: .env 自動読み込み（.env と .env.local、OS 環境変数保護対応）、高度な行パース（export 文・クォート・エスケープ・インラインコメント対応）、Settings クラスによるプロパティアクセスを実装。

### Changed
- ロギング:
  - すべての起動スクリプトから共通の setup_logging を呼び出してログ設定を統一。
  - ファイルハンドラは日次ローテーション・30 日保持に設定。
- 実行時のプロセス優先度を起動直後に "high" にセットすることで監視 / 実行の優先度を上げる挙動を採用。
- DB 接続:
  - Execution と Monitoring で DuckDB と SQLite の両方を利用（分析用に DuckDB、監視・発注履歴に SQLite）。
  - Paper Trading 環境では paper 専用 SQLite を使用して本番 DB と分離。

### Fixed
- .env パーサーの堅牢化:
  - export プレフィックス、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメント扱いなどを正しく処理するように改善。
  - 自動ロード時に OS 側の既存環境変数を保護する機能を追加（.env の上書き制御）。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合のフォールバック動作を明確化（コンソール出力のみで継続）。
- position_sizing / calc_score_weights 等でスコアが全て 0 の場合に等金額配分へフォールバックして例外を避けるように修正。
- run_monitoring / run_execution の終了処理で DB コネクションを確実にクローズするように整備。

### Security
- config_setup にて .env ファイルを生成する際、シークレット項目はマスク表示して入力・確認を行う旨を実装。
- .env の生成と README に「.env を絶対に Git にコミットしないこと」を明確に記載。

### Notes
- スクリプトとして直接実行可能（if __name__ == "__main__": main()）にしてあるため、デーモン化や systemd 連携は運用側での設定が必要。
- process_priority はプラットフォーム差分（Windows / POSIX）を吸収するが、権限不足時は警告を出してスキップする設計。

---

## [0.1.0] - 2026-04-21

初回公開リリース。上記 Unreleased に記載の機能群を含む初期安定版リリース。

- 主要機能:
  - 実行（ExecutionEngine）と監視（SystemMonitor）の起動スクリプト。
  - .env 管理（自動読み込み・対話ウィザード）と検証 CLI。
  - ポートフォリオ構築およびサイズ計算の純粋関数ライブラリ。
  - ペーパートレード検証レポート生成ツール。
  - DuckDB/SQLite を利用したデータアクセス基盤の組み込み。
  - ロギング、プロセス優先度などの運用ユーティリティ。

- 安定性・運用上の配慮:
  - 起動スクリプトは停止フラグ（data/stop_requested.flag）および PID ファイルを用いた安全停止制御を持つ。
  - 本番（live）環境に対する注意喚起と設定検証ロジックを導入。

---

その他、バージョン管理やリリースノートの詳細化（変更差分やコミット単位の履歴化）は今後のリリースで追記してください。