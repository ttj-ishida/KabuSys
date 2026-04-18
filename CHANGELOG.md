CHANGELOG
=========

すべてのリリースに関しては Keep a Changelog の指針に準拠しています。
日付はコードベースの作成時点（ソース内のコメントやデフォルト値等）から推測して付与しています。

[Unreleased]
------------

- 開発中の小幅修正・内部改善を反映（詳細はコミットログ参照）。

0.1.0 - 2026-04-18
-----------------

Added
- 実行・監視の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の Paper Trading SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する設計を想定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用 sqlite_path を使用する仕様。

- 設定関連ユーティリティ
  - config.py: 環境変数・設定管理クラス Settings を追加。.env 自動読み込み機能を備え、.env / .env.local の優先順位（OS 環境変数を保護）を実装。PAPER_FILL_MODE や各種パス／閾値等のプロパティを提供。
    - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
    - .env 行パーサは export 形式、引用符／エスケープ、インラインコメントを考慮して安全にパース。
  - config_setup.py: .env 作成・更新の対話式ウィザードを追加。各設定項目の説明・デフォルトを表示して .env を生成可能。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在とパースを検査。--strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力を安全にスキップしてコンソール出力を継続。
  - utils/process_priority.py: Windows / POSIX の差分を吸収してカレントプロセスの優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。psutil の権限不足等は警告してスキップする堅牢設計。

- ポートフォリオ構築・ポジションサイジング
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順＋同点時は signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア正規化重みを提供。全スコアが 0 の場合は等金額へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター別の既存エクスポージャが閾値を超える場合、新規候補を排除するロジック（unknown セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 にフォールバック（警告ログ）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の割当方式に対応した発注株数計算。lot_size（単元）丸め、max_position_pct（銘柄上限）、max_utilization（利用限度）、aggregate cap によるスケールダウンを実装。スケールダウン時には残余キャッシュを fractional 残差順に配分するアルゴリズムを導入。

- 研究用ファクター計算
  - research/factor_research.py: DuckDB 接続を受け取ってモメンタム・ボラティリティ等のファクターを計算するための基盤を追加（prices_daily / raw_financials を参照）。（ファイル末尾に計算関数の実装が続く想定。）

- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（平均・最大・P95）を集計して PASS/FAIL 判定を出力。P95 計算、日付フィルタ、DB パス引数/環境変数対応を備える。

- パッケージメタ情報
  - __init__.py に __version__ = "0.1.0" を追加し、主要サブパッケージを __all__ で公開。

Changed
- （初回リリース）設計上の決定を明確化
  - run_monitoring は環境変数 KABUSYS_ENV にかかわらず監視用の本番 sqlite_path を使用する仕様を明示（コード内ドキュメント）。
  - run_execution は paper_trading の場合に paper_sqlite_path を利用して DB を本番と完全に分離する挙動を明示。

Fixed
- 設定読み込み／ログ周りの堅牢化
  - .env 読み込みでファイル読取失敗時に警告を出すようにし、プロセスを停止させない設計に改良（config._load_env_file）。
  - ログディレクトリ作成失敗時にファイルハンドラの作成をスキップし、コンソール出力のみで継続するフォールバックを実装（logging_setup.setup_logging）。
  - process_priority の設定で権限不足や未対応プラットフォーム時に例外で停止させずに警告でスキップするように改善。

Security
- 特記事項なし（本リリースでは環境変数の管理や秘密情報の取り扱いに関するドキュメント化・対話入力のマスクを実装）。

Notes / 既知の制約
- .env ファイルは生成時に平文で保存されます。Git 等にコミットしないよう .env 作成ガイドで注意喚起済み。
- position_sizing の価格フォールバック: price_map に欠損（0.0）があるとエクスポージャが過少見積りされる可能性があり、将来的に前日終値等のフォールバックを追加する予定（TODO コメントあり）。
- research/factor_research.py はファイル末尾で実装が続く想定のため、実際のファクター計算ロジックはコードベースの続きを参照してください。
- 起動スクリプトは外部コンポーネント（BrokerClient, ExecutionEngine, SystemMonitor 等）に依存します。これらの実装は別ファイルに分離されており、起動時に適切に配置されていることが前提です。

今後の予定
- ファクター計算の完全実装と単体テスト強化
- 単元株サイズ（lot_size）を銘柄別に扱う拡張
- .env シークレット管理（Vault 等）やより厳密な本番ガード（更なるチェック項目）の追加

--- 

注: この CHANGELOG は提供されたソースコードからの推測に基づいて作成しています。より詳細な変更履歴・コミット単位の差分は Git のコミットログを参照してください。