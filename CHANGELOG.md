# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※ この履歴はソースコードの内容から推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-22

### Added
- 基本アプリケーションフレームワークを実装。
  - パッケージバージョン: `kabusys` v0.1.0（src/kabusys/__init__.py）。
- 起動スクリプト
  - 実行エンジン起動スクリプト: `run_execution.py`
    - プロセス優先度を起動時に "high" に設定。
    - 環境が `paper_trading` の場合は専用の Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と分離。
    - 実行エンジンをデーモンスレッドで起動し、`data/stop_requested.flag` による安全な停止をサポート。
    - PID ファイルサポート（`data/execution.pid`）。
  - 監視ループ起動スクリプト: `run_monitoring.py`
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 SQLite パス（Settings.sqlite_path）を使用する設計。
    - 停止フラグ（`data/stop_requested.flag`）検知によるループ終了と例外ハンドリング。
- 設定管理
  - `Settings` クラスを導入（src/kabusys/config.py）。
    - .env 自動ロード（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - 自動ロード抑止フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
    - 多数の設定プロパティ（DB パス, API トークン, 環境種別, ログレベル, 各種閾値等）を提供。
    - `PAPER_FILL_MODE` 等の値チェックを実装（不正値は例外）。
    - `is_live` / `is_paper` / `is_dev` 等のユーティリティプロパティを提供。
- 設定関連 CLI
  - 環境設定ウィザード: `config_setup.py`
    - 対話式で `.env` を生成・更新。
    - シークレット項目のマスク表示、既存値の再利用、保存確認をサポート。
  - 設定検証ツール: `validate_config.py`
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや `config/*.yaml` の存在・パース検証（PyYAML があれば内容検証）を行う。
    - `--strict` オプションで警告を FAIL 扱いにできる。
- ログ基盤
  - `setup_logging` ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout への StreamHandler と、日次ローテート（30日保持）の TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ自動作成、環境変数 / 引数によるログレベル・出力先解決。
    - ログディレクトリ/ファイル作成失敗時はファイルハンドラをスキップして stdout のみで動作。
- プロセス / リソース制御ユーティリティ
  - `set_process_priority` と `set_cpu_affinity`（src/kabusys/utils/process_priority.py）
    - Windows / POSIX(Linux/macOS/FreeBSD) に対応して優先度（high/normal/low）を設定。
    - CPU affinity を先頭 N コアに固定する機能を提供。
    - 権限不足や未対応環境では警告を出して安全にフォールバック。
- ポートフォリオ構築モジュール（純粋関数群）
  - `portfolio_builder.py`
    - 候補選定（スコア降順 + タイブレーク）、等重み・スコア重みの計算（スコアが全て 0 の場合は等重みへフォールバック）。
  - `risk_adjustment.py`
    - セクター集中制限の適用（既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" をサポート、未知の値は 1.0 にフォールバック）。
  - `position_sizing.py`
    - 重み・候補・ポートフォリオ情報から発注株数を算出（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate 上限（available_cash）制御、cost_buffer（手数料・スリッページ見積）考慮したスケールダウンと再配分ロジックを実装。
    - 価格欠損時のスキップ、スケールダウン時の残差処理による安定的な配分。
- 研究用ファクター計算モジュール（骨格）
  - `research/factor_research.py` にモメンタム等の計算関数（DuckDB 接続を受け、prices_daily 等を参照する設計）が追加（実装途中の関数あり）。
- Paper Trading 検証ツール
  - `tools/paper_verification_report.py`
    - Paper Trading SQLite（環境変数 `PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）から指標を集計してレポート出力。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）など。
    - P95 計算、日付フィルタ（--from / --to）、閾値による Pass/Fail 判定を実装（閾値はスクリプト内定数）。
- 監視 DB 初期化ユーティリティ
  - `monitoring.monitoring_db.init_monitoring_db` を run スクリプトで呼び出し、監視テーブルを必ず用意（冪等）。
- Broker / Execution コンポーネントの組み立て（実行フローの骨格）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の相互接続を run_execution で行う（EngineConfig 等で日付や PID を渡す）。

### Changed
- .env ファイル自動読み込みの挙動を明確化
  - 読み込み優先順: OS 環境変数 > .env.local > .env。
  - OS 環境変数は保護され、.env.local の override によって意図せぬ上書きを防止。
- ロギングの挙動統一
  - 既にハンドラが設定されている場合は一度クリアして再設定し、二重出力を防止。

### Fixed
- .env パーサの堅牢化
  - export プレフィックス対応、クォート（シングル/ダブル）とバックスラッシュエスケープの正しい解釈、行内コメントの扱いを実装。
  - 無効行や空行、コメント行を無視。
- Execution/Monitoring の安全シャットダウン
  - `data/stop_requested.flag` の検知で正常に停止する処理を追加。
  - run_monitoring の poll 間隔に対する環境変数の不正値を検出しデフォルトにフォールバック（負や 0 を無効扱い）。
- ポートフォリオ計算の安定化
  - calc_score_weights: 全スコアが 0.0 の場合は等重みへフォールバックしてゼロ割を回避。
  - calc_regime_multiplier: 未知のレジーム値に対してログ警告を出し 1.0 にフォールバック。
  - calc_position_sizes: 価格欠損・0 値をスキップして例外を避ける。スケーリング時に lot_size 単位で丸め、残余資金で順次配分するロジックを追加。
- logging_setup: ログディレクトリ作成失敗時にファイルハンドラを安全にスキップし、stderr への警告出力にフォールバック。

### Security
- API トークン等の機密値は .env として扱うことを想定し、config_setup で `.env` を生成する際に注意書きを明示（.env を Git にコミットしない旨）。

### Documentation / UX
- config_setup の対話式ウィザードで既存値のマスク表示・再利用、保存確認を実装して初期設定を支援。
- validate_config での詳細メッセージ（INFO/WARNING/ERROR）により起動前チェックが容易に。

### Notes / Known limitations
- research/factor_research.py は設計・骨格が導入されているが、一部実装が途中（ファイル末尾が途切れている状態）である可能性があるため、本格利用時は関数の完成度を確認してください。
- position_sizing の価格フォールバック（前日終値や取得原価など）は未実装（TODO コメントあり）。価格欠損時はスキップによる保守的な振る舞いとなる。
- 一部の開発者ユーティリティ（例: `monitoring_db.init_monitoring_db` の詳細、ExecutionEngine の内部挙動、BrokerClientFactory の実装）は本履歴の範囲外のため、実際の運用前に追加のレビューが必要です。

---

今後のリリースでは以下を予定（推定）
- research/factor_research の完遂と単体テスト
- ExecutionEngine／BrokerClient の統合テストとエラーハンドリング改善
- ログ出力・メトリクスのさらなる標準化（構造化ログ、Prometheus 等）

-----------------------------------------------------------------------------
保守・運用に関する不明点や追記希望があれば教えてください。必要に応じて履歴を追補します。