CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正 / 堅牢性向上
- Docs: ドキュメント改善 / CLI ヘルプ等

Unreleased
----------
（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-21
-----------------

Added
- 基本アプリケーション構成を実装
  - パッケージエントリポイントとバージョンを追加 (src/kabusys/__init__.py, __version__ = "0.1.0")。

- 環境設定・読み込み
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。未検出時は自動ロードをスキップ（src/kabusys/config.py）。
  - .env 行パーサを強化して、export プレフィックス・クォート（シングル/ダブル）・バックスラッシュエスケープ・行内コメント扱いをサポート（src/kabusys/config.py）。
  - Settings クラスを実装し、環境変数からアプリ設定を一元取得（DBパス、APIトークン、KABUSYS_ENV、ログレベル、監視閾値、Paper Trading の設定などをプロパティ化）。

- 設定ウィザード & 検証 CLI
  - 対話式 .env 作成/更新ウィザードを追加（python -m kabusys.config_setup）。既存値の読み込み、シークレットマスク表示、保存確認をサポート（src/kabusys/config_setup.py）。
  - 設定検証ツールを追加（python -m kabusys.validate_config）。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DBパス親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML が無ければスキップ）、本番用ガード（LINE通知設定や Kill Switch 設定の警告）を実施。--strict モードで警告もエラー扱いにできる（src/kabusys/validate_config.py）。

- 実行プロセス起動スクリプト
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - Broker クライアントファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動ロジックを実装。
    - 停止フラグ（data/stop_requested.flag）検知で安全停止、実行用 pid ファイル path を扱う。
    - プロセス優先度を "high" に設定（起動直後）。
    - duckdb 接続を利用（分析用）。

- 監視プロセス起動スクリプト
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様（監視は本番 DB を参照）。
    - stop flag 検出でループ終了、check_once() の例外をログして継続、KeyboardInterrupt をハンドルしてグレースフルに終了。
    - sqlite3 と duckdb の両方で接続を行い終了時にクローズ。

- ロギング / プロセス制御ユーティリティ
  - 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と、日次ローテート（30日保持）の TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソールのみで継続するフォールバック。
    - LOG_LEVEL / LOG_DIR の解決ルールを明示。
  - プロセス優先度・CPU アフィニティ設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/macOS の違いを吸収して優先度設定を試みる。psutil の権限エラー等は警告してスキップ。
    - set_cpu_affinity によるコアピニングをサポートし、利用不可時は警告。

- ポートフォリオ構築モジュール
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、signal_rank をタイブレーク）
    - calc_equal_weights（等金額）
    - calc_score_weights（スコア比率、総スコアが 0 の場合は等金額にフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存ポジションのセクター比率に応じて候補を除外、"unknown" セクターは制限外）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" の乗数マップ、未知レジームは警告して 1.0 フォールバック）
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の配分方式を実装
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を使った保守的見積り、残余キャッシュに対する再配分ロジックを実装
    - 価格欠損時のスキップやログ出力に配慮

- リサーチ（ファクター計算）基盤
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity 設計方針と定数を定義。DuckDB を使って prices_daily / raw_financials を参照して計算する設計（calc_momentum 等の実装開始）。

- Paper Trading 検証レポート
  - paper_verification_report CLI を追加（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95））を集計してレポート出力。
    - P95 計算実装、閾値による PASS/FAIL 判定、DB 存在チェックとユーザ向けメッセージ。

Changed
- DB 初期化/監視テーブル
  - run_execution/run_monitoring の起動時に init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。監視テーブルが存在しない場合でも起動時に作成する仕様に変更（src/kabusys/run_* に反映）。

- ログ出力先の標準化
  - ログは stdout に出力する方針を採用（cron / スケジューラからの扱いを考慮）。ファイル出力はオプション的に日次ローテーションで行う（src/kabusys/utils/logging_setup.py）。

- 環境依存の DB 分離
  - 実行エンジンは paper_trading 環境のときに専用 SQLite（data/paper_trading.db）を使用する挙動を明確化。監視は常に本番監視 DB を使用する設計（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）。

- MONITOR_POLL_INTERVAL の取り扱い
  - MONITOR_POLL_INTERVAL を文字列→整数に変換し、0 以下や不正値はログ警告のうえデフォルト（60 秒）にフォールバックする仕様を追加（src/kabusys/run_monitoring.py）。

Fixed
- エラーハンドリング強化
  - SystemMonitor のポーリングループ内で check_once() が例外を出してもループを継続するよう例外捕捉し、詳細をログに出力することで監視のレジリエンスを向上（src/kabusys/run_monitoring.py）。
  - run_execution のエンジンスレッド監視中に停止フラグを検出すると engine.stop() を呼んで安全停止する処理を追加（src/kabusys/run_execution.py）。
  - logging_setup: ログディレクトリの作成に失敗した場合にファイルハンドラ作成をスキップし、コンソール出力のみで継続するフォールバックを実装。ファイルハンドラ生成失敗時もログに警告（src/kabusys/utils/logging_setup.py）。
  - process_priority / set_cpu_affinity: psutil の AccessDenied/NotImplemented 等の例外を警告して処理をスキップ、クロスプラットフォームで安全に動作するように改善（src/kabusys/utils/process_priority.py）。
  - paper_verification_report: DB が存在しない場合の説明メッセージを追加し、SQLite 接続エラー（テーブルが無いなど）を捕捉してデフォルト値でレポートを作る（src/kabusys/tools/paper_verification_report.py）。
  - .env ローダ: 読み込み失敗時に warnings.warn を出し、処理を継続するように変更（src/kabusys/config.py）。
  - validate_config: PyYAML が未インストールの場合に YAML 検証をスキップして警告する挙動を追加し、パース失敗時はエラー収集に貯めるよう改善（src/kabusys/validate_config.py）。

Docs
- 各モジュールに詳細な docstring / 使用例 / 設計コメントを追加（config, config_setup, validate_config, run_monitoring, run_execution, logging_setup, portfolio/*, research/*, tools/* 等）。これにより開発者が各コンポーネントの目的と使い方を把握しやすくなった。

Notes / Known limitations
- factor_research.calc_momentum などファクタ計算モジュールは設計方針と定数が整備されているものの、実装が途中の関数が存在する可能性があります（まだ DuckDB SQL 部分の完成が必要）。
- position_sizing の lot_size は全銘柄共通の実装。将来的に銘柄別 lot_size を持たせる拡張がコメントに記載されている。
- apply_sector_cap の exposure 計算は price が欠損（0.0）の場合に過少見積りとなる可能性がある旨の TODO コメントあり。フォールバック価格導入の余地あり。

---

今後のリリース案（例）
- factor_research の各ファクター完全実装と単体テスト追加
- ExecutionEngine / BrokerClient の統合テスト（Paper / Live 切替の E2E）
- 各関数群のユニットテスト（portfolio, position_sizing のエッジケース）
- ログ周りの CI 環境での動作確認（ログディレクトリ作成失敗時のハンドリング）

（終）