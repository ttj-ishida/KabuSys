# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトのバージョンは `src/kabusys/__init__.py` の `__version__` によります。

---
## [Unreleased]

### Added
- run_monitoring 起動スクリプトを追加。
  - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
  - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループを終了。
  - Monitoring は環境（KABUSYS_ENV）にかかわらず本番用の `sqlite_path` を使用。
  - 起動時にプロセス優先度を "high" に設定。
  - DuckDB 接続を併用。

- run_execution 起動スクリプトを追加。
  - `KABUSYS_ENV=paper_trading` のときは MockBroker を利用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
  - 実行中の停止フラグ検知（data/stop_requested.flag）と PID ファイル出力（data/execution.pid）。
  - 実行エンジンを別スレッドで起動し、フラグ検知で安全に停止。

- 設定周りを充実化
  - `kabusys.config.Settings` クラスを追加し、環境変数（および .env 自動ロード）をラップ。
  - `.env` 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
  - `.env` のパースロジックを強化（export プレフィックス対応、クォートやバックスラッシュエスケープ対応、インラインコメント処理）。
  - `PAPER_FILL_MODE` の有効値チェック（instant/partial/never/reject）を実装。
  - `KABUSYS_ENV` / `LOG_LEVEL` 等の妥当性チェックを実装。

- 設定ユーティリティ
  - 対話式 .env 作成ウィザード `kabusys.config_setup` を追加（既存値の読み込み、シークレットマスク、選択肢・デフォルト対応、保存）。
  - 設定検証 CLI `kabusys.validate_config` を追加（必須環境変数、DB パス、config/*.yaml の存在/パース確認、`--strict` オプションで警告を FAIL として扱う）。

- ロギングとプロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続する耐障害性を実装。
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX の差分を吸収してプロセス優先度設定（high/normal/low）を行う。
    - CPU affinity を設定する `set_cpu_affinity` を追加。
    - 権限不足等で失敗した場合は警告を出して処理をスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定 / 重み計算: `portfolio.select_candidates`, `calc_equal_weights`, `calc_score_weights`。
  - セクター集中制限とレジーム乗数: `risk_adjustment.apply_sector_cap`, `calc_regime_multiplier`。
  - 株数決定・資金配分・単元丸め: `position_sizing.calc_position_sizes`。
    - risk_based / equal / score の各配分方式をサポート。
    - lot_size による丸め、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer を考慮した保守的見積り、端数配分ロジックを実装。
    - 価格欠損時のスキップや各種上限チェックを実装。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。paper_trading DB（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、レイテンシ）を集計し PASS/FAIL 判定を出力するスクリプトを提供。
  - P95 計算や日付フィルタ、欠損テーブルに対する耐性を実装。
  - デフォルト閾値（稼働率 99%、成立率 90% 等）を定義。

- 研究 / ファクター計算基盤（着手）
  - `kabusys.research.factor_research` にて DuckDB を用いたファクター計算の枠組みを追加（Momentum / Value / Volatility / Liquidity を想定）。関数インターフェースや定数を用意。

### Changed
- DB 初期化の自動化
  - 起動時に監視テーブルの存在を保証するため `init_monitoring_db` を呼び出すようにした（冪等に動作）。

- 実行フロー
  - どの起動スクリプトも最初にプロセス優先度を設定するよう統一。
  - run_execution は paper_trading 環境では専用 DB を使用して本番データと混ざらないように変更。

### Fixed
- 環境変数パースでの細かい不具合対策（クォートやエスケープ、コメント判定）により .env の柔軟性を向上。
- ログディレクトリ作成失敗時の例外ハンドリングを追加。ファイルハンドラ作成失敗時も起動継続。

### Notes
- モニタリングはあえて環境に依存せず「本番」用の sqlite_path を参照する設計です。開発時やテスト時は注意してください。
- `.env` は絶対にリポジトリに含めないでください（config_setup のヘッダでも注意喚起あり）。

---
## [0.1.0] - 2026-04-25

初回公開リリース。以下の主要機能を含みます。

### Added
- 基本アプリケーション構造の追加（パッケージ kabsys）。
- 起動スクリプト:
  - run_execution（ExecutionEngine 起動）
  - run_monitoring（SystemMonitor 起動）
- 環境設定 / ユーティリティ:
  - config (Settings クラス、.env 自動ロード/パース)
  - config_setup（対話式 .env ウィザード）
  - validate_config（設定検証 CLI）
- ログ・プロセス管理ユーティリティ:
  - logging_setup（標準化されたロギング設定）
  - process_priority（優先度 / CPU affinity 設定）
- ポートフォリオ構築モジュール:
  - portfolio_builder（候補選定・重み付け）
  - position_sizing（株数計算、資金配分）
  - risk_adjustment（セクターキャップ、レジーム乗数）
- Paper Trading 検証ツール（tools.paper_verification_report）
- 研究用ファクター計算の下地（research.factor_research、DuckDB ベースの設計）
- DuckDB を分析用途に組み込むための接続コードを追加。

### Changed
- 監視/実行スクリプトがログセットアップとプロセス優先度設定を起動時に行うように統一。
- Paper Trading 用の DB を分離して本番 DB に影響を与えない設計。

### Fixed
- .env 読み込み処理の堅牢化（ファイル読み込み失敗時の警告等）。

### Removed
- （このリリースでは削除はありません）

---

セマンティックバージョニングに基づく今後の方針
- 小さな後方互換性のない変更はメジャーを上げる（1.x → 2.0.0）前に CHANGELOG に明示します。
- バグフィックスや小さな改善はマイナー/パッチに反映します。

貢献・バグ報告
- バグや改善提案は issue にて報告してください。報告の際は再現手順、環境（KABUSYS_ENV、.env の設定の概略）、ログ抜粋を添えてください。