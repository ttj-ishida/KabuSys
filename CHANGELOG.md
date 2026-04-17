# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記録しています。  
カテゴリ: Added, Changed, Fixed, Deprecated, Removed, Security。

## [0.1.0] - 2026-04-17
初回リリース。

### Added
- 基本アプリケーションパッケージを追加。
  - kabusys パッケージのバージョンを 0.1.0 として定義。
- 設定読み込み・管理
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装（OS 環境変数優先）。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - プロジェクトルート検出機能を追加（.git または pyproject.toml を探索）。
  - .env パーサ実装:
    - export プレフィックス対応。
    - シングル/ダブルクォート値のエスケープ処理対応。
    - クォート無し値のインラインコメント判定（'#' の前が空白/タブの場合のみ）。
    - 値上書き制御（override フラグ、protected による保護）。
  - Settings クラスを実装し、主要な環境変数（J-Quants / kabu API / DB パス / Paper Trading 関連 / 監視閾値 等）をプロパティで提供。
  - PAPER_FILL_MODE の検証（有効値: "instant", "partial", "never", "reject"）。
- 設定ツール
  - 対話式ウィザード (kabusys.config_setup) を追加:
    - .env の初期作成・更新を支援。
    - シークレット項目はマスク表示。
    - 生成される .env ヘッダにコミット禁止の注意を記述。
- 設定検証 CLI
  - kabusys.validate_config を追加:
    - 必須/任意環境変数の存在チェック。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DUCKDB / SQLITE パスの親ディレクトリ存在確認。
    - config/*.yaml の存在チェックと PyYAML がある場合のパース検証。
    - 本番環境 (KABUSYS_ENV=live) 向けの追加ガード（LINE 設定や Kill Switch 設定の警告）。
    - --strict オプションで警告を失敗扱いにできる。
- 実行スクリプト
  - run_execution:
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動処理。
    - 停止フラグ (data/stop_requested.flag) 検出でセッション停止。
    - 起動時にプロセス優先度を High に設定。
  - run_monitoring:
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用（監視用 DB は常に監視対象の本番 DB を参照する設計）。
    - 停止フラグ検出でループ終了。
    - 起動時にプロセス優先度を High に設定。
- 監視 DB 初期化ユーティリティ
  - init_monitoring_db 呼び出しを run_execution / run_monitoring で行い、監視用テーブルの存在を保証（冪等）。
- プロセス制御ユーティリティ
  - utils.process_priority モジュールを追加:
    - Windows と POSIX（Linux/Mac/FreeBSD）の差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS）を設定する set_process_priority。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップする設計。
- ポートフォリオ構築ライブラリ
  - portfolio モジュールを追加（純粋関数群、DB 非依存）。
    - portfolio_builder:
      - select_candidates: スコア降順＋タイブレークの実装。
      - calc_equal_weights / calc_score_weights（スコア全0 の場合は等配分にフォールバック）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中上限チェック（売却予定銘柄を露出計算から除外可）。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear、未知は警告して 1.0 フォールバック）。
    - position_sizing:
      - calc_position_sizes: risk_based / equal / score 各方式に対応。lot_size（単元）丸め、max_per_stock・aggregate cap によるスケールダウン処理、cost_buffer を反映。
- リサーチ / ファクター計算
  - research.factor_research を追加:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を DuckDB SQL で計算。データ不足時は None を返す。
    - calc_volatility: ATR/相対 ATR/20 日平均売買代金/出来高比率等を計算（実装途中ファイル末尾までの設計を含む）。
    - DuckDB を利用し prices_daily / raw_financials テーブルのみ参照する設計。
- ツール
  - tools.paper_verification_report を追加:
    - Paper Trading の検証レポート生成（DB から稼働率・注文成功率・送信率・レイテンシ等を集計）。
    - P95 計算、閾値に基づく PASS/FAIL 判定を実装。
    - --from / --to / --db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数に対応。

### Changed
- 監視・実行の DB ハンドリング設計を明確化:
  - monitoring は常に sqlite_path（本番）を参照することをドキュメント化。
  - run_execution は paper_trading モードのときに paper_sqlite_path を使い DB を完全分離。
- .env ファイルの読み込み優先度:
  - OS 環境変数 > .env.local > .env の順でロードする仕様を採用。
  - .env.local は override=True（OS 環境変数を保護しつつ上書き）。
- プロセス優先度設定を起動直後に行うように統一。

### Fixed
- 環境変数パースの各種エッジケースに対応。
  - クォート内のバックスラッシュエスケープに対応し、閉じクォートまで正しく復元。
  - クォートなし値のコメント解釈を改良（'#' の前が空白かタブの場合にコメントとみなす）。
- position_sizing のスケーリング・端数処理ロジックを実装（lot_size 単位での再配分アルゴリズム）。
- process_priority の未対応 OS や権限不足での例外を捕捉して安定化。

### Security
- config_setup による .env 出力時に「.env を絶対に Git にコミットしないこと」を明記（秘密情報の流出防止推奨）。
- Settings のシークレット値取得は環境変数を直接参照し、未設定時は ValueError で明示的にエラーを出すことで起動時に気づきやすくしている。

### Notes / Limitations
- research.calc_volatility 実装はファイル末尾で続きがある設計になっている（完全なバリデーションや補助関数は今後追加予定）。
- 一部の機能（ExecutionEngine / SystemMonitor / BrokerClientFactory 等）は本稿に含まれる他モジュールに依存しており、ここで提示されたスクリプトはそれらの実装に基づいて動作する想定。
- 権限やプラットフォーム依存の処理（プロセス優先度 / CPU affinity）は実行環境により効果が異なるため、権限不足時はスキップされる。

---

今後のリリースでは以下を予定しています:
- factor_research の完全実装とユニットテスト整備
- ExecutionEngine / Monitoring 各コンポーネントの振る舞いに対する統合テスト追加
- DuckDB ベースの分析パイプラインの安定化と最適化
- ドキュメント（README/運用手順）の充実化

もし CHANGELOG に反映してほしい追加の差分（バグ修正や改善点など）があればお知らせください。