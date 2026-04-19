# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの現在の状態から推測して作成した変更履歴（主に初期リリース相当の機能追加）です。

全般的な注記
- この CHANGELOG は提供されたソースコードの内容（ファイル構成・実装内容）から推測して作成しています。実際のコミット単位の履歴ではありません。
- バージョン番号はパッケージの __version__ 値 (0.1.0) を基にしています。

## [0.1.0] - 初期リリース
公開日: 未指定

### Added
- 実行・監視用の起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine の起動エントリポイント。
    - KABUSYS_ENV に応じてペーパートレード用 DB（data/paper_trading.db）を使用する分離対応。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動・停止制御を実装。
    - 停止フラグ (data/stop_requested.flag) による安全停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor ポーリングループの起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境に関係なく本番の sqlite_path を使用する設計（explicit な挙動）。
    - 停止フラグ検知でループを終了し、例外発生時はログ出力して次のポーリングへ継続。

- 設定管理と自動読み込み機能を追加
  - config.py
    - .env 自動読み込み (プロジェクトルート判定: .git または pyproject.toml を基準)。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env のパースロジック（quoted / escaped / inline comment の扱い）を慎重に実装。
    - Settings クラスを追加し、J-Quants / kabu API / LINE / DB パス / 監視閾値 / システム設定等のプロパティ化された設定取得を提供。
    - paper_trading 用の PAPER_FILL_MODE 検証、paper_sqlite_path、pid / kill flag 等を提供。

- 設定関連の CLI を追加
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - デフォルト値・選択肢・シークレット入力対応・既存 .env の読み込みを実装。
    - .env 書き込みテンプレートを用意（注意喚起コメント含む）。
  - validate_config.py
    - 起動前に .env と config/*.yaml（可能なら PyYAML を使ってパース）を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、Live 環境向けの追加ガード等を実装。
    - --strict オプションで警告をエラー扱いにできる。

- ポートフォリオ構築関連の純粋関数群を追加（DB参照なし、メモリ計算のみ）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア順ソートと上位選定。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分、スコア合計が 0 の場合は等配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存ポジションを考慮して新規候補を除外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear のマップと未知レジームのフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定。
    - 単元株（lot_size）で丸め、ポジション上限 / aggregate cap / cost_buffer（手数料・スリッページ見積）を考慮したスケーリングロジックを実装。
    - 価格欠損時のスキップやログ出力など耐障害性を持たせている。

- ロギング・プロセスユーティリティを追加
  - utils/logging_setup.py
    - setup_logging 関数で全起動スクリプトで統一的なログ設定を提供。
    - StreamHandler を stdout に出力、TimedRotatingFileHandler で日次ローテーション（30 日保持）。
    - LOG_DIR / LOG_LEVEL の環境変数や引数での上書き対応。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX（Linux/Mac/FreeBSD）に対応した優先度設定。
    - set_cpu_affinity(cpu_count) で CPU affinity を最初の N コアに制限するユーティリティ。
    - 権限不足や未対応 OS の場合は警告ログを出す安全設計。

- analysis / レポート用ツールを追加
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート出力スクリプト。
    - system_status / trade_logs / risk_logs などのテーブルから稼働率、成立率、送信率、レイテンシ指標（平均・最大・P95）を集計。
    - 判定基準（閾値）を定義し、PASS/FAIL 判定を出力。
    - CLI オプションで期間（--from / --to）と DB path（--db）を指定可能。
    - P95 計算や日付フィルタの組み立て、欠損テーブルに対する例外ハンドリングを実装。

- 研究 / ファクター計算の基盤を追加
  - research/factor_research.py（実装の骨子）
    - DuckDB 接続を受けて定量ファクター（Momentum / Value / Volatility / Liquidity）を計算する設計。
    - calc_momentum の骨子（モメンタム指標、MA200 乖離など）を実装開始（営業日ウィンドウ、スキャン範囲の定義あり）。
    - DuckDB の prices_daily / raw_financials を用いた設計で、本番 API にはアクセスしない方針。

- パッケージ初期化
  - __init__.py にてバージョン __version__ = "0.1.0" を定義し、主要サブパッケージを __all__ に追加。

### Changed
- （初期リリース）プロジェクト全体の機能設計として、監視・実行・設定・ポートフォリオ構成・レポート・研究モジュールを分離し、CLI から利用できる形でまとめた。

### Fixed
- 各所で入力検証やフォールバックを実装
  - MONITOR_POLL_INTERVAL の不正値（0 や負数、非数）を検出して警告しデフォルトにフォールバック。
  - PAPER_FILL_MODE の無効値を検出して ValueError を送出。
  - ログディレクトリ作成失敗時の挙動（StreamHandler のみで継続）を明確化。
  - process_priority / cpu_affinity 設定時の権限不足や未実装 API に対するハンドリング（警告ログ）を追加。

### Security
- .env の自動生成テンプレートに「.env を Git にコミットしないこと」の注意喚起を追加。

---

今後の推奨事項（コードからの注記）
- portfolio.position_sizing の TODO にあるように、将来的には銘柄ごとの lot_size を導入すると精度が向上します。
- risk_adjustment.apply_sector_cap では price_map に欠損（0.0）があるとエクスポージャーが過小評価される可能性があるため、前日終値や取得原価によるフォールバックを検討してください。
- research/factor_research の calc_momentum はファイル末尾で途中（start_da で切れている）ため、実装の完了が必要です（提供コードの続きがある場合は反映推奨）。

もし、この CHANGLEOG をリポジトリの実際のコミット履歴に合わせて細かく分割・日付付与したい場合は、コミットログやリリース日を教えてください。それに合わせて改定して再出力します。