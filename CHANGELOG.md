# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
リリース方針: SemVer 準拠。

## [Unreleased]

## [0.1.0] - 2026-04-20
初回公開リリース。

### Added
- 実行エントリスクリプトを追加
  - run_execution.py — ExecutionEngine 起動スクリプト（プロセス優先度設定、DB接続、BrokerClientFactory によるブローカー生成、ExecutionEngine の起動と停止監視、停止フラグ / PID ファイルの取り扱い）。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数対応、停止フラグ検知、例外ハンドリング、監視 DB 初期化）。
- 環境設定・検証用ツールを追加
  - config_setup.py — 対話式 .env ウィザード（.env の生成・更新、デフォルト値・シークレット扱いのサポート）。
  - validate_config.py — 起動前の設定検証 CLI（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス／config YAML の存在チェック、--strict モード）。
- 設定管理
  - config.py — 自動 .env ロード（プロジェクトルート検出: .git または pyproject.toml）、.env / .env.local の読み込みルール（OS 環境変数を保護）、高度な .env パーサ（クォートやエスケープ、コメント処理）、Settings クラスによるプロパティアクセス（DB パス、paper trading 用パス、閾値、KABUSYS_ENV 判定など）。
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
- ロギング基盤
  - utils/logging_setup.py — ルートロガー設定ユーティリティを追加（stdout への StreamHandler、日次ローテートの TimedRotatingFileHandler、ログディレクトリ作成処理、環境変数/引数からのログレベル・ログディレクトリ解決、既存ハンドラのクリア）。
  - ログ出力は標準出力（stdout）を使用し、ファイル出力は logs/<app_name>.log（日次ローテーション、30日保持）。
- プロセス制御ユーティリティ
  - utils/process_priority.py — クロスプラットフォームでのプロセス優先度設定（Windows / POSIX 対応）、CPU affinity 設定ユーティリティ、権限不足時に警告してスキップする堅牢性。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - select_candidates — スコア降順・タイブレーク処理による候補選定。
    - calc_equal_weights / calc_score_weights — 等金額・スコア加重の重み算出（スコア総和が0の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap — セクター集中制限（既存保有を考慮して候補を除外、"unknown" セクターは除外しない挙動）。
    - calc_regime_multiplier — 市場レジームに応じた投下資金乗数（bull/neutral/bear 対応、未知レジームは警告の上フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes — allocation_method（risk_based / equal / score）に基づく株数決定、単元株（lot_size）丸め、per-position 上限・aggregate cap によるスケールダウン、cost_buffer による保守的コスト見積り、残差処理による追加配分ロジック。
  - portfolio/__init__.py で上記関数群を公開。
- ツール
  - tools/paper_verification_report.py — Paper Trading 検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）から以下指標を算出:
    - 稼働率（system_status）、ポーリング成功/失敗集計
    - 注文関連（trade_logs）から Created/Sent/Filled カウント、成功率・送信率
    - risk_logs からのリスク却下数
    - レイテンシ指標（avg / max / P95）および P95 算出ロジック
    - 基準値（稼働率・成功率・送信率・P95）を元に PASS/FAIL 判定とレポート出力
- 監視用 DB 初期化呼び出し
  - monitoring.monitoring_db.init_monitoring_db を run_execution と run_monitoring の起動時に呼び出し、監視テーブルが存在することを保証（冪等）。
- パッケージ情報
  - __init__.py にバージョン 0.1.0 を設定。

### Changed
- なし（初回リリースのため新規導入）。

### Fixed
- なし（初回リリースのため該当なし）。

### Notes / 実装上の注意点
- run_monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視データを記録する設計。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（data/paper_trading.db など）を使用して本番 DB と分離する想定。BrokerClientFactory により MockBrokerClient の使用が切り替わる。
- Settings.paper_fill_mode は有効値 ("instant","partial","never","reject") を検証する。
- .env パースはクォート内のバックスラッシュエスケープや行内コメントの解釈に対応（実用性重視の実装）。
- logging_setup はログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続する耐障害性を持つ。
- process_priority の設定は権限不足や未対応 OS の場合に警告してスキップする。CPU affinity は psutil の機能に依存。
- position_sizing と risk_adjustment にいくつかの注記（TODO）が存在:
  - price が欠損（0.0）の場合の扱いで過少見積りになる可能性（将来的に価格フォールバックを検討）。
  - lot_size は現状グローバル定数的扱いで、将来的に銘柄別拡張を想定。
- research/factor_research.py はファクター計算モジュールとして設計されているが、ファイル末尾に未完成箇所が存在する（実装継続の余地あり）。

### Security
- .env ファイルは絶対にコミットしない旨を config_setup の生成ヘッダに明記。

---

将来的に以下を予定:
- research モジュールの完全実装（ファクター計算の完成）
- ExecutionEngine / BrokerClient のテスト強化、Mock の整備
- 単体テストと CI の追加、ドキュメントの拡充（API 仕様、デプロイ手順等）

---------------------------------------------------------------------
参考: Keep a Changelog — https://keepachangelog.com/ja/1.0.0/