CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/).

[0.1.0] - 2026-04-22
--------------------

Added
- 初回リリース (バージョン 0.1.0)。
- 基本アーキテクチャ・起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。起動時にプロセス優先度を設定し、スレッドでエンジンを実行。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱う。
  - run_monitoring: SystemMonitor のポーリングループを実行するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能。監視用 DB は環境にかかわらず本番 sqlite_path を使用。
- 設定管理・セットアップ・検証
  - config: 環境変数読み込み・ラッパー Settings を実装。自動 .env ロード（プロジェクトルートは .git または pyproject.toml を基準）。必須値取得、型チェック、複数設定項目（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、閾値等）を提供。
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援。シークレットはマスクして表示。生成結果を .env に書き出す。
  - validate_config: 起動前検証 CLI を追加。必須環境変数や KABUSYS_ENV、DB パス、config/*.yaml の存在・パース（PyYAML があれば内容検査）や本番向けガードをチェック。
- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup: stdout 用 StreamHandler と 日次ローテートの TimedRotatingFileHandler を設定する共通ユーティリティを追加。ログディレクトリ作成失敗時のフォールバック動作あり。
  - utils.process_priority: Windows / POSIX を吸収したプロセス優先度設定、CPU affinity 設定ユーティリティを追加。権限不足や未対応プラットフォーム時は警告してスキップ。
- ポートフォリオ構築関連モジュール
  - portfolio.portfolio_builder: シグナル選定 (select_candidates)、等重配分 (calc_equal_weights)、スコア重み配分 (calc_score_weights) を追加。score が全て 0 の場合は等重へフォールバック。
  - portfolio.risk_adjustment: セクター集中制限 (apply_sector_cap) と市場レジームに基づく乗数 (calc_regime_multiplier) を実装。unknown セクターの扱い、レジーム未登録時のフォールバックが含まれる。
  - portfolio.position_sizing: 各銘柄の発注株数計算を実装（risk_based / equal / score）。単元株（lot_size）で丸め、per-stock 上限・aggregate cap（利用可能現金）でスケールダウンし、残余キャッシュを考慮して端数を補正するロジックを実装。
- Paper Trading 向けツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計し PASS/FAIL を判定。--from/--to/--db オプション対応。閾値はソースで定義（稼働率 99% 等）。
- Research（下地）
  - research.factor_research: ファクター計算モジュールの骨組みを追加（モメンタム、ボラティリティ等の計算方針と定数を含む）。DuckDB 接続を受け取り SQL/Python で計算する設計。

Changed
- ログ出力
  - ログはデフォルトで stdout に出力するように統一（cron 等でリダイレクトしやすくするため）。ファイル出力は logs/<app_name>.log に日次ローテーションで保存（バックアップ 30 日）。
- 環境变量ロードの優先順位
  - OS 環境変数 > .env.local > .env の順でロード。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- データベース分離（Paper Trading）
  - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（data/paper_trading.db がデフォルト）を使用し、本番 DB と完全に分離。

Fixed
- 環境変数の堅牢なパース
  - .env パーサが export プレフィックス、シングル/ダブルクォート内のエスケープ、行末コメントの扱いなどに対応。無効行は無視。
- 監視ループの回復性
  - monitor.check_once() 実行中に例外が発生した場合でもログ出力して次のポーリングまで待機するようにして、監視プロセスが落ちにくくなった。
- MONITOR_POLL_INTERVAL のバリデーション
  - 環境変数 MONITOR_POLL_INTERVAL が不正（整数変換失敗や 0 以下）の場合、警告を出してデフォルト（60 秒）へフォールバック。

Notes
- 設計上のセーフガード
  - validate_config による起動前チェックや run_execution/run_monitoring の停止フラグ・PID 管理など、誤操作や本番稼働時の安全装置を備えています。
- DuckDB / SQLite の扱い
  - 分析用途に DuckDB、監視・トレードログ等に SQLite を利用する設計。Paper Trading では別 SQLite を推奨。
- 未実装 / 今後の課題
  - research.factor_research は設計と定数を含むが一部実装が継続中（calc_momentum の実装途中など）。
  - position_sizing の価格フォールバック（前日終値や取得原価）や lot_size の銘柄別対応は TODO コメントあり。

Meta
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に対応。

--- 

今後のリリースでは、factor_research の完全実装、Strategy/Execution の統合テスト、より細かいログ・メトリクスの追加、銘柄ごとの単元対応などを検討しています。