# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

※本 CHANGELOG は提供されたソースコードから実装内容を推測して作成しています。

## [Unreleased]

- なし

---

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買フレームワーク「KabuSys」の基礎機能を実装しました。

### Added
- 全体
  - パッケージ基本情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - DuckDB / SQLite を利用したデータ保存・分析基盤の統合（Settings でパス指定）。
- 設定関連
  - 環境変数読み込み・管理モジュール（src/kabusys/config.py）
    - .env / .env.local の自動読み込み（プロジェクトルート検出ロジックあり）。
    - 強力な .env パーサ（コメント、export プレフィックス、クォート内のエスケープ処理などに対応）。
    - 環境変数取得ユーティリティ（必須変数チェックや各種設定プロパティを提供）。
    - 環境自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 対話式の .env 作成ウィザード CLI（src/kabusys/config_setup.py）
    - 各種設定項目の入力支援、既存 .env の読み込み・更新、保存機能。
  - 設定検証 CLI（src/kabusys/validate_config.py）
    - 必須環境変数・KABUSYS_ENV 値チェック、ログレベルチェック、DB パスや config/*.yaml の存在・パース確認、live 環境向けガード（LINE 通知や Kill Switch の注意）を実装。
    - --strict オプションで警告を失敗扱いにする機能を追加。
- 実行関連
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine の組み立てと起動ロジック（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler を連携）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（settings.paper_sqlite_path）を使い、本番 DB と分離（MockBrokerClient を利用する想定）。
    - 起動前に停止フラグ（data/stop_requested.flag）確認、pid ファイル管理、デーモンスレッドでの実行と安全な停止手順を実装。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor の一回チェックループを定期実行（MONITOR_POLL_INTERVAL 環境変数で間隔上書き、デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを記録。
    - 停止フラグ監視・例外保護・リソースクローズ処理を実装。
- ロギング・プロセス管理
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout ストリームハンドラ + 日次ローテートファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル / ログディレクトリの解決ルール（引数 > 環境変数 > デフォルト）。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収する set_process_priority、set_cpu_affinity を提供。
    - psutil を使い、権限不足や未対応 OS の場合は警告を出して安全にフォールバック。
- ポートフォリオ構築（pure functions）
  - 候補選定・重み算出（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア順で上位 N 件選定）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重配分、全スコア0 の場合は等金額配分にフォールバック）
  - セクター集中管理・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクター比率に基づき新規候補を除外）
    - calc_regime_multiplier（regime に応じた投下資金倍率、未知の値は警告のうえ 1.0 にフォールバック）
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes（risk_based / equal / score の配分方式、lot_size 単位切り捨て、aggregate cap によるスケールダウンと残差配分ロジック）
    - 各種パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization, cost_buffer 等）を受け取り可変戦略に対応
- モニタリング DB 初期化
  - init_monitoring_db を利用して監視テーブルの存在を保証（冪等処理） — run_execution/run_monitoring で呼び出し
- Paper Trading 検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からデータを読み込み、稼働率、注文成功率、送信率、P95 レイテンシ等を算出してレポートを生成。
    - 閾値（稼働率99%、成立率90%、送信率95%、P95 レイテンシ200ms）に基づく PASS/FAIL 判定。
    - クエリ実行時のテーブル未存在（OperationalError）を考慮したフォールバック処理を実装。
- リサーチ（実装の骨格）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum / Value / Volatility / Liquidity を計算する方針と一部定数を定義。DuckDB 接続を受ける設計。
    - 実装は関数群の骨格を含む（ファクター計算ロジックの一部が未完／継続実装想定）。

### Changed
- 初回リリースのため変更履歴はありません。

### Fixed
- .env パーサでのクォート内エスケープとインラインコメント処理を考慮することで、より堅牢な .env 読み込みを実現。
- ログディレクトリ作成失敗・ファイルハンドラ生成失敗時にアプリが致命的な例外で落ちないように保護。
- run_execution / paper_verification_report で DB テーブルが存在しない場合に例外で中断せずフォールバックする処理を追加。

### Known issues / Notes
- apply_sector_cap の価格欠損時（price == 0.0）はエクスポージャーが過小見積もりされる可能性があり、将来的に前日終値や取得原価等のフォールバック価格を使う TODO コメントあり。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄別 lot_map への拡張を想定した TODO コメントあり。
- process_priority / set_cpu_affinity は権限や OS に依存するため、失敗時は警告ログを出してスキップする設計になっています。
- factor_research.py はコメント・定数までは整備されていますが、ファクター計算ロジックの一部が未完の箇所（ソース末尾が途中で切れている）があります。今後完成予定。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使用します。監視データを環境に依存させたくない設計が反映されていますが、運用方針に応じて変更可能です。

---

照会・改善提案があればお知らせください。必要であれば各モジュールごとの詳細なリリースノート（関数一覧、CLI の使用例、既知の制限のチケット案）も作成します。