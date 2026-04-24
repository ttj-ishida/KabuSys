CHANGELOG
=========

All notable changes to this project will be documented in this file.
このファイルは Keep a Changelog の形式に準拠しています。
詳細: https://keepachangelog.com/ja/1.0.0/

unreleased
----------

0.1.0 - 2026-04-24
------------------

Added
- 初期公開（0.1.0）。主要な機能群と CLI を実装。
- 起動スクリプト / デーモン
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 停止判定はプロジェクト直下の data/stop_requested.flag ファイルで行う。
    - Monitoring は KABUSYS_ENV に依らず本番用 sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用のペーパートレード DB を使用（data/paper_trading.db がデフォルト）および MockBrokerClient の利用が想定される。
    - 実行中は PID ファイルを管理し、stop フラグ検知で安全に停止する仕組みを実装。
- 設定管理 / 設定支援
  - config.py: 環境変数読み込み・Settings クラスを実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env, .env.local を優先順でロード）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - .env パーサは export 構文、引用符付き値、インラインコメント対応など堅牢に実装。
    - 各種設定プロパティ（DB パス、PID ファイル、しきい値、環境種別判定、Paper Trading 用挙動など）を提供し、値検証を行う。
  - config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成・更新を支援）。
    - 必要項目・選択肢・シークレット入力のサポート、既存 .env の読み込み、保存確認画面を実装。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス・YAML ファイルの存在確認、live 環境向けの追加注意喚起などを行う。
    - --strict オプションで警告も FAIL 扱いに可能。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR / app_name による設定解決をサポート。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows/Linux/Mac(一部) を吸収。psutil を用いて優先度設定／CPU 固定を試み、失敗時は警告でスキップ。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナルの候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア全てが 0 の場合は等金額配分にフォールバックする挙動を含む。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（unknown セクターは制限対象外）。
    - 市場レジームに基づく乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" とフォールバック）。
  - portfolio/position_sizing.py
    - ポジションサイズ算出 calc_position_sizes を実装。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）、cost_buffer を考慮した保守的見積り、残余配分ロジック等を実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を算出し、Pass/Fail を判定する閾値を定義。
    - コマンドラインで期間指定 (--from / --to) や DB 指定 (--db) が可能。
- 研究モジュール（作業中）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（モメンタム・MA200・ATR 等、DuckDB 経由での計算設計）。
    - 実装は開始済み（ファイル末尾が途中で切れているため継続作業が必要）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / Implementation details
- run_monitoring と run_execution はプロセス優先度を "high" に設定してから各種初期化を行う設計（utils.process_priority.set_process_priority を利用）。
- .env の自動読み込みでは OS 環境変数を保護（既存の環境変数を上書きしない／.env.local での上書きは許可）する仕組みを導入。
- validate_config は PyYAML がインストールされていない場合、YAML の内容検証をスキップして警告を出すようになっている（外部依存の緩和）。
- Paper Trading（is_paper）判定に基づき、run_execution は paper_sqlite_path を使用して本番データとの分離を担保する。
- logging_setup はファイルハンドラ作成失敗時でもコンソール出力で動作を継続するため、運用環境でログ保存に失敗してもプロセス自体は影響を受けにくい。

Known issues / TODO
- research/factor_research.py が途中で切れており、完全実装に至っていない（継続実装が必要）。
- position_sizing の価格欠損時の挙動（price が 0 の場合のフォールバック）は TODO コメントあり。前日終値等のフォールバックロジックの検討が推奨される。
- 一部の外部機能（BrokerClientFactory、ExecutionEngine 等）は実装ファイルに依存しており、環境に応じたモック／実ブローカーの用意が必要。

作者
- KabuSys チーム

---