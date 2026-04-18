# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

最新: 0.1.0（初回リリース）

---

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 基本アプリケーション情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて本番 DB とペーパートレード用 DB を分離して使用（paper_trading は data/paper_trading.db を使用）。
    - BrokerClientFactory を経由してブローカークライアントを生成（ペーパートレードでは MockBrokerClient を想定）。
    - engine をデーモンスレッドで起動し、 data/stop_requested.flag による安全停止、execution.pid の管理。
    - RiskManager（RiskConfig）や Reconciler、OrderManager、OrderRepository の組立てを行う。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する仕様。
    - stop_requested.flag 検知、例外のロギングと回復（次ポーリングまで待機）。

- 設定管理
  - config.py: .env 自動読み込み機能を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - .env（デフォルト）と .env.local（上書き）を読み込み。OS 環境変数は保護。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env のパーサは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント扱い等に対応。
  - Settings クラスを導入し、アプリケーション設定をプロパティとして提供（J-Quants/Kabu API、DB パス、PID/kill フラグ、監視閾値、環境判定など）。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）。
    - KABUSYS_ENV の検証（development, paper_trading, live）。
    - log_level の検証。

- 設定関連 CLI
  - config_setup.py: 対話式 .env 作成ウィザードを提供。
    - デフォルト値、選択肢、シークレット入力のサポート、既存 .env の読み込みと Enter による再利用。
    - 生成される .env のテンプレートと注意事項（.env を Git にコミットしない等）。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在確認（PyYAML があればパース検証）。
    - --strict オプションで警告を FAIL 扱いにできる。
    - live 環境用の追加ガード（LINE 設定未登録や KILL_FLAG_CLEAR_ON_START の注意喚起）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補抽出（同点タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率での重み計算。スコア全てが 0 の場合は等金額配分へフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を防ぐための候補除外ロジック（sell_codes を考慮）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear をマッピング、未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 複数の配分方式に対応（risk_based / equal / score）。
      - lot_size（単元株）考慮、max_position_pct による per-stock 上限、max_utilization による投下上限、cost_buffer による保守的見積。
      - aggregate cap を超える場合のスケーリングと端数（lot 単位）配分ロジック実装。

- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（30 日分保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数からの解決、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバック。
  - utils/process_priority.py:
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）両対応でプロセス優先度設定（psutil を利用）。許可エラー等は警告でスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 固定（psutil を利用）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成 CLI を追加。期間指定オプション (--from / --to / --db) に対応。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出。
    - PASS/FAIL 判定基準（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms 等）を定義して出力。
    - P95 算出ユーティリティ、日付フィルタの構築、DB 存在チェックなどを実装。

- リサーチ（骨組み）
  - research/factor_research.py: DuckDB 接続を受け取り、モメンタム・ボラティリティ・流動性等のファクター計算を行う設計の骨組みを追加（prices_daily / raw_financials を想定）。関数 calc_momentum の実装が開始されている（ファイルは途中まで実装）。

### 変更 (Changed)
- 監視および実行スクリプトは起動直後にプロセス優先度を "high" に設定するように統一。
- ログ出力は stdout を使う（stderr ではない）方針に統一。cron / タスクスケジューラ実行時の扱いを考慮。

### 修正 (Fixed)
- .env パーサの挙動を強化：
  - export プレフィックス、クォート内のエスケープ、インラインコメントの取り扱いを改善し、より実用的な .env 構文に対応。
- calc_score_weights: 全スコアが 0 の場合に正しく等配分へフォールバックして警告を出すように修正。

### 注意事項 / ドキュメント (Notes)
- .env はセキュリティ上 Git にコミットしないこと（config_setup のヘッダにも注意書きあり）。
- paper_trading 環境は本番 DB と完全に分離されるよう設計されているため、本番データとペーパーデータの混同に注意。
- 一部モジュール（例: research/factor_research.py）は実装の途中であり、追加の実装・テストが必要。

### 依存関係（注意）
- duckdb: 分析処理・ファクター計算で使用。
- psutil: プロセス優先度・CPU affinity 設定で使用。
- PyYAML: validate_config で存在すれば config/*.yaml のパース検証を行う（任意）。

---

将来のリリースでは以下を検討してください:
- research モジュールの完全実装とユニットテスト追加。
- 設定値・しきい値の外部化（config/*.yaml から読み込み）とドキュメント化。
- 起動スクリプトのユニットテスト・統合テスト（stop flag・pid 管理の検証）。
- 銘柄別 lot_size や価格フォールバックロジックの強化（position_sizing の TODO 参照）。