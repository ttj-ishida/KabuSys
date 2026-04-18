KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠しています。

Unreleased
- （なし）

0.1.0 — 2026-04-18
Added
- 初期リリースとして以下の主要機能を追加しました。
  - 実行/監視ランナー
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し MockBrokerClient と分離して動作します。スレッドでエンジンを実行し、data/execution.pid を PID ファイルとして扱います。停止フラグ（data/stop_requested.flag）検知時の安全停止処理を実装。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化します。
  - 設定管理
    - config.py: Settings クラスを導入し、環境変数/ .env ファイルからの設定取得を一元化。自動 .env ロード（.env, .env.local の順、OS 環境変数を保護）をサポート。PAPER_FILL_MODE 等のバリデーションや path プロパティ、env/log level 判定ロジックを実装。
    - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加（.env のテンプレート書き出し機能含む）。複数の設定項目（J-Quants、kabu、DB パス、LINE、ログ等）を対話的に入力可能。
    - validate_config.py: 起動前検証 CLI を追加。必須環境変数や KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML がある場合）パース検証、KABUSYS_ENV=live に対する追加ガード等を実装。--strict オプションで警告を失敗扱いにできます。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定（select_candidates）と等分配・スコア加重（calc_equal_weights, calc_score_weights）を実装。スコア全てが 0 の場合は等分配にフォールバック。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームはフォールバックで 1.0、ログ出力あり。
    - portfolio/position_sizing.py: position size 計算（risk_based / equal / score の配分方式）、単元切り上げ・aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料/スリッページ考慮）等を実装。lot_size 固定（将来的に銘柄別対応を想定する TODO コメントあり）。
    - portfolio/__init__.py で主要関数をエクスポート。
  - ユーティリティ
    - utils/logging_setup.py: 共通ロギング設定ユーティリティを追加。stdout ストリームハンドラと日次ローテート（TimedRotatingFileHandler）をルートロガーへ設定。LOG_DIR/LOG_LEVEL の解決ルール、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py: psutil を用いたプロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows/POSIX の差分を吸収し、権限不足時は警告を出して処理をスキップ。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成立率、送信率、レイテンシ（平均・最大・P95）等を集計し PASS/FAIL 判定を出力します。コマンドラインで日付レンジ指定 (--from/--to) と DB パス指定 (--db) が可能。デフォルト閾値は稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms。
  - 研究モジュール（計算基盤）
    - research/factor_research.py: DuckDB 接続を受けてモメンタム/Value/Volatility/Liquidity といったファクターを計算するためのモジュール（関数骨格・定数・仕様記述）を追加。DuckDB の prices_daily / raw_financials を参照する設計。
  - パッケージ情報
    - __init__.py にバージョン 0.1.0 を設定。

Changed
- 初期リリースの意図で、監視・実行それぞれで DB の取り扱いを明確化:
  - 監視: 環境にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用して監視テーブルを初期化します（init_monitoring_db を呼び出し）。
  - 実行: paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- .env 読み込みの挙動:
  - プロジェクトルートを .git または pyproject.toml で検出して .env/.env.local を自動ロード。既存の OS 環境変数は保護され、.env.local は .env を上書き可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いをサポートするよう拡張。

Fixed
- 実行・監視ループにおける堅牢性強化:
  - run_monitoring: check_once() 内で発生した例外はログに詳細を残して次ポーリングへ継続するようにキャッチ。停止フラグ（data/stop_requested.flag）検知で安全にループを抜ける。
  - run_execution: 起動前に停止フラグを検査して誤起動を防止。実行中は停止フラグ検知で engine.stop() を呼んで安全に終了。

Security
- config_setup が生成する .env ファイルに関して「絶対に Git にコミットしないこと」を明記するヘッダを追加（.env の取り扱いの注意喚起）。
- Settings._require() は必須環境変数未設定時に ValueError を投げ、起動前に問題が明示されるように。

Other notes / Internal
- ロギングはデフォルトで stdout に出力するように設定（cron/task scheduler 下でのリダイレクト運用を想定）。
- process_priority は権限不足や未対応 OS に対して警告を出し、動作を安全にスキップする実装。
- position_sizing と risk_adjustment の各モジュールに将来的な拡張（銘柄別 lot_size、価格フォールバック等）の TODO コメントを残しています。
- validate_config は PyYAML 未インストール時に YAML の検証をスキップし、警告を出す挙動。

Known limitations / TODO
- research/factor_research.py の実装は（ファイル末尾の切れが示すように）一部未完の箇所がある可能性があります。実環境での完全動作は追加実装/テストを推奨します。
- position_sizing の lot_size は現状共通固定。将来的に銘柄別単元対応が必要。
- apply_sector_cap の価格欠損時の取り扱い（0.0 を使うとエクスポージャーが過少見積もられる点）は TODO として注記されており、堅牢なフォールバック戦略を追加する予定です。

Acknowledgments
- 本リリースは初期機能群の整備に注力しており、運用に必要な CLI、ログ、設定、基本的なポートフォリオ構築ロジックおよび Paper Trading 向け検証ツールを含みます。今後のリリースでさらにユニットテスト・ドキュメント・未実装部の完成を予定しています。