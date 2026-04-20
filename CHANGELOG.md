# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リンクやチケット番号は存在しないため、コードベースから推測できる変更点をまとめています。

## [Unreleased]

## [0.1.0] - 2026-04-20
初回公開リリース（推測）。以下はこのリポジトリに含まれる主要機能・修正点の一覧です。

### Added
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。バックグラウンドスレッドでセッションを実行し、停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を扱う。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB を使用し、本番 DB と完全に分離する仕組みを導入（PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - BrokerClientFactory を通じてブローカークライアントを作成し、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てて実行。
    - RiskManager に対するデフォルト設定（最大ポジション比率、利用率、レートリミット、サーキットブレーカー、最大ドローダウン等）を組み込み、初期ポートフォリオ値を broker.get_available_cash() で取得して渡す。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に依存せず本番 sqlite_path を使用する（監視データは共通の監視 DB に集約）。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグによる安全終了・KeyboardInterrupt のハンドリング・DB 接続クローズを実装。

- 設定関連
  - config.py
    - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）を実装。優先順位: OS 環境変数 > .env.local > .env。
    - .env パーサーが export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - Settings クラスを導入し、環境変数の取得とバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を提供。各種パス（DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH 等）を Path 型で返すユーティリティを含む。

  - config_setup.py
    - 対話式の .env 作成/更新ウィザードを追加。既存 .env の読み込み再利用、シークレットのマスク表示、選択肢・デフォルト値の提示、最終確認後の .env 書き出しを実装。

  - validate_config.py
    - 起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および（PyYAML が利用可能なら）構文チェック、KABUSYS_ENV=live 時の追加ガード（LINE 通知や Kill Switch 関連）等を実装。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通セットアップを提供。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみにフォールバック。
    - ログレベル・ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - Windows と POSIX（Linux, macOS 等）を吸収するプロセス優先度設定機能を追加（high/normal/low）。対応不可や権限不足の場合は警告を出して安全にスキップする。
    - CPU affinity を最初の N コアに固定する機能を提供（設定が不要な場合は無効化）。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、同点タイブレーク）、等重み・スコア重みの算出を提供。スコアが全て 0 の場合は等重みへフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中上限の適用（既存保有のセクター別時価を計算し、上限超過セクターの新規候補を除外）と市場レジームに応じた投下資金乗数 calc_regime_multiplier を提供（"bull"/"neutral"/"bear" をマップ、未知のレジームはフォールバックして 1.0）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウンと残余配分）や cost_buffer による保守的コスト見積りをサポート。

- 解析・ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。P95 レイテンシ、稼働率、注文成功率、送信率、リスク却下数などを SQLite（PAPER_TRADING_SQLITE_PATH）から集計してレポート出力。閾値による PASS/FAIL 判定を実装。
  - research/factor_research.py（部分実装）
    - Momentum 等のファクター計算（DuckDB の prices_daily、raw_financials を参照）を意図したモジュールを追加（モジュール設計、定数、calc_momentum のシグネチャを含むが本文は途中）。

- パッケージメタデータ
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

### Changed
- （初回リリースにつき過去の変更履歴なし。実装上の設計上の工夫を以下に記載）
  - .env 読み込みの優先度を OS 環境変数を保護する形で設計（.env.local は上書き可だが OS 環境は保護）。
  - ロギングは stdout を主要なコンソールストリームとして使用（cron などで stdout/stderr を一本化する運用への配慮）。

### Fixed
- エラー耐性の強化
  - run_monitoring のポーリング内で monitor.check_once() が例外を投げてもループを継続するように例外ログと回復処理を追加。
  - DB ハンドラ生成やログディレクトリ作成で失敗した場合はファイル出力を無効化してプログラムを停止させないフォールバック処理を実装。
  - process_priority / set_cpu_affinity はアクセス許可や未対応環境で発生する例外を補足して警告ログのみ出すように変更。

### Security
- 機密情報取扱いの配慮
  - config_setup の対話でシークレット項目は出力時にマスク表示（****）。.env のテンプレート生成時に「.env を絶対に Git にコミットしないこと」を明示。

### Notes / その他
- 構成ファイル（config/*.yaml）はデフォルトで存在しない可能性を想定し、validate_config は PyYAML 未インストール時にパース検証をスキップして警告を出す実装になっています。
- run_monitoring は Monitoring 用テーブルを保証するため init_monitoring_db を呼ぶ等、監視インフラの初期化を行います。
- 一部のモジュール（research/factor_research.py など）は未完の実装が含まれているため、将来的な拡張・完成が予定されます。

（本 CHANGELOG は与えられたソースコードから推測して作成しています。実際のリリースノート作成時はコミット履歴・チケットを参照して必要に応じて修正してください。）