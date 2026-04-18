Changelog
=========

すべての変更は Keep a Changelog に準拠して記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。  

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------

Added
- 初期リリース。KabuSys のコア機能群を実装・提供。
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine の起動スクリプトを提供。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient 経由でペーパートレード動作を行う設計をサポート。
    - エンジンは別スレッドで実行し、data/stop_requested.flag による外部停止を監視。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
- 監視用エントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを提供。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値はデフォルトへフォールバックして警告を出力。
    - 監視用 DB は KABUSYS_ENV に依らず本番 sqlite_path を使用する動作を明示（安全運用上の意図に基づく設計）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 設定管理
  - config.py: 環境変数管理・読み込みを実装。
    - プロジェクトルート判定（.git または pyproject.toml を探索）に基づき .env/.env.local を自動読み込み（OS 環境変数は保護）。
    - .env のパースはシングル/ダブルクォート、エスケープ、インラインコメント処理、`export KEY=val` 形式に対応。
    - 多数の設定プロパティを提供（J-Quants トークン、kabu API、DB パス、ペーパートレード設定、監視閾値、環境種別など）。PAPER_FILL_MODE の検証も実装。
    - Settings クラスとグローバル settings インスタンスを提供。
- 設定関連 CLI
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援。
    - デフォルト値・選択肢・シークレット入力をサポート。保存前の確認プロンプト付き。
  - validate_config.py: 起動前チェックツールを実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および（PyYAML がインストールされている場合は）パース検証を行う。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング・プロセス設定ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定を提供。
    - STDOUT ストリームハンドラと日次ローテーションのファイルハンドラ（TimedRotatingFileHandler、30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル / ログディレクトリの解決ルールを明示。
  - utils/process_priority.py: プロセス優先度設定と CPU affinity 設定を提供。
    - Windows / POSIX の差異を吸収して set_process_priority(level: "high"/"normal"/"low") をサポート。
    - set_cpu_affinity(cpu_count) で最初の N コアに固定可能（権限不足等は警告でスキップ）。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順ソートとトップ N 選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化配分。スコア全てが 0 の場合は等配分へフォールバックして警告。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を抑えるフィルタ。既存保有のセクター別時価を計算して、閾値超過セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の割当方式をサポートして、単元株（lot_size）に丸めた発注株数を計算。aggregate cap（利用可能現金を超える場合のスケールダウン）と残差処理を実装。
    - cost_buffer（手数料・スリッページ見積）を考慮した保守的なコスト見積りを実装。
    - 単元株・上限チェック・既存ポジション差分計算を含む。
- 研究・因子計算（基盤）
  - research/factor_research.py: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクターを SQL + Python で計算する設計を開始（prices_daily, raw_financials テーブル参照）。モジュール設計・定数・calc_momentum の骨子を実装（calc_momentum は途中まで実装）。
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証用レポート生成スクリプトを追加。
    - system_status, trade_logs, risk_logs テーブルを解析して稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を計算し、PASS/FAIL 判定を出力する。
    - デフォルト DB は data/paper_trading.db。--db / PAPER_TRADING_SQLITE_PATH により変更可能。
    - P95 の独自計算や欠損データハンドリング、閾値定数を実装。
- パッケージ初期化
  - __init__.py でバージョン __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ にエクスポート。

Changed
- （初版のため該当なし）

Fixed
- 環境変数パースやポーリング間隔の不正値に対する堅牢性を強化（不正値は警告のうえデフォルトを使用）。

Removed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Security
- （初版のため該当なし）

Notes / Known limitations / TODO
- run_monitoring は設計上「監視は本番 sqlite_path を使用する」と明示的に実装されています。本番運用時に意図しない DB を参照しないよう注意してください。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合の挙動に注意。将来的には前日終値や取得原価などのフォールバックを検討する旨の TODO コメントあり。
  - lot_size を銘柄別に設定する拡張は未実装（TODO）。
- research/factor_research.calc_momentum はファイル末尾で途中実装の状態に見えるため、完全実装・テストが必要。
- 一部の機能は外部ライブラリ（psutil, duckdb, PyYAML 等）に依存。環境によっては依存パッケージのインストールが必要。
- .env 自動ロードはプロジェクトルートが検出できない場合スキップされる。テスト環境等で自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグを用意。

---

作成元: ソースコード解析に基づく初期リリース記述（自動生成）  
必要であれば、各ファイルの実装詳細や想定される運用手順を元に CHANGELOG の項目を追加・分割します。