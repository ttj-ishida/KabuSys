CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
要約は日本語で記載しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-17
------------------

Added
- 基本パッケージ初回リリース。
- 環境設定・読み込み
  - Settings クラスを追加。環境変数からアプリ設定を取得する単一インターフェースを提供（J-Quants / kabuステーション / DB / ログ / 監視閾値等）。
  - 自動 .env 読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数を保護する機能と KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションをサポート。
  - .env パーサーの強化: export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行内コメントの扱い（クォート無の '#' は直前が空白/タブの場合にコメントと認識）。
- 設定関連 CLI
  - config_setup: 対話式 .env 作成・更新ウィザードを追加。シークレットはマスク表示、既存値の読み込み、確認画面、.env 出力テンプレートを実装。
  - validate_config: .env と config/*.yaml の検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、PyYAML による YAML 構文検証（未インストール時は警告）、本番環境向け追加ガード、--strict オプションをサポート（警告を FAIL 扱い）。
- 実行 / 監視エントリポイント
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を起動時に設定（set_process_priority("high")）。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB と分離（MockBrokerClient を利用する設計に対応）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行。data/execution.pid を PID ファイルとして使用し、data/stop_requested.flag による停止監視を実装。
    - RiskConfig のデフォルト値を含む初期設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10...）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計（monitoring DB 初期化 init_monitoring_db を実行）。
    - stop flag（data/stop_requested.flag）検出でループ終了。KeyboardInterrupt のハンドリングと DB 接続のクリーンアップを実装。
- データベース / 分析基盤
  - DuckDB 接続を分析用途に採用（Settings.duckdb_path）。
  - 監視用 SQLite 初期化ユーティリティ init_monitoring_db を利用。
- ユーティリティ
  - process_priority: クロスプラットフォームでのプロセス優先度設定ユーティリティを追加（Windows/Linux/macOS の差分吸収）。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。psutil が投げるアクセス権限例外等を捕捉しフォールバック。
- Portfolio（ポートフォリオ構築）
  - portfolio_builder: 候補選定 select_candidates（スコア降順、同点は signal_rank 昇順）、等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等分にフォールバック）を実装。
  - risk_adjustment: apply_sector_cap（セクター集中上限の適用、"unknown" セクターは制限除外）、calc_regime_multiplier（レジームに応じた投下資金乗数: bull/neutral/bear のマップ、未知レジームは警告の上 1.0 にフォールバック）を実装。
  - position_sizing: calc_position_sizes を実装。allocation_method による計算（"risk_based" / "equal" / "score"）をサポートし、
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）を考慮。
    - cost_buffer を使った保守的コスト見積りと aggregate cap 超過時のスケーリング（スケール適用後の端数を lot 単位で残差順に追加配分）を実装。
- リサーチ / ファクター計算
  - factor_research: DuckDB 接続を用いたファクター計算実装（モメンタム: mom_1m/mom_3m/mom_6m, MA200乖離；ボラティリティ: ATR20, 相対 ATR, 20日平均売買代金等）。集計ウィンドウは営業日ベースでのラグ計算を行い、データ不足時は None を返す設計。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、P95 レイテンシ等を集計。閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL 判定を出力。
    - P95 パーセンタイル計算を実装し、日付範囲フィルタ（ISO8601 UTC 文字列）を受け付ける。DB が存在しない場合のエラーメッセージを表示。

Changed
- パッケージメタ
  - パッケージバージョンを __version__ = "0.1.0" に設定。

Fixed
- （初回リリースのため過去のバグ修正記録なし）

Security
- .env の取り扱いに関する注意喚起を config_setup の出力コメントに記載（.env を Git に含めない旨を強調）。

Notes / Implementation details
- .env の読み込み順は OS 環境変数 > .env.local > .env（.env.local は OS 環境変数を保護しつつ上書き可能）。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" にしようとするが、権限不足などで変更できない場合は警告を出してスキップする安全設計。
- Paper Trading（paper_trading）実行時は本番 DB と完全分離されるよう paper_sqlite_path を利用する設計になっている（PAPER_TRADING_SQLITE_PATH により上書き可能）。
- 一部モジュール（例: factor_research）の実装は DuckDB 上のテーブル構成（prices_daily / raw_financials 等）を前提としており、データ準備が必要。

Breaking Changes
- なし（初回リリース）

Acknowledgments
- このリリースは内部モジュール群（設定、CLI、監視・実行、ポートフォリオ構築、リスク制御、位置決め、分析ツール）を含む初期実装をまとめたものです。次期リリースではテストカバレッジ、ドキュメント（API / 設定例）、および broker クライアントの concrete 実装（実発注ロジック）の追加を予定しています。