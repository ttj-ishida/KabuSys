# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。重要な変更点・追加点・既知の挙動をコードベースから推測してまとめています。

## [Unreleased]
- （現在なし）

## [0.1.0] - 2026-04-19
初期リリース。自動売買システム KabuSys の基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- 起動スクリプト / 実行系
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。環境に応じて本番 DB またはペーパートレード専用 DB を使用する。
    - KABUSYS_ENV=paper_trading 時は Paper Trading 用の SQLite（既定: data/paper_trading.db）を用い、MockBrokerClient を利用する設計を想定。
    - 停止制御のための stop flag（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱う。
    - スレッドで ExecutionEngine を動作させ、停止フラグ検知時に安全に停止するループを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 停止フラグの検知、例外発生時のロギング、KeyboardInterrupt による終了処理、DB接続のクローズを実装。
    - Monitoring は環境にかかわらず本番の sqlite_path を参照する仕様（監視用 DB の共通化）。

- 設定管理・初期化 CLI
  - config.py
    - 環境変数のラッパー Settings を追加。各種設定（DB パス、KABUSYS_ENV、ログレベル、各種しきい値、ペーパートレード関連設定等）をプロパティとして提供。
    - .env の自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml ベース）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH の分離等の設定を追加。
  - config_setup.py
    - .env 作成・更新の対話式ウィザードを追加。主要な環境変数を対話的に入力し .env を生成・上書きできる。
    - 既存 .env 読み込み、シークレット項目のマスク表示、保存の確認を実装。
  - validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数、KABUSYS_ENV 値、DB パス、config/*.yaml の存在とパース（PyYAML がある場合）等を検証可能。
    - --strict モードで警告も失敗（exit 1）扱いにできる。

- ロギング・ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）をルートロガーに設定する。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。
    - ログレベル・ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。
- プロセス制御ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定（set_process_priority）を追加。Windows / POSIX（Linux, Darwin, FreeBSD）を吸収して適切に nice/priority を設定。
    - CPU affinity を設定する set_cpu_affinity を提供（存在しない環境や権限不足時は警告を出してスキップ）。
- ポートフォリオ構築（純関数）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。
    - スコア合計が 0 の場合に等配分へフォールバックする警告を追加。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（当日売却予定銘柄の除外、"unknown" セクターは上限適用除外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: risk_based / equal / score 対応）。
    - 単元株丸め（lot_size）や 1銘柄上限、aggregate cap（available_cash を超えた場合のスケーリングと残差処理）を実装。
    - cost_buffer による保守的見積りを導入。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI を追加。期間フィルタ (--from / --to)、DB パス指定（--db / 環境変数）に対応。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計し、しきい値に基づく PASS/FAIL 判定を出力。
    - P95 計算、レイテンシ集計、テーブル存在しない場合のフォールバック処理を実装。
- 研究用モジュール（未完だが基盤実装）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（モメンタム、MA200乖離、ATR、出来高関連等の計算方針と定数を定義）。
- パッケージメタ
  - __init__.py にてバージョンを "0.1.0" に設定。

### Changed
- 設計/運用上の注意点（ドキュメント的に明記）
  - monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使うことを明記（監視 DB の分離ポリシー）。
  - run_execution は paper_trading 環境で DB を完全に分離する仕様により、本番 DB へ誤って書き込まれないよう配慮。

### Fixed
- 環境変数パーサの堅牢化
  - config._parse_env_line にて:
    - export KEY=... 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなし時のインラインコメント扱い改善（# の前がスペース/タブでコメントと認識）
  - .env 読み込みで OS 環境変数を保護する仕組みを導入（protected set）。

### Security
- シークレット項目の取り扱い
  - config_setup の対話表示でシークレットはマスク表示（"****"）されるように実装。
  - .env の自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Migration
- .env の自動ロードは既定で有効。テストや CI などで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかでなければ ValueError を送出します。既存の環境変数がこれらに該当するか確認してください。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のいずれかである必要があります（不正値は例外）。
- ログ出力先（logs/）の作成に失敗した場合はファイル出力が無効化され、コンソールのみでの運用になります。ログディレクトリの権限設定を確認してください。

---

（以上）