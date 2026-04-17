# CHANGELOG

すべての変更は Keep a Changelog に準拠して記載します。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

※ 以下は提示されたコードベースから推測して作成した初期リリースの変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

初回リリース — KabuSys 基本コンポーネントの実装。

### Added
- 基本構成とバージョン情報
  - パッケージバージョンを 0.1.0 として導入（src/kabusys/__init__.py）。

- 環境変数 / 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml、優先順位: OS環境 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env のパースに対応（export プレフィックス、クォート、エスケープ、インラインコメントの取り扱い）。
    - 必須設定取得ヘルパー _require()。
    - 各種設定プロパティ（J-Quants / kabu API、LINE、DBパス、監視閾値、環境判定など）。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）。

- 設定ウィザード CLI
  - 対話式 .env 生成/更新ツール（src/kabusys/config_setup.py）。
    - 入力プロンプト、既存値の再利用、保存確認。
    - .env の書式化出力（機密値はマスク表示の扱いをドキュメント化）。
    - デフォルト値と選択肢を提供。

- 設定検証 CLI
  - 起動前チェックツール（src/kabusys/validate_config.py）。
    - 必須/任意環境変数のチェック。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DUCKDB/SQLITE パスの親ディレクトリチェック。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 未設定、KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict モードで警告を失敗扱いにできる。

- 実行用スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境に応じて本番 DB または Paper Trading 専用 DB を使用（PAPER_TRADING_SQLITE_PATH / settings.is_paper）。
    - BrokerClientFactory を用いたブローカークライアント生成（paper_trading 時は MockBroker を利用する想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をデーモンスレッドで起動。
    - 停止フラグ（data/stop_requested.flag）検出で安全停止。
    - pid ファイル管理（data/execution.pid の使用）。

  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は環境に依らず本番 sqlite_path を使用して監視テーブルを初期化。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
    - 停止フラグ検出でループ終了。
    - エラー時はログ出力して次回ポーリングまで待機。

- データベース初期化ユーティリティ
  - 監視 DB 初期化呼び出し箇所を追加（init_monitoring_db の呼び出し：monitoring 側テーブルの冪等初期化）。

- ユーティリティ
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収する実装。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - psutil による実装。権限不足や未対応環境は警告してスキップ。

- ポートフォリオ構築ライブラリ
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: スコア降順ソート（同点は signal_rank によるタイブレーク）。
    - calc_equal_weights, calc_score_weights（スコアがすべて 0 の場合は等配分にフォールバックと警告）。

  - セクター制限・レジーム調整（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存保有に基づくセクター上限判定（max_sector_pct）、“unknown” セクターは制限対象外。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未定義はフォールバック 1.0）。

  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）。
    - calc_position_sizes: allocation_method("risk_based", "equal", "score") に対応。
    - リスクベースの株数計算、単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash によるスケールダウン）。
    - cost_buffer による保守的コスト見積り、残差処理で lot_size 単位の再配分を行う。

  - これらをパッケージ公開（src/kabusys/portfolio/__init__.py）。

- リサーチ / ファクター計算
  - DuckDB ベースのファクター計算モジュール（src/kabusys/research/factor_research.py）。
    - モメンタム（1M/3M/6M / MA200乖離）、ボラティリティ（ATR20、相対ATR）、流動性（20日売買代金）等の計算関数（DuckDB SQL を使用）。
    - target_date を指定して prices_daily テーブルを参照し結果を返す設計。

- ツール
  - Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）。
    - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）からデータを集計してレポートを出力。
    - 指標: 稼働率、注文成功率(Filled/Created)、送信率(Sent/Created)、リスク却下数、レイテンシ（avg/max/P95）。
    - デフォルトの合格基準を定義（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 レイテンシ <=200ms）。期間指定オプション (--from/--to) と DB 指定 (--db)。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （特記事項なし。ただし .env の取り扱いは .env を絶対に Git にコミットしない旨を config_setup のコメントで明示）

---

備考 / 動作に関する注意事項（コードからの推測）
- run_monitoring/run_execution は起動時にプロセス優先度を上げる設計だが、psutil の権限・OS 制約により実際にはスキップされうる（警告ログが出る）。
- .env 自動読み込みロジックはプロジェクトルートの検出に __file__ ベースの親探索を使うため、パッケージ配布後も CWD に依存せず動作する想定。ただしプロジェクトルートが見つからない場合は自動ロードをスキップする。
- Paper Trading と本番 DB は明確に分離される設計（paper_trading モード時は paper_sqlite_path を使用）。
- config/*.yaml の完全な検証は PyYAML に依存する。PyYAML がインストールされていない場合は YAML 内容検証はスキップして警告を出す。
- 一部コメント／TODO に将来の拡張（銘柄ごとの lot_size マスタ、価格フォールバック等）が残されている。

もし CHANGELOG に追記したい項目（例えば実際の変更日、リリースノートの翻訳方針、差分の強調箇所など）があれば教えてください。必要に応じて英語版やリリースノート用短い要約版も作成できます。