Keep a Changelog に準拠した CHANGELOG.md（日本語）
すべての重要な変更をこのファイルに記録します。  
この変更履歴は提示されたコードベースから機能・修正点を推測して作成しています。

フォーマット:
- 各バージョンごとに分類（Added / Changed / Fixed / Deprecated / Removed / Security）
- 日付はこの生成日時（2026-04-21）を初回公開日として記載しています

Unreleased
---------
（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-21
-------------------
Added
- 基本パッケージ初期実装を追加
  - パッケージメタ情報: kabusys.__version__ = 0.1.0
- 実行系・監視系起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動用。KABUSYS_ENV=paper_trading 時の専用 DB 分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）と MockBrokerClient の切替をサポート。実行中停止フラグ（data/stop_requested.flag）と PID ファイル管理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループを実行。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。監視 DB は実行環境に関わらず本番 sqlite_path を使用する挙動を実装。
- 環境設定周りのユーティリティを追加
  - config.py: .env 自動読み込み（プロジェクトルート検出ロジック）、.env/.env.local の読み込み順序、環境変数の取得ラッパー（Settings クラス）を提供。種々の設定プロパティ（DB パス、ログレベル、しきい値、paper_trading の挙動など）を定義。PAPER_FILL_MODE の検証ロジックを追加。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを実装。複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス等）を対話的に生成・保存可能。
  - validate_config.py: 起動前チェック CLI。必須環境変数の有無、KABUSYS_ENV/LOG_LEVEL 等の妥当性、DB パス親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML がある場合）パース検証、本番時のガードチェック（LINE 設定、KILL_FLAG_CLEAR_ON_START）を実装。--strict フラグで警告も失敗扱いにできる。
- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py: stdout ストリームハンドラと日次ローテート（TimedRotatingFileHandler、30 日保持）のファイルハンドラをルートロガーにセットする共通セットアップ。LOG_DIR 作成失敗時のフォールバック（コンソールのみ）に対応。
  - utils/process_priority.py: psutil を使ったプロセス優先度（high/normal/low）設定と CPU affinity 固定機能を実装。Windows/Linux/その他 POSIX の差分を吸収し、許可されない環境では警告を出してスキップする。
- ポートフォリオ構築関連モジュールを追加（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（スコア順で上位 N）と重み計算（等分配・スコア加重。全スコア 0 の場合はフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（既存保有のセクター別曝露を算出して候補除外）、市場レジームに基づく投下資金乗数の計算（bull/neutral/bear）を実装。未知レジームはフォールバックして 1.0 を返す。
  - portfolio/position_sizing.py: 株数決定ロジックを実装（risk_based / equal / score の allocation_method をサポート）。単元株（lot_size）で丸め、per-stock 上限・aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残差配分アルゴリズムを実装。将来的な拡張（銘柄別 lot_size）に関する TODO コメントあり。
  - portfolio/__init__.py: 主要関数をエクスポート。
- リサーチ / ファクター計算（初期実装）
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity 系ファクター設計を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。モメンタム計算関数 calc_momentum の骨格と定数、計算方針を導入（ファイル末尾で実装が途中で切れている）。
- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py: ペーパートレードの SQLite (PAPER_TRADING_SQLITE_PATH) を参照して稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計し、PASS/FAIL レポートを標準出力へ出力する CLI を実装。既定の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく判定ロジックを実装。
- 監視 DB 初期化ユーティリティ（init_monitoring_db）や SystemMonitor / ExecutionEngine 等を呼び出す箇所を組み込むことで、監視テーブル存在の保障や DuckDB 接続の統一を実現。

Changed
- （初回リリースのため該当なし）

Fixed
- 環境変数読み込みの堅牢化
  - .env の各行パースでシングル/ダブルクォート内のエスケープ、コメント扱いのルールを実装し、export PREFIX=val 形式にも対応。
  - .env 自動ロード時に OS 環境変数を保護（protected set）して不意の上書きを回避。
- ロギング周り
  - ログディレクトリ作成に失敗した際はファイルハンドラを省略してコンソールログのみで継続する挙動を追加（起動の失敗を防止）。
- run_monitoring/run_execution の安全起動
  - 起動直後にプロセス優先度を設定する位置に変更（最初に実行）し、監視/実行の安定性を向上。
  - 停止フラグ（data/stop_requested.flag）検知により安全にループ/セッションを終了可能。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 秘匿情報は .env に格納する設計を推奨。config_setup の生成テンプレートに「.env を絶対に Git にコミットしないこと」を明記。

Notes / Known issues / TODO
- research/factor_research.calc_momentum の実装が途中で切れている（ファイル末尾にて実装継続が必要）。
- position_sizing.calc_position_sizes 内の価格欠損（price が 0.0）の場合にエクスポージャーが過少見積りされる問題がコメントとして残っており、将来的に前日終値や取得原価によるフォールバック実装が推奨されている。
- PAPER_FILL_MODE の不正値は ValueError を送出する（実行時にクラッシュを招く可能性あり）。デプロイ前に .env の検証を行うこと（validate_config を推奨）。
- run_monitoring のポーリング間隔 MONITOR_POLL_INTERVAL に 0 以下や非整数を与えると警告してデフォルトにフォールバックするが、大きすぎる値や極端な単位誤りは検出しない。
- DuckDB / SQLite の schema 変更や未作成テーブルに対するクエリ時に OperationalError をハンドリングする箇所があるが、完全な回復処理は実装されていないため初回起動時は init_monitoring_db 等でテーブル作成を確実に行う必要がある。
- run_execution/run_monitoring の停止フラグや PID 管理はファイルベースで実装されているため、複数インスタンスやコンテナ環境での運用時に運用ルールが必要。

参考
- 自動検証・設定作成: python -m kabusys.validate_config, python -m kabusys.config_setup
- 実行スクリプト: python -m kabusys.run_execution, python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---
この CHANGELOG はコードの中に含まれる機能記述・コメントを基に推測して作成しています。実際のリリースノートとして使用する場合は、実装担当者による確認・補正をお願いします。