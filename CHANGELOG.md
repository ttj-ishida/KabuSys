CHANGELOG
=========

このプロジェクトは Keep a Changelog の形式に従って変更履歴を管理しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（なし）

[0.1.0] - 2026-04-18
-------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基礎機能を実装。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を使い MockBrokerClient を利用することで本番 DB と分離。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルによる安全停止に対応。
- 設定管理
  - config.py: .env 自動読み込み機能（.env → .env.local の優先順位）、.env 行の詳細なパース（export 付き行、引用符とエスケープ、インラインコメント判定）を実装。Settings クラスで環境変数をラップし、各種プロパティ（パス、閾値、env 判定、PAPER_FILL_MODE の検証など）を提供。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。既存値の読み取り・マスク表示、確認プロンプト、.env 書き出しロジックを実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検査、live 環境向けガードチェック、--strict モードをサポート。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。コンソール(stdout) と 日次ローテーションファイル（TimedRotatingFileHandler）をセットアップ。LOG_DIR/LOG_LEVEL の考慮、既存ハンドラのリセット、ファイルハンドラ失敗時のフォールバックを含む。
  - utils/process_priority.py: psutil を使ったプロセス優先度設定および CPU affinity セット機能を追加。Windows/Linux/macOS を吸収する実装で、権限不足などの失敗は警告でフォールバック。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア・ランクに基づく）と重み計算（等配分・スコア加重）を実装。スコアが全て 0 の場合のフォールバック動作を含む。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（既存ポジションのセクターエクスポージャ計算と候補フィルタリング）と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。未知のレジームや "unknown" セクターの扱いについての挙動を明記。
  - portfolio/position_sizing.py: 株数決定ロジックを実装（risk_based / equal / score）。単元株（lot_size）丸め、1銘柄上限・aggregate 上限の考慮、コストバッファ反映、利用可能現金に基づくスケーリングと小数端数の再配分ロジックを含む。
- 解析 / ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95 を含む）を算出し、閾値に基づく PASS/FAIL 判定を出力。--from/--to/--db オプション対応。
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB を用いて prices_daily / raw_financials を参照する設計（ファイル内に計算境界や定数を定義）。
- DB/分析統合
  - 各スクリプトで DuckDB 接続を受け取る設計を採用（duckdb_path を Settings 経由で設定）。monitoring 用 SQLite（monitoring.db）と分析用 DuckDB（kabusys.duckdb）を使い分ける方針。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Notes / Implementation details
- run_monitoring は KABUSYS_ENV にかかわらず監視用の production sqlite_path（Settings.sqlite_path）を使用する設計。
- run_execution は paper_trading 環境であれば専用の paper_sqlite_path を使い DB を分離。ExecutionEngine 起動時に既に停止フラグが立っている場合は起動をスキップする安全策を実装。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行う。プロジェクトルートが特定できない場合は自動ロードをスキップする。
- .env 読み込みは既存の OS 環境変数を保護するため保護セット（protected）を用いて上書き制御を行う。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
- position_sizing のスケーリング処理は lot_size（単元）単位での丸めと、端数を残余キャッシュで再配分するアルゴリズムを採用し再現性を考慮（同一端数時は code を二次キーにして安定ソート）。
- ロギングは標準出力に出すため StreamHandler を stdout に固定。ファイル出力に失敗した場合はコンソールのみで継続するフォールバック有り。
- process_priority / set_cpu_affinity は権限不足や未サポート環境で失敗しても動作を継続する（警告ログを出力）。

Known issues / TODO
- research/factor_research.py 内の一部関数が実装途中（ファイル末尾が切れている様子）。完全なファクター計算ロジックの追加・テストが必要。
- position_sizing の price 欠損（0.0）の場合にエクスポージャが過少評価される旨の TODO コメントあり。フォールバック価格（前日終値や取得原価）導入を検討。
- 将来的な拡張案として銘柄ごとの単元情報を持つ設計（lot_map）への対応が示唆されている。

開発者向けメモ
- バージョンはパッケージ __version__= "0.1.0" に設定済み。必要に応じて次バージョンでは Unreleased セクションに変更点を追記してください。