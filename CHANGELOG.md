CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はコードベースの現状（このリポジトリのスナップショット）に基づく推定です。

[Unreleased]
------------

- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-04-19
-------------------

Added
- 基本アプリケーション構成を実装（初期リリース）。
  - パッケージメタ情報: kabusys.__version__ を "0.1.0" に設定。
- 起動スクリプトを追加。
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。KABUSYS_ENV に応じてペーパートレード用 DB を分離し、MockBroker を利用する構成をサポート。停止フラグ（data/stop_requested.flag）および PID ファイル管理に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視用 DB は本番 sqlite_path を使用。
- 設定管理と補助 CLI を追加。
  - config.py: .env 自動読み込み機能（.env/.env.local）、環境変数の取得ラッパー（Settings クラス）、各種設定値の検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を実装。
  - config_setup.py: 対話式 .env 作成ウィザードを実装。デフォルト値、シークレット入力、ファイル書き出しをサポート。
  - validate_config.py: 起動前チェック CLI を実装。必須環境変数・パス・config/*.yaml の存在とパース（PyYAML があれば）を検証。--strict オプションで警告を FAIL 扱いにできる。
- ログ・プロセス周りユーティリティを追加。
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と日次ローテーションされる TimedRotatingFileHandler を設定する setup_logging を実装。ログディレクトリ作成失敗時はファイル出力をスキップする堅牢性を持つ。
  - utils/process_priority.py: Windows と POSIX 系を吸収するプロセス優先度設定および CPU affinity 設定ユーティリティを実装。アクセス権限や未対応プラットフォーム時は警告を出して安全にスキップ。
- ポートフォリオ構築・リスク調整・ポジションサイジングの純関数群を実装（DB 非依存）。
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中の上限適用（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。unknown セクターはセクター上限の対象外として扱う。
  - portfolio/position_sizing.py: risk_based / equal / score の各配分方式に対応した株数計算ロジックを実装。単元株（lot_size）丸め、銘柄ごとの上限（max_position_pct）、全体の aggregate cap（available_cash）に基づくスケーリング、手数料・スリッページ考慮（cost_buffer）をサポート。端数処理では lot_size 単位の再配分を行う。
- 研究用モジュールとツールを追加。
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity の計画と一部実装。calc_momentum の実装が開始されている）。DuckDB を利用して prices_daily / raw_financials を参照する設計。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。期間フィルタ、稼働率・注文成功率・送信率・レイテンシ（平均 / 最大 / P95）を集計し PASS/FAIL 判定（閾値はソース内で定義）を出力。PAPER_TRADING_SQLITE_PATH 環境変数またはコマンドライン --db で DB を指定可能。
- 監視・ログ収集用 DB 初期化ヘルパーの呼び出しを統一。
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプト内で呼び出して監視テーブルの存在を保証（冪等）。
- モジュールの公開 API を整理。
  - portfolio パッケージ __init__.py で主要関数を明示的にエクスポート。

Changed
- なし（初回リリースのため該当なし）。

Fixed
- なし（初回リリースのため該当なし）。

Security
- なし特記。

Notes / 実装上の注意（推測）
- run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path（data/paper_trading.db がデフォルト）を使用し、本番 DB から完全に分離されたログ記録を行う設計。
- run_monitoring は環境に関係なく本番 sqlite_path を参照して監視情報を収集する設計（監視だけは本番 DB を使う想定）。
- 設定の自動ロードはプロジェクトルート検出 (.git または pyproject.toml) に依存する。CWD に依存せずパッケージ配布後も動作するよう配慮。
- env ファイルのパーサはクォート処理、エスケープ、インラインコメント処理などを考慮した堅牢な実装になっている。
- ログは stdout とファイル両方に出力され、ファイル出力は日次ローテーションかつ 30 日分保持される。ログディレクトリ作成に失敗した場合もコンソールログは継続される。
- process_priority / set_cpu_affinity は権限不足や未対応 OS でも安全に失敗するよう警告を出してスキップするため、運用側でのクラッシュを防ぐ設計。

Breaking Changes
- なし（初回リリース）。

Acknowledgements / TODO（今後の改善点・未実装箇所）
- research/factor_research.calc_momentum の実装が途中で終わっているように見える（コードスナップショットの末尾が途中）。ファクター計算の完全実装・テストが必要。
- position_sizing の価格欠損時（price==0.0）の扱いに関する TODO コメントあり。過去終値等のフォールバック戦略を導入することでより堅牢にできる。
- apply_sector_cap の警告ログや価格欠損時の挙動についてドキュメント化・単体テスト追加が望ましい。
- config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py）が参照されているため、ドキュメント化やテンプレートの整備を推奨。

--- 

参考: 本 CHANGELOG は提供されたコードベースの内容から機能・意図を推測して作成しています。実際の変更履歴やリリース日・バージョン運用方針は開発者側の記録に基づいて調整してください。