# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。

なお、本記録は与えられたコードベースから振る舞い・追加機能を推測して作成しています。

## [Unreleased]

特になし。

## [0.1.0] - 2026-04-19

### Added
- 全体
  - 初回リリース。日本株自動売買フレームワーク「KabuSys」の基礎機能群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト / デーモン
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）によりポーリング間隔を上書き可能。
    - 停止制御にプロジェクトの data/stop_requested.flag ファイルを監視。
    - Monitoring は実行環境にかかわらず本番用の sqlite_path を使用する仕様を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - SQLite / DuckDB 接続の初期化と適切なクローズ処理を実装。
    - 監視処理中の例外を捕捉してログに出力し、次ポーリングへ継続。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し paper_trading 用 DB（`data/paper_trading.db`）に完全分離して記録する挙動を実装。
    - 停止フラグ（data/stop_requested.flag）や実行 PID ファイルの取り扱いを実装。
    - 起動時にプロセス優先度を "high" に設定。
    - ExecutionEngine をデーモン・スレッドで起動し、停止フラグに応じて安全に停止。

- 設定管理
  - config.py
    - 環境変数管理用 Settings クラスを追加。
    - .env 自動読み込み機能を実装（`.env` と `.env.local`、OS 環境変数の保護を考慮）。
    - .env のパース実装を強化（export プレフィックス、クォート値のエスケープ、インラインコメントの処理など）。
    - 各種設定プロパティを提供（J-Quants / kabuステーション / DB パス / PID / 監視閾値 / 環境種別判定 等）。
    - `paper_fill_mode` の値検証と `paper_sqlite_path` の分離を実装。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。
    - 主要設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）をユーザに入力させ `.env` を生成。
    - 既存 .env の読み込み・既存値の再利用機能、シークレット値のマスク表示を実装。
    - 書き込みフォーマットで .env のテンプレート出力を実装。

  - validate_config.py
    - 起動前の設定検証 CLI を追加（env の必須項目チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック）。
    - `--strict` オプションにより警告も FAIL 扱いで終了可能。
    - PyYAML 未導入時の警告、ライブ環境向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化関数 `setup_logging()` を追加。
    - コンソール出力は stdout を使用、ファイル出力は日次ローテーション（TimedRotatingFileHandler）で 30 日分保持。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時にはファイル出力をスキップし、コンソール出力のみで継続。

  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定 `set_process_priority()` を追加。
    - CPU アフィニティ固定用 `set_cpu_affinity()` を追加（利用可能コア数を考慮）。
    - アクセス権限不足や未対応 OS を考慮しエラーを抑制して安全にスキップする実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定関数 `select_candidates()` を追加（スコア降順、同点は signal_rank でブレーク）。
    - 重み計算 `calc_equal_weights()`（等金額）と `calc_score_weights()`（スコア正規化、全スコア0時は等分へフォールバック）を追加。

  - portfolio/risk_adjustment.py
    - セクター集中防止の `apply_sector_cap()` を追加（既存ポジションからセクター別エクスポージャー算出、閾値超過セクターの候補除外）。
    - 市場レジームに応じた投下資金乗数を返す `calc_regime_multiplier()` を追加（bull/neutral/bear とフォールバック挙動を実装）。

  - portfolio/position_sizing.py
    - 発注株数算出 `calc_position_sizes()` を追加。
    - allocation_method により "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金にスケールダウン）を実装。
    - cost_buffer を考慮した保守的なコスト見積りと残差の lot_size 単位での再配分ロジックを実装。

  - portfolio/__init__.py で上記関数群をエクスポート。

- リサーチ（ファクター算出）骨子
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨子を追加（モメンタム、MA200、ATR、流動性、財務指標などの設計・定数定義）。
    - 関数インターフェース（calc_momentum 等）を用意。今後 DuckDB SQL と組み合わせて実装拡張する設計。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - SQLite（paper_trading.db）を参照し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出して標準出力にレポート化。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づいた PASS/FAIL 判定を実装。
    - コマンドライン引数で期間（--from / --to）と DB パス（--db）を指定可能。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes
- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行うため、配布後やテスト時に動作しない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化できます。
- ロギングは stdout を標準出力に使用するため、cron やスケジューラから起動した際のログリダイレクト設定に配慮してください。
- run_execution/run_monitoring といった長時間稼働プロセスはプロセス優先度設定や停止フラグの存在に依存するため、本番導入時は `data/` ディレクトリ周りの権限・運用フローを整備してください。
- 一部モジュール（ExecutionEngine、SystemMonitor、monitoring_db 等）は本記録の対象コードで参照されており、別モジュールとして実装されることを想定しています。

---

（終わり）