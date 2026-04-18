# Changelog

すべての重要な変更は Keep a Changelog に従って記載します。  
フォーマット: https://keepachangelog.com/ja/

注意: 以下の履歴は提示されたソースコードから推測して作成したものであり、実際のコミット履歴と完全に一致するとは限りません。

## [Unreleased]

- ドキュメントや小さな実装調整などリリース前の未反映項目をここに掲載します。

---

## [0.1.0] - 2026-04-18

Added
- 初期リリース: KabuSys のコア機能を実装。
- 実行・監視プロセス起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプトを提供。スレッドで engine.run_session を実行し、data/execution.pid を使用してプロセス管理。
    - 停止フラグ (data/stop_requested.flag) を監視し、検知時にエンジンを安全に停止。
    - KABUSYS_ENV=paper_trading の場合、本番 DB と分離して paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用する想定（Broker のファクトリで MockBrokerClient を切替）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。DuckDB と SQLite を使用して監視データを記録。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）はデフォルトにフォールバックして警告を出力。
    - 監視プロセスは停止フラグファイルの存在を確認して終了する。
    - 監視は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用する設計（監視データは本番 DB に記録）。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env のパースを強化。export プレフィックス対応、引用符内でのバックスラッシュエスケープ処理、インラインコメントの扱いに対応。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、主要環境変数（J-Quants、kabuAPI、DB パス、Paper Trading 関連設定、監視閾値など）をプロパティで安全に取得。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH など paper_trading 用設定を追加。
    - PID / kill flag 関連のパス設定と監視閾値（CPU/MEM/DISK）をプロパティで提供。

- CLI ユーティリティ
  - config_setup.py
    - 対話式ウィザードで .env を初期生成・更新するツールを追加。
    - 秘匿入力のマスク表示、選択肢サポート、既存 .env の読み込み・再利用をサポート。
    - .env の書式テンプレートを出力し、Git にコミットしないよう注意書きを含む。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数の存在チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードなどを行う。
    - --strict オプションで警告も失敗扱いにできる。
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。SQLite（デフォルト: data/paper_trading.db）から期間フィルタでデータを集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を行う。
    - P95 算出、日付フィルタ、SQL の耐障害性（テーブル欠如時のフォールバック）を実装。
    - レポート内の閾値（稼働率、成功率、送信率、P95）を定義済み定数で管理。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（score 降順、タイブレークルール）と重み計算（等金額 / スコア加重）を追加。スコアが全て 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有額からセクター比率を算出し、上限超過セクターの新規候補を除外。unknown セクターは制限対象外。
    - レジーム乗数 calc_regime_multiplier を実装（bull/neutral/bear に対する乗数、未知レジームは 1.0 へフォールバック）。
  - portfolio/position_sizing.py
    - position size 計算（risk_based / equal / score）を実装。損切り率・許容リスク率に基づく risk-based、lot 単位丸め、per-position 上限・aggregate cap（利用可能現金でスケールダウン）、cost_buffer（手数料・スリッページの保守的見積り）を考慮した配分ロジックを実装。
    - スケーリング時の残差処理（lot_size 単位で再配分するアルゴリズム）を実装。

- 研究系 / ファクター計算
  - research/factor_research.py
    - DuckDB を用いたモメンタム・ボラティリティ等のファクター計算関数を追加（calc_momentum / calc_volatility）。
    - 200 日移動平均、1m/3m/6m リターン、ATR、出来高指標などを SQL ウィンドウ関数で計算。データ不足時は None を返す設計。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度を設定するユーティリティを追加。Windows（psutil の priority constants）と POSIX（nice 値）を吸収し、対応外 OS はスキップして警告を出す。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。権限不足や未実装 API は警告してスキップ。

Changed
- パッケージ情報
  - __init__.py にて初期バージョンを 0.1.0 として定義。

Fixed
- 環境変数 / .env 関連の堅牢性向上
  - .env パーサで引用符・エスケープ・インラインコメント処理の不整合を改善し、実運用での .env 読み込みに強くした。
- run_monitoring/run_execution の例外・終了処理を強化
  - monitor.check_once() の例外を捕捉してループを継続するようにし、DB コネクションは finally ブロックで確実にクローズするようにした。
  - ExecutionEngine スレッド停止時の join/stop シーケンスを整備。

Security
- 秘密情報の扱いに関する注意
  - config_setup.py で生成される .env に対して「絶対に Git にコミットしないこと」を明示。

Migration notes / 運用メモ
- .env 関連
  - 自動ロードが有効（デフォルト）でプロジェクトルート (.git または pyproject.toml) を探索して .env/.env.local を読み込みます。自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください。
  - .env.local は .env を上書きする（既存 OS 環境変数は保護される）。
- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、Execution は paper_sqlite_path を使用して本番 DB と分離します。デフォルトパスは data/paper_trading.db。
  - PAPER_FILL_MODE に不正な値を設定すると Settings が例外を投げます。有効値は instant / partial / never / reject。
- 監視・停止
  - 両スクリプトはプロジェクト内 data ディレクトリに stop_requested.flag を置くことで安全に終了できます。実行中の PID 管理や kill flag の運用ルールに注意してください。
- 依存
  - 一部機能（config YAML の検証）では PyYAML の存在を検査します。インストールされていない場合は該当検証をスキップして警告を出力します。
  - process_priority, CPU affinity は psutil に依存。権限がない環境では警告を出力して処理をスキップします。

クレジット
- 実装は提示されたソースコードに基づく推測によるものです。細かな実装差分・バグ修正は実際のコミットログを参照してください。