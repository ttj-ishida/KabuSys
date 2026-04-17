# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。KabuSys の基本的なランタイム・設定・ポートフォリオ構築・モニタリング・検証ツール群を追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。

- 環境変数／設定管理
  - src/kabusys/config.py
    - .env 自動読み込み機能（プロジェクトルート検出：.git または pyproject.toml）。
    - .env および .env.local の読み込み順序（OS 環境変数を保護）。
    - 複雑な .env パース機能（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い）。
    - 各種設定プロパティ（J-Quants / kabuステーション / LINE / DuckDB / SQLite / Paper Trading 関連パス、監視閾値、KABUSYS_ENV の検証等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。

  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI。
    - デフォルト値と説明付きプロンプト、シークレット入力の扱い、保存キャンセル/確認フローを実装。

  - src/kabusys/validate_config.py
    - 起動前検証 CLI。必須環境変数、KABUSYS_ENV、DB パス、config/*.yaml の存在・パース確認、ライブ環境時のガードチェック等。
    - --strict オプションで警告を失敗扱いにできる。

- 実行・監視エントリポイント
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト（プロセス優先度設定、DB 接続、依存コンポーネント組立、スレッド実行、停止フラグ監視）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB から分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository、OrderManager、RiskManager（デフォルト設定）、Reconciler、ExecutionEngine の組立と実行制御。
    - data/execution.pid に PID を書く想定、stop_requested.flag による停止制御。

  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず監視用（本番） sqlite_path を使用する旨の挙動。
    - stop_requested.flag によるループ終了、check_once() の例外ハンドリング、起動時にプロセス優先度を上げる処理を実装。

- モニタリング DB 初期化
  - run_execution/run_monitoring から monitoring DB 初期化（init_monitoring_db）呼び出しを行い、監視テーブルの存在を保証（冪等）。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定ユーティリティ（high/normal/low）。
    - CPU affinity 固定関数（最初の N コアにピン留め）。
    - psutil を使い、権限不足や未サポート環境では警告を出してスキップする堅牢化。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナルの候補選定 (select_candidates)、等重み付け (calc_equal_weights)、スコア加重 (calc_score_weights)。
    - スコア全てが 0 の場合は等重みへフォールバックと警告。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限の適用 (apply_sector_cap): 現有ポジションを参照してセクター上限を超える候補を除外。
    - マーケットレジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマップ、未知レジームは警告とフォールバック）。

  - src/kabusys/portfolio/position_sizing.py
    - 各銘柄の発注株数計算 calc_position_sizes（risk_based / equal / score の allocation_method をサポート）。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap によるスケールダウンと端数配分ロジック、コストバッファ対応。
    - 価格欠損時のスキップやデバッグログを備える。

  - src/kabusys/portfolio/__init__.py
    - 上記関数群をまとめてエクスポート。

- リサーチ（ファクター計算）
  - src/kabusys/research/factor_research.py
    - DuckDB を用いたファクター計算モジュール（momentum / volatility 等）。
    - momentum: 1M/3M/6M リターン、MA200 乖離の計算（ウィンドウサイズと不十分データの取扱いを明記）。
    - volatility: ATR、平均売買代金、出来高比率等を計算（SQL ベースの窓関数利用、NULL 伝播を考慮）。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード DB を解析して検証レポートを出力する CLI。
    - 可用性（稼働率）、注文成功率（fill_rate）、送信率、リスク却下数、レイテンシ（avg/max/P95）を算出し PASS/FAIL を判定する閾値を定義（稼働率 99%、fill 90% 等）。
    - --from / --to / --db オプションで期間や DB パスを指定可能。PAPER_TRADING_SQLITE_PATH 環境変数にも対応。
    - P95 計算関数を実装し、データ不足や sqlite の OperationalError を冗長に扱う。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env ファイルには秘密情報（API トークン等）が含まれるため、config_setup で生成した .env は絶対に Git にコミットしない旨を明記。

### Notes / ユーザー向け重要事項
- DB 分離
  - run_execution は paper_trading 環境では paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番監視 DB と記録を完全に分離します。
  - run_monitoring は「監視 DB（sqlite_path）」を環境に依らず使用する旨の実装上の挙動に注意してください（監視は常に本番用監視 DB を指す設計）。

- 停止制御
  - data/stop_requested.flag（プロジェクトルート直下 data ディレクトリ）により、起動中のエンジンや監視ループをグレースフルに停止できます。
  - 起動時に KILL_FLAG_CLEAR_ON_START を 1 にしていると自動クリアの挙動に関する警告を出す箇所があります（本番では 0 を推奨）。

- 環境変数読み込み順序
  - OS 環境変数 > .env.local > .env の優先順位で読み込まれます。OS 環境変数は保護され、.env.local でも上書き可、.env は未設定キーのみ設定されます。
  - 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

- 外部依存
  - psutil（プロセス優先度・CPU affinity）、duckdb、sqlite3、PyYAML（validate_config の追加検証で必要）などがランタイムで使用されます。validate_config は PyYAML 未導入時に YAML 検証をスキップして警告を出します。

---

今後のリリース案（例）
- モジュールごとのユニットテスト追加
- stocks マスタによる銘柄別 lot_size 対応
- position_sizing の価格フォールバック改善（前日終値や取得原価の使用）
- 更なるモニタリングメトリクス拡充（ディスク/メモリしきい値アラート等）

（必要であれば、各ファイルの差分ベースでより細かい変更ログを生成します。）