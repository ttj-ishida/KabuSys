# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠します。

## [Unreleased]

- 今後の変更をここに記載します。

## [0.1.0] - 2026-04-19

初期公開リリース。以下の主要機能・ユーティリティを実装しました。

### Added
- 実行/監視起動スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は専用の paper trading 用 SQLite を使用し、Mock ブローカーを利用する設計をサポート。
  - run_monitoring.py: SystemMonitor をポーリングで実行する監視スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
  - 両スクリプトで停止フラグ（data/stop_requested.flag）を監視し、PID ファイルやプロセス優先度設定に対応。

- 設定/環境管理
  - config.py: 環境変数と設定の読み取りを集中管理する Settings クラスを追加。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等の既定値と取得ロジックを実装。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV のバリデーション、ログレベルの検証などを実装。
    - プロジェクトルート探索を行い .env/.env.local の自動読み込み（OS 環境変数を保護して上書き制御）。
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加（secret マスク、確認プロンプト、保存機能）。
  - validate_config.py: 起動前に .env や config/*.yaml の妥当性を検証する CLI を追加。`--strict` オプションで警告を FAIL 扱いに可能。

- ポートフォリオ構成ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのソート/上位選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア重み計算（スコア合計が 0 の場合のフォールバックを含む）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションの時価ベースで計算、売却予定銘柄除外、"unknown" セクターは除外しない仕様）。
    - calc_regime_multiplier: マーケットレジームに応じた資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 等配分・スコア配分・リスクベース配分をサポート。単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に収めるためのスケーリング）、cost_buffer を考慮した安全な発注株数算出。

- ユーティリティ
  - utils/logging_setup.py:
    - 統一ロギング設定ユーティリティを追加。StreamHandler（stdout）と日次ローテートの TimedRotatingFileHandler（デフォルト logs/）をルートロガーへ設定。ログディレクトリ作成失敗時のフォールバックやログレベル解決ロジックを実装。
  - utils/process_priority.py:
    - プラットフォームを抽象化したプロセス優先度設定と CPU affinity 設定を追加。Windows / POSIX の差分を吸収し、権限不足などで失敗しても警告ログでスキップする堅牢な実装。

- 分析・検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し PASS/FAIL 判定を行う。
    - レポート出力と日付フィルタ（--from / --to）、DB パスの引数または環境変数による指定に対応。
    - デフォルトの基準値（稼働率 99% など）を定義。

- 研究モジュール（骨組み）
  - research/factor_research.py:
    - 定量ファクター（Momentum/Value/Volatility/Liquidity）の計算方針と一部定数を追加。DuckDB を使った prices_daily / raw_financials 参照を想定した実装方針を明記（関数の部分実装あり）。

- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- .env 読み込みの挙動を明確化
  - OS 環境変数を保護する仕組み（protected set）を導入し .env/.env.local の読み込み順と上書きルールを定義。
  - export KEY=val 形式やクォート・エスケープ、インラインコメント処理に対応した .env パーサを実装。

- ログ出力の標準化
  - 全起動スクリプトが setup_logging を最初に呼ぶようにし、統一されたログ形式・ローテーションを使用。

### Fixed / Robustness
- ファイル/ディレクトリ作成失敗や外部ライブラリ未インストール時に graceful に振る舞うよう改善
  - logging_setup: ログディレクトリ作成に失敗した場合はファイルハンドラをスキップして stdout のみで継続。
  - validate_config: PyYAML 未インストール時に YAML 検証をスキップして警告を出す。
  - process_priority: 権限不足などで優先度設定できない場合は警告でスキップ。
  - run_execution / run_monitoring: DB 接続とクローズを finally ブロックで保証。例外時にもリソースがクリーンに解放されるように実装。

### Security
- .env ファイル生成時にシークレット項目をマスクして扱う（config_setup）。
- .env の取り扱いに関する注意書きを .env に出力（Git にコミットしない旨の警告）。

### Notes / Known limitations
- 一部モジュールは依存コンポーネント（ExecutionEngine, BrokerClient, SystemMonitor, monitoring_db など）の実装を前提としており、今回のリリースではインターフェース/起動用ラッパや純粋関数群を中心に実装しています。
- research/factor_research.py は計算方針と一部実装を含むが、完全実装は今後の作業対象です（コード末尾が途中で切れている箇所あり）。
- apply_sector_cap: price_map に価格が欠損した場合のフォールバックロジックは TODO として注記してあります（将来的な拡張予定）。

---

セマンティックバージョニング: 0.1.0 は初期公開リリースです。今後の機能追加や API 変更はメジャー/マイナー/パッチに従って記録します。