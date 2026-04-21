# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを実装しました。
- 実行エントリ:
  - run_execution: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、ExecutionEngine のスレッド実行・停止制御（停止フラグ監視）を実装。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検知・例外保護・DBクローズ処理を実装。
- 設定管理:
  - config: .env 自動読み込み（.env / .env.local、OS 環境変数を優先）と Settings クラスを実装。多くの設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 関連設定等）を提供。
  - config_setup: 対話式 .env 作成/更新ウィザードを実装（python -m kabusys.config_setup）。
  - validate_config: 起動前検証 CLI を実装。必須環境変数や config/*.yaml の存在/パース検証、--strict オプションをサポート（python -m kabusys.validate_config）。
- ユーティリティ:
  - logging_setup: 統一ログ設定ユーティリティを追加。コンソール (stdout) と日次ローテーションのファイルハンドラをルートロガーに設定。ログディレクトリ作成のフォールバック処理や LOG_LEVEL / LOG_DIR の解決をサポート。
  - process_priority: プロセス優先度設定・CPU affinity ユーティリティを追加。Windows / POSIX の差を吸収して安全に優先度設定を試行。
- ポートフォリオ構築（純粋関数群、DB 参照なし）:
  - portfolio.portfolio_builder: 候補選定 select_candidates、等配分 calc_equal_weights、スコア配分 calc_score_weights を実装。
  - portfolio.risk_adjustment: セクター上限適用 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。
  - portfolio.position_sizing: position sizing ロジック calc_position_sizes を実装。risk_based / equal / score の配分方式、単元株（lot_size）、手数料・スリッページ考慮（cost_buffer）、aggregate cap スケールダウン等をサポート。
  - kabusys.portfolio パッケージのエクスポートを追加。
- 分析 / リサーチ:
  - research.factor_research: ファクター計算モジュールの実装を開始（モメンタム等の計算ロジックの基盤を用意）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。
- ツール:
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。期間指定オプション（--from, --to）および --db 指定をサポート。稼働率、注文成功率/送信率、P95 レイテンシ等の指標を出力し、閾値に基づく PASS/FAIL 判定を行う。デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。
- パッケージ基礎:
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

### 変更 (Changed)
- .env 読み込み挙動:
  - 自動ロードの優先順位を OS 環境変数 > .env.local > .env として実装。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルール等に対応。
- DB 周りの取り扱い:
  - run_monitoring は KABUSYS_ENV にかかわらず「本番」sqlite_path を使用して監視 DB に接続する設計（監視データは本番 DB に記録する意図）。
  - run_execution は KABUSYS_ENV=paper_trading の場合、専用の paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
  - 監視テーブルが存在することを保証する init_monitoring_db を各起動時に呼び出す（冪等）。
- ロギング:
  - StreamHandler を stdout に向けることで cron/Task Scheduler 等でのリダイレクト運用を想定。
  - 日次ローテーションは 30 日分保持に設定。

### 修正 (Fixed)
- process_priority と CPU affinity の設定失敗時に例外で停止しないように警告ログにフォールバックする安全策を追加。
- run_monitoring 内の MONITOR_POLL_INTERVAL 環境変数の不正値（非正整数等）に対して警告を出しデフォルト 60 秒へフォールバックするバリデーションを追加。

### 注意事項 (Notes)
- PAPER_FILL_MODE は "instant" / "partial" / "never" / "reject" のいずれかであることを Settings で検証します（不正な値は例外）。
- config_validate は PyYAML が未インストールの場合、YAML 内容検証をスキップして警告を出します。
- position_sizing の一部（価格が欠損した場合のフォールバック等）については TODO コメントが残っており、将来的な改善余地があります。
- run_execution/run_monitoring は停止制御にプロジェクトルート下の data/stop_requested.flag 等のファイルを使用します。運用時はこれらのファイル管理に注意してください。

### 既知の制約 (Known issues)
- research.factor_research の実装はファイルの途中で切れている箇所があり、未完部分が存在する可能性があります（今後の追加実装を想定）。
- 単元株（lot_size）は現状グローバルな共通値（デフォルト 100）として扱っており、将来は銘柄ごとの単元対応が必要。

---

（以降のリリースでは Unreleased セクションを使い、変更点を差分で記録してください。）