# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
日付は本コードベースから推測した初回リリース日として 2026-04-24 を使用しています。

## [Unreleased]

- 今後の機能追加候補・既知の改善点（コード内コメントより推測）
  - portfolio.position_sizing: 銘柄ごとの lot_size をマスタから受け取るよう拡張（TODO）。
  - portfolio.risk_adjustment: 価格欠損時（price == 0.0）のフォールバック価格（前日終値や取得原価）対応。
  - research.factor_research: ファイル末尾が途中で切れているため、計算ロジックの残り実装・テストが必要。
  - ログ周りやファイル作成失敗時のエラーハンドリング強化、より詳細な監視ルールの追加検討。

---

## [0.1.0] - 2026-04-24

初回リリース。以下の主要機能を実装。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys v0.1.0）。
  - パッケージ構成（execution, monitoring, portfolio, utils, research, tools などのモジュール群）。

- 実行系 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV により paper_trading 用 DB を分離（settings.paper_sqlite_path を使用）。
    - BrokerClientFactory を介してブローカークライアントを生成。
    - ExecutionEngine をデーモンスレッドで起動し、data/stop_requested.flag による停止制御を実装。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知によるループ終了。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する設計。

- 設定管理 / CLI
  - config.py: 環境変数・設定管理モジュールを追加。
    - .env 自動ロード機能（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - .env ファイルのパースはクォート・エスケープ・インラインコメント等に対応。
    - Settings クラスで多数の設定プロパティを公開（DB パス、API トークン、監視閾値、KABUSYS_ENV 判定 等）。
    - 環境の妥当性チェック（KABUSYS_ENV / LOG_LEVEL の許容値チェックなど）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - .env の既存値読み込み、シークレット項目のマスク表示、保存確認、ファイル書き出し。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の検査、パスの親ディレクトリ存在チェック、config/*.yaml の存在とパース（PyYAML が無ければスキップ）、
      本番時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性の警告）等を実施。
    - --strict フラグで警告をエラー扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順選別（タイブレークとして signal_rank を使用）。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等分配へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限ロジック（既存ポジションのセクター別エクスポージャーに基づき、新規候補を除外）。
      - unknown セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数の算出（未知レジームはフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
      - 単元（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer の考慮。
      - スケールダウン時は端数の再配分を行い、lot 単位で追加配分。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテート TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を root ロガーへ設定。
    - LOG_DIR / LOG_LEVEL / 引数での上書きに対応。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定と CPU affinity 設定を追加（Windows / POSIX 対応）。
    - set_process_priority("high"|"normal"|"low"), set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS では警告を出して安全にスキップ。

- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプトから利用して監視用テーブルの存在を保証（冪等処理）。

- Paper Trading / 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ指標（平均 / 最大 / P95）など。
    - Pass/Fail 基準値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 latency <= 200 ms）。
    - 日付フィルタ（--from / --to）と --db オプションに対応。
    - DB テーブルが存在しない場合でもエラーを吸収して N/A を表示する耐障害性を備える。

- Research
  - research.factor_research.py（ファクター計算モジュール）
    - Momentum / Value / Volatility / Liquidity 等ファクター計算の枠組みと定数を実装開始。DuckDB の prices_daily / raw_financials テーブルを参照して計算する設計。
    - calc_momentum の関数シグネチャ等を実装（ファイル末尾は未完）。

### Changed
- 初期リリースのため該当なし（新規追加が中心）。

### Fixed
- 初期リリースのため該当なし。

### Removed
- 初期リリースのため該当なし。

### Security
- 初期リリースのため該当なし。
  - 注意: .env ファイルは Git に絶対にコミットしない旨を config_setup.py に明記。

---

注記（実装上の重要ポイント / 既知の振る舞い）
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる（配布後も安全）。
- .env の読み込み順は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- run_monitoring と run_execution は起動時にプロセス優先度を "high" に設定しようとする（権限不足時は警告で継続）。
- Paper Trading は本番 DB と完全分離される（settings.is_paper 判定により paper_sqlite_path を使用）。
- いくつかの箇所に TODO / 将来的な拡張メモが残されている（価格フォールバック、銘柄別 lot_size、research の未完部分など）。

もし特定機能について詳しい記述（例: API 仕様、DB スキーマ、CLI 使用例など）が必要であれば、該当ソースファイルを元に追記します。