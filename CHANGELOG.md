# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-17

初回リリース — KabuSys の基本機能を実装しました。主な追加・仕様は以下の通りです。

### Added
- 起動用スクリプト／デーモン
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 実行中は data/stop_requested.flag により優雅に停止できる仕組みを実装。
    - 監視 DB は設定に関わらず本番 sqlite_path を使用する仕様。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用 DB（data/paper_trading.db または環境変数で指定）に完全に分離して記録。
    - 実行時の停止フラグ検知 (data/stop_requested.flag) と PID ファイル操作をサポート。
- 設定管理
  - config.py
    - Settings クラスを提供し、環境変数からアプリ設定を取得。
    - 自動 .env ロード機能（.env/.env.local）を実装（プロジェクトルートは .git または pyproject.toml から探索）。
    - .env パースは export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープシーケンスに対応。
    - 各種設定プロパティ（DB パス、PID ファイル、監視閾値、PAPER_FILL_MODE の妥当性チェック等）を実装。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。
    - シークレット項目はマスク表示して入力を促す。保存時は生成済みのテンプレート形式で書き出す。
  - validate_config.py
    - 起動前検証用 CLI。必須環境変数、KABUSYS_ENV、DB パス、config/*.yaml の存在・パースなどをチェック。
    - --strict オプションで警告も FAIL 扱いにできる。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出す。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額重み（calc_equal_weights）、スコア加重（calc_score_weights）。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）。
    - 市場レジームに基づく投下資金乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py
    - 株数算出ロジック（risk_based / equal / score）、単元丸め、aggregate cap によるスケールダウンロジックを実装。
    - コストバッファ（スリッページ/手数料想定）対応や、残差処理による lot 単位での追加配分実装。
  - portfolio/__init__.py
    - 上記関数をエクスポートするパッケージエントリを追加。
- ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。
    - CPU affinity を設定する set_cpu_affinity() を追加。
    - 権限不足や未対応プラットフォーム時は警告ログを出して安全にフォールバック。
- 分析／レポート
  - tools/paper_verification_report.py
    - ペーパートレード DB を解析して検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、レイテンシ（平均／最大／P95）などを算出し、閾値（稼働率 99%、成功率 90% など）に基づく PASS/FAIL 判定を出力。
    - 日付フィルタ、DB パス指定 (--db) に対応。
- リサーチ
  - research/factor_research.py
    - DuckDB 接続を受け取りファクター（モメンタム、ATR ベースのボラティリティ、流動性指標等）を計算する関数を実装。
    - momentum（1M/3M/6M リターン、MA200 乖離）と volatility（ATR20、相対 ATR、20日平均売買代金、出来高比率）を提供。
- モニタリング関連
  - monitoring.monitoring_db.init_monitoring_db の利用を各起動スクリプトで呼び出し、監視用テーブルの冪等初期化を保証。
  - stop/kill フラグのパス設定を Settings やスクリプト側で一貫して扱う実装。
- パッケージメタ
  - __init__.py にて __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed / Robustness
- .env 自動読み込み時に OS 環境変数を上書きしないよう保護（protected set を導入）。
- .env パーサは不正な行を無視し、引用符ありの値のエスケープ処理やインラインコメントの扱いを改善。
- MONITOR_POLL_INTERVAL の不正値（整数化失敗、0 や負値）に対して警告を出しデフォルトへフォールバックする挙動を run_monitoring に実装。
- process_priority や CPU affinity の設定失敗時に例外を投げず警告ログを出すようにし、実行継続可能とした。
- position_sizing のスケールダウン・端数処理で単元（lot）に従った安定した割当てを実装（再現性を考慮したソート順を採用）。
- paper_verification_report における P95 計算、欠損データ時の N/A 表示や SQL 実行失敗時のフォールバックを実装。

### Security
- config_setup の項目確認表示でシークレット値をマスク（"****"）表示するようにした（.env を画面に表示する際の配慮）。

### Notes / Operational
- run_execution は paper_trading モード時に paper_sqlite_path を用いて本番データと完全に分離する仕様のため、ローカルでの検証時は環境変数の設定ミスに注意してください。
- validate_config の live 環境チェックは、本番リスク（LINE 未設定、KILL_FLAG_CLEAR_ON_START の誤設定等）に関する注意を出すようになっています。
- DuckDB を用いるリサーチ処理は prices_daily / raw_financials テーブルを前提としており、外部 API への接続は行いません。

---

今後の予定（例）
- 監視アラートの LINE 通知実装（設定が整い次第）
- 銘柄別 lot_size 管理の追加（stocks マスタ参照）
- factor_research の追加ファクター実装およびパフォーマンス最適化

もし特に強調して記載したい変更点や、リリースノートに含めるべき追加情報（署名、ビルド手順、既知の制限など）があれば教えてください。