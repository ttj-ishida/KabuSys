CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/

Unreleased
----------

- ドキュメントやユーティリティ等の小修正・調整（作業中の項目あり）。

0.1.0 - 2026-04-23
-----------------

初回リリース — KabuSys の基本機能を実装しました。以下はコードベースから推測してまとめた主な追加・変更点です。

Added
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB（data/paper_trading.db）を使用し、本番 DB と完全分離して MockBrokerClient を利用する仕組みをサポート。
    - 起動時にプロセス優先度を "high" に設定する処理を追加（utils.process_priority）。
    - 停止制御用のフラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応、フラグ検知でエンジンを安全に停止。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path（data/monitoring.db）を使用する仕様。
    - 停止フラグ検知でループを終了し、リソースをクリーンに閉じる。

- 設定・環境変数管理
  - config.py
    - 環境変数をラップする Settings クラスを実装。各種設定（J-Quants・kabu API・DB パス・監視しきい値等）をプロパティとして提供。
    - プロジェクトルート検出（.git または pyproject.toml を探索）に基づき .env/.env.local の自動読み込みを行う（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env のパースロジックは引用符やエスケープ、インラインコメントの扱いに対応。
    - PAPER_FILL_MODE（paper trading の fill 動作）、KILL_FLAG_CLEAR_ON_START、各種閾値などの設定項目を定義。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - デフォルト値、選択肢、シークレット入力、既存 .env の取り込み、保存確認などの UX を提供。

  - validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数の存在、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース確認、本番環境向けのガードチェック等を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、タイブレークに signal_rank）と等重・スコア加重ウェイト計算を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバック（警告ログ）。

  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）を実装。既存保有のセクター別エクスポージャーを計算し、上限超過セクターの候補除外を行う。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマップ、未知レジームはフォールバック）。

  - portfolio/position_sizing.py
    - 発注株数決定ロジックを実装（risk_based / equal / score の方式に対応）。
    - 単元株（lot_size）で丸め、ポジション上限・利用率上限・cost_buffer を考慮した aggregate cap（スケーリング）処理を実装。
    - 価格欠損時のスキップやログ出力など堅牢化。

- ユーティリティ
  - utils/logging_setup.py
    - 全アプリで共通利用できるログ設定ユーティリティを追加。
    - stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）でログをファイルに保存（デフォルト logs/、30 日保持）。
    - LOG_DIR/LOG_LEVEL 環境変数や引数での上書きに対応。ディレクトリ作成失敗時はコンソールのみで継続。

  - utils/process_priority.py
    - Windows/Linux/macOS を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定を追加。psutil を利用し、権限や未サポート OS の場合は警告を出してスキップ。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などの SQLite テーブルを集計し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を算出して PASS/FAIL 判定を出力。
    - --from/--to/--db オプション対応。P95 計算・しきい値（稼働率99%、成功率90% など）を定義。

- 研究用モジュール（部分実装）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールを設置。Momentum / Value / Volatility / Liquidity の計算を設計し、calc_momentum 等の骨組みを実装（関数途中で実装が途切れている箇所あり）。

Changed
- パッケージメタ
  - __init__.py にバージョン情報 __version__ = "0.1.0" を設定。

Fixed
- 環境変数パーサーの堅牢化
  - config._parse_env_line で export プレフィックス、引用符内部のバックスラッシュエスケープ、インラインコメント処理、空行/コメント行の無視などを適切に処理するよう実装し、.env 読み込みの信頼性を向上。

- 監視・起動の安全性強化
  - stop flag / pid file / kill flag 関連の取り扱いを各スクリプトで明示的に扱い、起動時の誤発注や強制再起動リスクを低減。

Notes / Known issues
- research/factor_research.calc_momentum はファイル末尾で実装途中で終了しており、完全実装が必要（コード末尾が不完全に切れている）。
- 一部 TODO コメントあり（例: position_sizing の銘柄別 lot_size の将来的拡張、risk_adjustment の price 欠損時のフォールバック処理など）。運用での精度向上や堅牢化に向けた追加実装が想定される。
- DuckDB / PyYAML 等の外部依存が必須（validate_config は PyYAML がなければ YAML 検証をスキップする）。

Security
- 本バージョンでは機密情報（API トークン等）を .env に保存する設計になっており、README 等で .env を Git に含めない注意喚起が記載されています（config_setup.py のヘッダ参照）。本番運用時は適切なシークレット管理を推奨します。

参考（主な CLI / 起動方法）
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

--- 
今後のリリースでは research モジュールの完成、テスト整備、エラーハンドリング強化、戦略バックテスト・デプロイ周りの CI/CD やドキュメント充実を推奨します。