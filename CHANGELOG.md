# Changelog

すべての重要な変更点は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: 以下の変更点は提示されたコードから推測して作成しています。

## [Unreleased]

### Added
- run_monitoring 起動スクリプトを追加
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループを終了。
  - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する旨を明示。

- run_execution 起動スクリプトを追加
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB に分離して MockBroker を使用（本番 DB と完全分離）。
  - 停止フラグや PID ファイル管理をサポートし、別スレッドで ExecutionEngine を稼働。
  - 実行開始前に停止フラグが立っている場合は起動を中止。

- 環境設定・検証用 CLI を追加
  - config_setup: 対話式ウィザードで .env を初期作成 / 更新（シークレット入力、既存値の再利用、保存確認）。
  - validate_config: .env と config/*.yaml の基本的な整合性チェックを行う CLI。--strict オプションで警告を FAIL 扱いにできる。

- 環境変数自動読み込み機構を実装（kabusys.config）
  - プロジェクトルートを .git または pyproject.toml を基準に自動検出して .env / .env.local を読み込む（OS 環境変数を保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パーサは export プレフィックス、クォート（シングル/ダブル）内のバックスラッシュエスケープ、行末コメント処理などに対応。

- 設定オブジェクト（Settings）を追加
  - 各種設定（DB パス、API トークン、KABUSYS_ENV、LOG_LEVEL、監視閾値など）をプロパティとして取得・検証。
  - PAPER_FILL_MODE のバリデーションや paper_trading 用 sqlite パスの扱いを実装。

- ロギングユーティリティを追加（kabusys.utils.logging_setup）
  - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
  - 既存ハンドラを一度クリアして重複登録を防止、ログディレクトリ作成失敗時はファイル出力をスキップして警告。

- プロセス優先度 / CPU affinity ユーティリティを追加（kabusys.utils.process_priority）
  - Windows / POSIX の差分を吸収して set_process_priority, set_cpu_affinity を提供。
  - アクセス制限や未対応 OS では警告を出して安全にフォールバック。

- ポートフォリオ構築関連モジュールを追加（kabusys.portfolio）
  - portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - risk_adjustment: セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。
  - position_sizing: allocation_method（risk_based / equal / score）に基づく株数算出、単元株丸め（lot_size）、aggregate cap によるスケールダウン、コストバッファ考慮などを実装。

- Paper Trading 検証レポートツールを追加（kabusys.tools.paper_verification_report）
  - SQLite（paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し CLI でレポート出力。
  - 指標ごとの閾値（稼働率, 成功率, 送信率, P95 レイテンシ）を定義し PASS/FAIL 判定を行う。
  - --from / --to / --db オプションをサポート。

- research/factor_research の基礎実装（ファクター計算の定数・calc_momentum の設計開始）
  - モメンタム、MA、ATR、出来高系などの計算方針とパラメータを定義（DuckDB 経由で prices_daily / raw_financials を参照する設計）。

### Changed
- ログ出力の標準化
  - 起動スクリプト（monitoring / execution）共通で setup_logging を使用しログの一貫性を確保。
  - コンソールは stdout を使い、cron / scheduler 環境での取り扱いを考慮。

- DB 初期化の冪等化
  - run_monitoring と run_execution 起動時に init_monitoring_db を呼び出して監視テーブルの存在を保証（存在チェックと初期化の冪等性を想定）。

### Fixed
- MONITOR_POLL_INTERVAL の不正値対策
  - 環境変数で 0 以下や数値でない値が渡された場合、警告を出してデフォルト（60 秒）にフォールバック。

- .env パースにおけるコメント / クォート処理の不整合対策
  - クォート付き文字列内のエスケープ処理と、クォートなしでの行末コメント認識を実装して誤読を減らす。

---

## [0.1.0] - 初回リリース
（ライブラリ内での __version__ は "0.1.0"）

### Added
- 基本機能一式を初回リリース
  - 起動スクリプト: run_monitoring, run_execution
  - 設定管理: kabusys.config（.env 自動読み込み、Settings）
  - 設定関連 CLI: kabusys.config_setup（ウィザード）、kabusys.validate_config（検証）
  - ロギング / プロセス制御ユーティリティ: kabusys.utils.logging_setup, kabusys.utils.process_priority
  - ポートフォリオ構築ライブラリ: kabusys.portfolio（選定、重み付け、リスク調整、ポジションサイズ計算）
  - Paper Trading 検証ツール: kabusys.tools.paper_verification_report
  - 研究用ファクター計算の土台: kabusys.research.factor_research（モメンタム等の定義）

### Changed
- 初期リリースのため特記事項なし（上位での変更は Unreleased に記載）。

### Fixed
- 初期リリース向けに各種入出力・例外ケース（ログディレクトリ作成失敗、psutil 権限エラー、DB テーブル未作成など）に対するフォールバック処理を含め実装。

---

開発・運用における補足
- 本番環境（KABUSYS_ENV=live）では特に LINE 通知設定や Kill Switch の挙動を注意するよう validate_config で警告を出す設計になっています。
- 将来的な拡張メモ:
  - position_sizing の lot_size を銘柄別に拡張するための設計注釈あり。
  - risk_adjustment の価格欠損時のフォールバック（前日終値など）について TODO コメントあり。
  - research/factor_research の関数実装は継続中（スキャン期間、欠損データハンドリングの実装を予定）。

もし特定の変更点（例: 個別ファイルの差分やリリース日付）をより詳細に反映したい場合は、差分情報や希望のリリース日を教えてください。