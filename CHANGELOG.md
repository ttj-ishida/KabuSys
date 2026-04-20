# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。

全項目はコードベースから推測して記載しています。

## [0.1.0] - 2026-04-20

### 追加 (Added)
- 初回リリースとして以下の主要機能を実装。
  - 環境設定 / 実行用ユーティリティ
    - Settings クラスによる環境変数ベースの設定取得（src/kabusys/config.py）。
      - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL などの検証を実施。
      - デフォルトの DB パス: DUCKDB_PATH=`data/kabusys.duckdb`、SQLITE_PATH=`data/monitoring.db`。
      - PAPER_TRADING 用 DB パス: PAPER_TRADING_SQLITE_PATH（デフォルト `data/paper_trading.db`）。
      - PAPER_FILL_MODE（"instant" | "partial" | "never" | "reject"）の検証実装。
      - PID / kill flag 関連設定をプロパティで提供。
    - 自動 .env ロード機能
      - プロジェクトルートを `.git` または `pyproject.toml` から検出して `.env` / `.env.local` を読み込む。
      - OS 環境変数の保護（既存の値を上書きしない / .env.local は上書き可能）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env ファイルパーサーはクォート（単一・二重）・エスケープ・インラインコメント・`export KEY=...` 形式に対応。

  - 起動スクリプト / デーモン管理
    - run_execution: ExecutionEngine を起動するエントリポイント（src/kabusys/run_execution.py）。
      - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を使用し、MockBrokerClient を利用（本番 DB と完全分離）。
      - stop flag (`data/stop_requested.flag`) による安全停止処理、実行 PID ファイルの扱い。
      - ExecutionEngine の構成（OrderRepository、OrderManager、RiskManager、Reconciler 等）の組み立て。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は常に本番用 sqlite_path を参照する設計（環境に関わらず監視データは共通の監視 DB に保存）。

  - 設定関連 CLI / ユーティリティ
    - config_setup: 対話式 .env 作成ウィザード（src/kabusys/config_setup.py）。
      - 初期値・選択肢・シークレット入力対応、保存前の確認プロンプト、.env の出力テンプレートを提供。
    - validate_config: 起動前の設定検証 CLI（src/kabusys/validate_config.py）。
      - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在とパース検証（PyYAML 利用時）。
      - --strict モードで警告をエラーとして扱うオプション。

  - ロギング / プロセス制御ユーティリティ
    - setup_logging: 統一ロギング設定（src/kabusys/utils/logging_setup.py）。
      - stdout への StreamHandler（stdout を使用）、日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）。
      - LOG_DIR 指定・作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - process_priority: OS 横断のプロセス優先度 / CPU アフィニティ設定（src/kabusys/utils/process_priority.py）。
      - Windows（psutil の優先度定数） / POSIX (nice 値) に対応。CPU affinity 設定も提供。
      - 権限不足等で失敗しても警告ログを出してスキップする設計。

  - ポートフォリオ構築関連（純粋関数群）
    - portfolio_builder: 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）。
      - select_candidates: スコア降順、同点時は signal_rank 小のものを優先して上位 N 件を返す。
      - calc_equal_weights / calc_score_weights（スコア全 0 の場合は等金額へフォールバック）。
    - risk_adjustment: セクター上限適用、レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
      - apply_sector_cap: 既存保有比率が上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: "bull"/"neutral"/"bear" に対応する乗数（1.0/0.7/0.3）、未知レジームは警告を出し 1.0 にフォールバック。
    - position_sizing: 株数算出ロジック（src/kabusys/portfolio/position_sizing.py）。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - lot_size 単位で丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap によるスケールダウンロジックを実装。
      - 価格欠損時のスキップとログ出力、残余キャッシュを利用した端数割当ロジックを実装。

  - 分析・レポートツール
    - tools/paper_verification_report: Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）。
      - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg / max / P95）を集計して標準出力にレポート出力。
      - P95 計算、期間フィルタ（--from/--to）、DB パス解決（--db / env / デフォルト）を実装。
      - 判定閾値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）および PASS/FAIL 表示を実装。

  - リサーチ基盤（骨組み）
    - research/factor_research.py にて DuckDB を利用したファクター計算モジュールの骨組みを実装（モメンタム / MA200 / ATR / 出来高関連等。未完の関数あり、設計方針と定数を定義）。

  - パッケージ情報
    - パッケージ初期バージョン __version__ = "0.1.0" を追加（src/kabusys/__init__.py）。

### 変更 (Changed)
- なし（初回リリースのため）。

### 修正 (Fixed)
- なし（初回リリースのため）。

### 注意事項 / 実装上の補足 (Notes)
- run_monitoring は監視 DB（SQLITE_PATH）を環境にかかわらず本番用パスから接続します。監視データを分離したい場合は別途設定や運用上の調整が必要です。
- process_priority や CPU affinity の設定は権限依存のため、失敗した場合はログ警告でスキップされます（致命的ではありません）。
- .env パーサはクォートやエスケープ、インラインコメントをある程度考慮していますが、複雑なケースでは期待通りに解析されない可能性があるため注意してください。
- position_sizing の価格欠損（price が 0.0 など）に対する TODO が残っています。将来的に前日終値等のフォールバックを導入する予定です。
- config/*.yaml の存在チェックは PyYAML がインストールされている場合にパース検証を実施します。PyYAML がない場合は警告を出してスキップします。

---

今後のリリースでは、factor_research の完全実装、ExecutionEngine や SystemMonitor の詳細な実装（現在は起動と接続周りの統合が中心）に関する追加変更、テスト・ドキュメントの整備を予定しています。