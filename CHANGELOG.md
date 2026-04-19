CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。  
すべての重要な変更点を日本語で記載しています。

フォーマット:
- すべてのリリースは日付付きで記載しています（YYYY-MM-DD）。
- セクションは Added / Changed / Fixed / Deprecated / Removed / Security を使用します。

Unreleased
----------

（現在のスナップショットに基づく未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------

初回公開リリース。以下はこのコードベースで提供される主要な機能と変更点の概要です。

Added
- 基本アプリケーション情報
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。

- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV が paper_trading の場合は専用の paper_trading SQLite DB（data/paper_trading.db）を使用し、MockBrokerClient を利用する設計。
    - ブローカー生成を BrokerClientFactory で抽象化。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の依存コンポーネントを組み立て、ExecutionEngine をデーモンスレッドで実行。停止フラグ（data/stop_requested.flag）検知による安全停止を実装。
    - PID ファイル（data/execution.pid）管理。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を参照（環境に依存しない監視 DB 利用）。
    - 停止フラグ検知でループ終了、KeyboardInterrupt によるグレースフルな終了処理を実装。

- 設定管理・検証・ウィザード
  - config.py: 環境変数ラッパー Settings を導入。.env の自動読み込み機能（.env, .env.local）と自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を実装。  
    - .env のパースはクォート・エスケープ・コメント処理に対応。
    - 各種設定プロパティ（DB パス、ログレベル、paper_trading 用設定、監視閾値など）を提供。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV 値検証、ログレベル検証、DB パスの親ディレクトリチェック、config/*.yaml の存在と YAML パース確認、live 環境に対する追加ガードなどを実装。--strict オプションで警告を失敗扱いにできる。
  - config_setup.py: .env を対話的に作成/更新するウィザードを追加。既存値の読み込み、シークレットマスク、保存確認などに対応。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をフォールバック。
    - ログレベルとログディレクトリの解決順を明記（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。  
    - Windows と POSIX の差分を吸収し、許可がない場合は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全て 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中抑制（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。未知レジーム・unknown セクター等のフォールバック挙動を定義。
  - portfolio/position_sizing.py: 株数算出ロジックを実装（risk_based / equal / score の allocation_method に対応）。単元株（lot_size）考慮、1銘柄上限、aggregate cap によるスケーリング、cost_buffer による保守的見積りなどを含む。
  - portfolio/__init__.py で上記関数をエクスポート。

- リサーチ・ファクター（骨組み）
  - research/factor_research.py: Momentum 等のファクター計算モジュールの骨組みを追加（DuckDB 接続を受ける設計）。モメンタム、MA200 乖離、ATR、出来高関連などの定数と関数設計が含まれる（calc_momentum 等、ファイル途中まで実装）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。  
    - 入力: PAPER_TRADING_SQLITE_PATH 環境変数または --db オプション、期間フィルタ --from/--to。
    - 指標: 稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ 等を算出・判定（PASS/FAIL）。デフォルト閾値を定義（稼働率 99% など）。
    - SQLite が未作成の場合やテーブル不備を考慮した例外ハンドリングを実装。

- DB / DuckDB 連携
  - duckdb と sqlite3 の接続を利用する設計（monitoring 用初期化関数 init_monitoring_db を利用してテーブルを冪等に保証）。

Changed
- 初回リリースにつき「Changed」相当の過去変更はありません（新規追加）。

Fixed
- ロバスト性の強化
  - run_monitoring のポーリングループで monitor.check_once() の例外を捕捉して例外発生時にもループ継続するようにし、ログに例外詳細を残す実装。
  - MONITOR_POLL_INTERVAL の不正値（非整数や 0 以下）を検出してデフォルト（60 秒）へフォールバックし、警告ログを出力する処理を追加。
  - logging_setup: ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続するフェールセーフを実装。
  - config._load_env_file: ファイル読み込み失敗時に警告（warnings.warn）を出す等、堅牢化。
  - run_execution: 停止フラグが既に立っている場合は起動をスキップして安全に終了するチェックを追加。

Deprecated
- なし

Removed
- なし

Security
- セキュリティに関する明示的修正はなし。ただしシークレット値（例: J-Quants トークン、kabu API パスワード）は config_setup の対話でマスク表示、Settings では必須チェックを行い、.env の扱いについて「Git にコミットしないこと」を README コメントで強調。

注記 / 既知の制限
- research/factor_research.py はファイル中盤で実装が途中（calc_momentum 関数の途中で終わっている）。完全なファクター計算の実装は今後の作業が必要。
- position_sizing の価格データ欠損時の挙動に TODO コメントあり（price が 0.0 の場合のフォールバックを検討する余地）。
- .env 自動ロードはプロジェクトルートの検出（.git または pyproject.toml）に依存する。配布パッケージ化後の挙動に注意が必要。
- process_priority / set_cpu_affinity は権限不足や非対応 OS でスキップされる設計（警告を出力）。

開発者向けヒント
- 設定検証: python -m kabusys.validate_config
- .env ウィザード: python -m kabusys.config_setup
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 実運用起動: python -m kabusys.run_execution / python -m kabusys.run_monitoring

ライセンスやその他メタ情報はリポジトリのトップレベルファイルを参照してください。