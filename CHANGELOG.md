# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」ガイドラインに従います。

変更履歴のフォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

※ 日付はこのコードベースのスナップショット作成日です。

## [Unreleased]

- ドキュメントやテストケースの追加予定メモ
- research/factor_research.py のファクター計算機能は基盤実装あり（calc_momentum 等）だが、実装途中の箇所あり。精査・完成予定。
- TODO コメントにある拡張（銘柄ごとの lot_size 管理、価格フォールバックなど）の実装予定。

---

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ情報を追加
  - src/kabusys/__init__.py にバージョン情報 `__version__ = "0.1.0"` を設定。

- 環境設定・読み込み機能
  - .env 自動読み込み機構を追加（プロジェクトルートを .git / pyproject.toml から検出）。参照: src/kabusys/config.py
  - .env ファイルの安全なパース機能を実装（クォート・エスケープ・コメント処理対応）。
  - 必須環境変数取得時の例外発生処理を追加（_require 関数）。

- 環境設定支援 CLI
  - 対話式ウィザードで .env を生成・更新する CLI を追加。使用例: `python -m kabusys.config_setup`（src/kabusys/config_setup.py）。
  - ウィザードは既存 .env の読み込み・マスク表示・選択肢やデフォルトのサポートを提供。

- 設定検証 CLI
  - .env と config/*.yaml の事前検証を行う `validate_config` CLI を追加。`--strict` オプションで警告を失敗扱いにできる（src/kabusys/validate_config.py）。

- 実行系スクリプト
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合、mock ブローカーを使い paper_trading 用 DB に記録して本番 DB と分離。
    - プロセス優先度を起動時に "high" に設定する処理を実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイルによる停止制御を実装。
    - duckdb 接続を受け取る設計。

  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ検知でループを終了する仕組みを実装。

- 監視 DB 初期化
  - 監視テーブルを冪等に保証する init_monitoring_db 呼び出しを各起動処理内に組み込み（monitoring モジュールとの連携点を用意）。

- ロギング基盤
  - 統一的なロギングセットアップユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（デフォルト logs/、30日分保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を定義し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

- プロセス優先度 / CPU affinity ユーティリティ
  - set_process_priority と set_cpu_affinity を実装（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収する実装。
    - アクセス権や未サポート機能に対しては警告を出してスキップ。

- ポートフォリオ構築ライブラリ
  - 候補選定および重み計算: select_candidates, calc_equal_weights, calc_score_weights（src/kabusys/portfolio/portfolio_builder.py）。
    - スコア昇順・同点のタイブレーク等を明示。
  - セクター制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター別エクスポージャ計算とブロックロジック、レジームに応じた乗数（bull/neutral/bear）を提供。
  - 発注株数計算（ポジションサイジング）: calc_position_sizes（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の配分方式対応、単元株（lot_size）丸め、aggregate cap（利用可能現金とのスケール調整）、コストバッファ考慮。
    - 投資上限・最大利用率・stop loss 等のパラメータを受け取る柔軟な設計。
  - 上記をまとめたパッケージエクスポートを追加（src/kabusys/portfolio/__init__.py）。

- Paper Trading 検証ツール
  - Paper Trading の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - 日付フィルタ、DB パス引数/環境変数対応をサポート。

- 研究用ファクター計算（基盤）
  - ファクター計算モジュールの骨子を追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity の設計方針と計算パラメータを定義。DuckDB 経由で prices_daily / raw_financials を参照する設計。

### Changed
- 起動処理の安全性向上:
  - 起動直後にプロセス優先度を設定することで、実行中の優先度を確実に確保。
  - 監視プロセス（monitoring）は環境にかかわらず本番 sqlite_path を使用する旨を明示（安全運用のための設計決定）。

### Fixed
- 環境変数パースとロード時の堅牢性改善（コメント/クォートの扱い、export プレフィックス対応など）。
- MONITOR_POLL_INTERVAL に不正な値が設定された場合のフォールバックと警告ログを追加（run_monitoring.py）。

### Known issues / Notes
- apply_sector_cap: price が 0.0 の場合にエクスポージャが過小見積もられる旨の TODO コメントあり。将来的に前日終値や取得原価などでフォールバックすることを検討中（src/kabusys/portfolio/risk_adjustment.py）。
- position_sizing: 将来的な拡張として銘柄別の lot_size をサポートする設計を想定する TODO コメントあり（src/kabusys/portfolio/position_sizing.py）。
- research/factor_research.py は基盤実装があるが一部実装途中（ファイル末尾で途切れた箇所あり）。実用化前に追加実装と検証が必要。

### Security
- .env は絶対に Git にコミットしない旨を config_setup の生成コメントに明記（src/kabusys/config_setup.py）。

---

以上。ソースコードの内容から推測して CHANGELOG を作成しました。必要なら各項目をより詳しく、あるいは別バージョン分けして記述できます。どの程度の粒度で履歴を残したいか教えてください。