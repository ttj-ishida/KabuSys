CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/).
Released under semantic versioning.

Unreleased
----------

- -

[0.1.0] - 2026-04-19
--------------------

Added
- 初期リリース (バージョン 0.1.0)
- 実行スクリプト / エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。バックグラウンドスレッドでエンジンを実行し、停止フラグ (data/stop_requested.flag) を監視して安全に停止する。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、Paper Trading 用 DB を分離して利用する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。監視用 DB は環境に依らず本番 sqlite_path を利用する実装。
  - tools.paper_verification_report: ペーパートレード検証レポートを生成する CLI を追加。期間指定 (--from / --to) と DB パス指定 (--db) をサポートし、稼働率・注文成功率・送信率・レイテンシ（P95 等）を集計して PASS/FAIL 判定を行う。

- 設定・環境管理
  - config.py: Settings クラスを追加し、環境変数をプロパティとして安全に取得・検証する実装。主要な環境変数 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など) を必須扱いにし、KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の妥当性チェックを実施。
  - 自動 .env ロード機能を実装: プロジェクトルート（.git または pyproject.toml を基準）を検出して .env / .env.local を読み込み。OS 環境変数を保護する挙動、ロード無効化のための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加（シークレットマスク、選択肢、デフォルトの提示、.env テンプレート出力）。

- 設定検証
  - validate_config.py: 起動前に環境変数や config/*.yaml、DB パス等を検証する CLI を追加。--strict オプションで警告を FAIL 扱いにする機能や、KABUSYS_ENV=live 時の追加チェック（LINE 設定や Kill Switch の設定確認）を実装。

- 永続化・分析基盤
  - duckdb / sqlite の両方をサポート。duckdb は分析用、sqlite は監視・発注履歴用に使用。
  - monitoring_db の初期化ユーティリティを呼び出す処理を各エントリポイントで実行（冪等な初期化）。

- 実行コンポーネント（Execution サブシステム）
  - BrokerClientFactory によるブローカークライアント生産（Paper / Live 切替を想定）。
  - OrderRepository / OrderManager / Reconciler / RiskManager / ExecutionEngine の組み立てと実行フローを追加。RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を含む。
  - ExecutionEngine は PID ファイルの取り扱いや停止フラグ検知で安全停止可能。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: 候補選定 select_candidates、等金額/スコア加重の重み計算 calc_equal_weights / calc_score_weights（全銘柄スコアが 0 の場合は等金額にフォールバック）。
  - risk_adjustment: apply_sector_cap（セクター集中上限チェック）と calc_regime_multiplier（市場レジームに応じた投下資金乗数）。unknown セクターは上限対象外、未知レジームは 1.0 でフォールバック。
  - position_sizing: calc_position_sizes を実装。allocation_method に "risk_based" / "equal" / "score" をサポート。単元株（lot_size）で丸め、aggregate cap を超える場合にスケーリングして残差を lot 単位で配分するロジックを搭載。コストバッファ (cost_buffer) を考慮した保守的な見積りも実装。

- ロギングとプロセス制御ユーティリティ
  - utils.logging_setup.setup_logging: stdout (StreamHandler) と日次ローテート (TimedRotatingFileHandler) をルートロガーに設定。LOG_LEVEL / LOG_DIR の優先解決と、ログディレクトリ作成失敗時のフォールバック処理を実装。
  - utils.process_priority: psutil を用いたプロセス優先度設定 (Windows / POSIX の差分吸収) と CPU affinity 設定ユーティリティを実装。権限不足等は警告でスキップされる。

- 研究用モジュール（下準備）
  - research.factor_research: DuckDB を用いたファクター計算（Momentum / Value / Volatility / Liquidity）を想定した骨組みを追加。モメンタム計算等の定義（窓幅・スキャンレンジの定数）が含まれる（関数実装はモジュール内で継続実装予定）。

Changed
- パッケージ初期化:
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定し、主要サブモジュールを __all__ に列挙。

Fixed
- 初期実装として、ログ出力や環境読み込みの失敗時にプロセスが致命的に落ちないよう耐障害性を確保（ログディレクトリ作成失敗時はコンソールのみ、プロセス優先度設定の失敗は警告でスキップ、monitor.check_once() の例外はループ内で捕捉して継続）。

Notes / Known issues / TODOs
- research.factor_research の実装が途中（ファイル末尾で切れている関数の続きや完全なファクター出力処理が必要）。
- position_sizing: 各銘柄ごとの単元株サイズを将来的に stocks マスタから取得する設計へ拡張する旨の TODO コメントあり（現状は全銘柄共通 lot_size）。
- risk_adjustment.apply_sector_cap: price が欠損 (0.0) の場合にエクスポージャーが過少見積もられるリスクに関する注記。将来的に前日終値や取得原価でのフォールバックを検討中。
- Paper Trading と本番 DB の分離は想定済みだが、本番運用時の設定（LINE 通知、Kill Switch の取り扱い等）は validate_config による手動確認を推奨。

References
- リリース日: 2026-04-19
- 参照ソース: src/ 以下の初期実装群

[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0