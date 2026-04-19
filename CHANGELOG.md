# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
慣例により、重要な変更は分類（Added / Changed / Fixed / Security）しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初期リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理ツール、検証ツールなどを含みます。

### Added
- 起動スクリプト
  - run_execution.py: 実行エンジン（ExecutionEngine）を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に MockBrokerClient を利用し、paper_trading 用 SQLite（data/paper_trading.db）へ完全に分離して記録する挙動を実装。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイル管理・停止フラグ（data/stop_requested.flag）で安全に停止できる仕組みを提供。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を設定可能（デフォルト 60 秒）。
    - Monitoring は環境に依らず本番 sqlite_path を使用する（監視 DB の一貫性確保）。
    - 停止フラグ検出・例外保護・リソースクローズ処理を実装。

- 設定・環境管理
  - config.py: 環境変数/`.env` 管理を実装。
    - プロジェクトルート検出（.git または pyproject.toml に基づく）により .env の自動読み込みを行う。
    - .env 行のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - OS 環境変数を保護する仕組み（.env の上書き制御）をサポート。
    - 各種設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 関連など）を提供。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - .env の読み込み/上書き、秘匿項目のマスク表示、保存前の確認などを実装。
    - `.env` に絶対にコミットしない旨のヘッダを付与して書き出す。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在とパース（PyYAML があれば内容検証）などを実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング／プロセスユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ解決・作成時のフォールバックを実装（作成失敗時はファイルハンドラをスキップしてコンソールのみ出力）。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX (Linux/Mac/FreeBSD) に対応した優先度設定をラップ。
    - CPU affinity を最初の N コアに固定する機能を提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を提供。
    - スコアが全て 0 の場合に等配分へフォールバックする警告ロジックを含む。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を提供。
    - セクターが "unknown" の場合は制限を適用しない等の挙動を定義。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、ポジション上限・利用率上限、コストバッファ考慮の集約キャップとスケールダウンロジックを実装。
    - スケールダウン時の残差処理（fractional remainder に基づく追加配分）を実装。

- リサーチ
  - research/factor_research.py（計算ロジックの骨格を追加）
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクター計算を行う設計。モメンタム計算の定数・設計方針を定義（calc_momentum の実装を含む途中実装あり）。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。
    - Paper Trading 用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH または --db オプション）から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計し、閾値に基づく PASS/FAIL 判定を出力。
    - デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- ログ出力の設計方針
  - logging_setup が stdout を StreamHandler に使用するように決定（cron/スケジューラとのリダイレクト運用を想定）。
- DB 初期化の扱い
  - init_monitoring_db の呼び出しは冪等であり、監視テーブルが存在しない場合に作成することを明記。

### Fixed
- 環境変数パースの堅牢化
  - .env 行パーサーが export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを適切に処理するように改善（config._parse_env_line）。
- MONITOR_POLL_INTERVAL の堅牢化
  - run_monitoring のポーリング間隔取得で不正値（負数・ゼロ・非整数）に対して警告を出しデフォルト値にフォールバックする処理を実装。
- プロセス優先度設定のフォールバック
  - set_process_priority/set_cpu_affinity は権限不足や未対応 OS の場合に警告を出して失敗を安全にスキップするように改善。
- ログディレクトリ作成失敗時の動作安定化
  - ログディレクトリ作成に失敗してもプログラムは動作を継続し、コンソール出力のみで運用可能に。

### Security
- .env の扱いに関する注意書きを config_setup の書き出しファイルに含め、誤って Git にコミットしないよう促す文言を追加。

### Known issues / Notes
- research/factor_research.calc_momentum はファイル内で実装途中の箇所が存在します（骨格はあるが完全実装が必要）。将来のリリースで完成予定。
- apply_sector_cap: price_map に価格欠損（0.0）がある場合にエクスポージャーを過少評価する可能性がある旨の TODO コメントあり。フォールバック価格の導入を検討中。
- 一部の機能は外部モジュール（psutil, duckdb, PyYAML 等）に依存します。実行環境にこれらが揃っていることを確認してください。

---

変更履歴の追加・修正・詳細化を希望される場合は、どの機能・モジュールについて追記または分割したいかを教えてください。