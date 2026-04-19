CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- 今後の変更をここに記載します。

[0.1.0] - 2026-04-19
--------------------

初回リリース。コードベースから推測される主な機能・改善・動作仕様をまとめています。

Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
- 設定・環境変数関連
  - Settings クラス（src/kabusys/config.py）を追加。環境変数経由で各種設定（J-Quants / kabuステーション / DB パス /監視閾値 /環境種別 等）を安全に取得・検証。
  - .env 自動ロード機能を実装（プロジェクトルートの判定ロジックを含む）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 解析の強化:
    - export KEY=val 形式の対応
    - シングル/ダブルクォート、バックスラッシュエスケープ対応
    - インラインコメント判定ロジック（クォート無・スペース直前の # をコメントとして扱う等）
  - config_setup（src/kabusys/config_setup.py）: 対話式ウィザードで .env を初期作成／更新する CLI を追加。シークレットはマスク表示、既存値の再利用、保存前の確認プロンプトを実装。
  - validate_config（src/kabusys/validate_config.py）: .env や config/*.yaml の起動前検証ツールを追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスや YAML パース確認、本番環境向けの追加ガード（LINE 通知・Kill Switch 設定の注意）を実装。--strict フラグで警告を FAIL 扱いにできる。
- 実行系・監視系の起動スクリプト
  - run_execution（src/kabusys/run_execution.py）:
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度の設定、SQLite/DuckDB 接続、BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のデーモン起動および停止フラグによる制御を実装。
    - Paper Trading モードでは settings.is_paper に応じて専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB から完全分離する仕様を採用。
  - run_monitoring（src/kabusys/run_monitoring.py）:
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。監視 DB は環境にかかわらず本番 sqlite_path を使用する旨を明示。
    - 停止フラグファイルによる安全なシャットダウン、check_once() での例外をログ出力してループ継続する耐障害性を実装。
- モニタリング DB 初期化
  - init_monitoring_db（monitoring パッケージ内）を用いて監視テーブルの存在を保証（冪等処理）。
- ログ機能
  - setup_logging（src/kabusys/utils/logging_setup.py）:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを追加。
    - ログディレクトリ作成の失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバック実装。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を定義。
- プロセス制御ユーティリティ
  - process_priority（src/kabusys/utils/process_priority.py）:
    - Windows / POSIX の差を吸収してプロセス優先度を設定する関数を追加（high / normal / low）。
    - CPU affinity を最初の N コアに固定するヘルパー（set_cpu_affinity）を追加。権限不足時は警告を出してスキップ。
- ポートフォリオ構築ロジック
  - portfolio モジュール（src/kabusys/portfolio/）:
    - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等金額にフォールバックして警告を出す。
    - risk_adjustment: セクター集中制限 apply_sector_cap（既存保有のセクター比率が閾値を越える場合に当該セクター新規候補を除外）、市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知のレジームは警告の上でフォールバック）を実装。
    - position_sizing: 各銘柄の発注株数決定ロジックを実装（risk_based / equal / score）。単元株（lot_size）で丸め、1銘柄上限・aggregate cap（利用可能現金）超過時のスケーリングと端数配分ロジックを備える。手数料/スリッページ見積り用の cost_buffer 対応あり。
- 研究用ファクター計算
  - research/factor_research.py（部分実装）: Momentum/Value/Volatility/Liquidity などのファクター計算を想定した設計を追加（DuckDB を用いた prices_daily/raw_financials の参照を前提）。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成ツールを追加。システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを算出し、閾値（稼働率 99%、成功率 90%、送信率 95%、P95 200ms）に基づいて PASS/FAIL 判定を行う。日付フィルタ、DB パスのオーバーライド (--db / 環境変数) に対応。
- DB 統合
  - DuckDB（分析用）および SQLite（監視／ペーパートレード用）を利用。各起動スクリプトでの接続とクローズ処理を実装。

Changed
- ロギング出力先の仕様を統一（stdout を標準出力に用いることで外部ジョブスケジューラとのリダイレクト互換性を配慮）。
- .env 読み込みの保護（OS 環境変数は保護キーとして扱い .env.local の強制上書きを制御）。

Fixed
- 環境変数の不正値に対する堅牢性向上:
  - MONITOR_POLL_INTERVAL のパース時に不正値（非数・0 以下）で警告を出してデフォルトにフォールバック。
  - PAPER_FILL_MODE の検証（有効値以外は ValueError を送出）。
  - LOG_LEVEL / KABUSYS_ENV の不正値検出と説明的なエラー/警告メッセージ。
- プロセス優先度や CPU affinity の設定は権限不足や非対応 OS を graceful に扱うように修正（エラーで落ちないよう警告に留める）。

Security
- .env の取り扱いに関する注意が README 相当の出力に含まれる（config_setup の .env ヘッダに「絶対に Git にコミットしないこと」を明示）。

Notes / Implementation details（コードから推測）
- Paper Trading は本番 DB と完全分離される設計（settings.is_paper により paper_sqlite_path を使用）。
- 監視（monitoring）は本番 sqlite_path を使用する方針（KABUSYS_ENV にかかわらず本番の監視対象とする意図）。
- 多くのコンポーネントは外部依存（kabu API / J-Quants / ブローカークライアント等）を抽象化しており、MockBrokerClient 等でローカル検証が可能な設計。
- DuckDB を分析用に常設し、research や ExecutionEngine の分析処理で利用する想定。
- ログ周り・ディレクトリ作成等は起動環境（権限・ファイルシステム）に頑健になるよう安全弁が入っている。

Acknowledgments
- この CHANGELOG は提供されたコードベースの内容に基づき推測した変更履歴です。実際のコミット履歴や差分とは異なる場合があります。必要であれば、Git の履歴やリリースノート用の追加情報を提供してください。