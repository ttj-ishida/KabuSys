CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-21
--------------------

Added
- 実行・監視用の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを実装。KABUSYS_ENV による paper_trading モードをサポートし、ペーパートレード時は専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と完全に分離する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定・環境変数管理機能を追加
  - config.py: .env の自動読み込み（プロジェクトルート検出）と環境変数取得用 Settings クラスを実装。多くの設定項目（J-Quants, kabuAPI, DB パス, ログ設定, 監視閾値 等）をプロパティとして提供。PAPER_FILL_MODE のバリデーション等を含む。
  - config_setup.py: .env を対話式に生成・更新するウィザードを実装。デフォルト値・選択肢・シークレット入力対応。保存前の確認プロンプトを提供。
  - validate_config.py: 起動前検証 CLI を実装。必須環境変数の確認、DB パスの親ディレクトリチェック、config/*.yaml の存在チェック（PyYAML がある場合はパース検証）などを行う。--strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築機能（純粋関数群）を追加
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコアソート・上位 N 選出。
    - calc_equal_weights: 等金額配分の重み算出。
    - calc_score_weights: スコア加重配分（スコア全て 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの集中リスク制限（既存保有を考慮して新規候補をフィルタ）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知のレジームは警告後フォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 重み・候補・現金等を元に銘柄ごとの発注株数を決定。risk_based/equal/score の配分方式をサポートし、単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）を考慮。

- 実行系コンポーネントの組立てと起動フロー
  - execution 起動時に BrokerClientFactory を通じてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで起動・監視する実行フローを実装。停止フラグ（data/stop_requested.flag）および PID ファイルの扱いに対応。

- 運用ユーティリティを追加
  - utils/logging_setup.py:
    - ルートロガー設定ユーティリティ。stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler を設定（ログディレクトリ作成失敗時はファイル出力をスキップし、コンソールのみで継続）。ログレベル・ログディレクトリの解決順を明示。
  - utils/process_priority.py:
    - クロスプラットフォームのプロセス優先度設定と CPU affinity 設定。Windows / POSIX の差分を吸収し、権限不足や未対応プラットフォームでは警告ログを出してスキップする。

- 監視・レポート関連
  - monitoring 側で使用する DB 初期化（init_monitoring_db）呼び出しを起動処理に統合。
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite から集計レポートを生成するスクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを計算し PASS/FAIL 判定を行う。日時フィルタ（--from/--to）と DB パス指定オプションを提供。

- research/factor_research.py（ファクター研究基盤）を追加
  - DuckDB 接続を受け取り、prices_daily / raw_financials を用いてモメンタム・バリュー・ボラティリティ・流動性等のファクターを計算する方針とユーティリティを実装（calc_momentum 等の実装開始を含む設計を反映）。

Changed
- パッケージ初期化
  - kabusys/__init__.py に __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開。

Fixed / Hardened
- .env 読み込みの堅牢化
  - .env パーサーで export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応。既存 OS 環境変数を保護するため protected オプションを導入し、ロード順（OS > .env.local > .env）を明確化。

- ロギングのフォールバック
  - ログディレクトリ作成やファイルハンドラ生成に失敗した際に、プロセスが致命的に止まらないよう StreamHandler のみで継続する設計に変更。

- プロセス優先度設定のフォールバック
  - OS による未対応や権限不足時に警告ログを出して安全にスキップするように変更。

Notes / Implementation details
- 環境変数関連のデフォルト
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_DIR: logs/（デフォルト、環境変数 LOG_DIR で変更可能）
  - MONITOR_POLL_INTERVAL: 60 秒（環境変数で上書き可、無効値はデフォルトへフォールバック）
- 停止フラグ / PID
  - 起動スクリプトは project/data/stop_requested.flag を監視し、検知時に安全終了する。Execution 用に data/execution.pid を使用。
- Paper Trading（KABUSYS_ENV=paper_trading）
  - mock ブローカーを用いたテスト実行が可能。ペーパートレード時のデータは paper_sqlite_path に記録され、本番の monitoring DB と分離される。

今後の予定（予定・提案）
- research/factor_research.py のファクター実装の完成とユニットテスト整備
- execution / monitoring 周りの統合テスト、以及び各種エラーケースの詳細ハンドリング強化
- 銘柄別の lot_size マスタ対応（position_sizing の拡張）
- config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py）との連携強化

署名
----
This project — KabuSys v0.1.0 (初回リリース)
