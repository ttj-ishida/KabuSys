# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-17
初期リリース。主要機能の実装と CLI / ツール群を追加しました。

### Added
- 基本設定・環境変数管理
  - .env/.env.local の自動読み込みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。プロジェクトルートは .git または pyproject.toml を基準に自動検出します（src/kabusys/config.py）。
  - .env ファイルのパースを強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理対応）。無効行のスキップも実装（src/kabusys/config.py）。
  - Settings クラスでアプリケーション設定を一元化。データベースパス、Paper Trading 用 DB、各種閾値やフラグ等のプロパティを提供（src/kabusys/config.py）。

- 環境設定・検証用 CLI
  - 対話式ウィザードで .env を作成/更新する config_setup CLI を追加（src/kabusys/config_setup.py）。シークレット項目のマスク表示、既存値の再利用、確認ダイアログを実装。
  - 起動前に設定を検証する validate_config CLI を追加（src/kabusys/validate_config.py）。必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスや config/*.yaml の存在/パースチェックを実施。--strict モードで警告も失敗扱いに可能。

- 実行・監視プロセス起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading DB を使用し、本番 DB と分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てを実装。
    - 停止フラグ (data/stop_requested.flag) を監視し、検出時にセッション停止を実行。PID 管理（data/execution.pid）対応。
    - デフォルト RiskConfig を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）、初期ポートフォリオ値を broker.get_available_cash() で取得。
  - システム監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境に関わらず本番の sqlite_path を使用して監視 DB を初期化・接続。停止フラグでループ終了。
    - 起動時にプロセス優先度を high に設定。

- ポートフォリオ構築ライブラリ
  - 銘柄選定・重み付け（select_candidates / calc_equal_weights / calc_score_weights）を実装（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中制限とレジーム乗数の適用（apply_sector_cap / calc_regime_multiplier）を実装。unknown セクター扱いの挙動やフォールバックを明確化（src/kabusys/portfolio/risk_adjustment.py）。
  - ポジションサイズ計算（calc_position_sizes）を実装。risk_based / equal / score の割当方式、単元株（lot_size）丸め、aggregate キャップに基づくスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮（src/kabusys/portfolio/position_sizing.py）。
  - ポートフォリオ関連 API をパッケージとしてエクスポート（src/kabusys/portfolio/__init__.py）。

- リサーチ / ファクター計算
  - DuckDB を用いたファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム（mom_1m/mom_3m/mom_6m、ma200_dev）やボラティリティ（ATR、avg_turnover、volume_ratio）等の計算ロジックを SQL + Python で実装。
    - データ不足時の None ハンドリング、スキャン期間のバッファ設定等を実装。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収する実装。アクセス権や未サポート環境では警告を出して安全にフォールバック。
    - set_cpu_affinity によるプロセスを最初の N コアに固定する機能を提供。

- 検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標集計と PASS/FAIL 判定を実装。期間フィルタ（--from / --to）と DB 指定オプションをサポート。
    - DB のテーブル未存在時は sqlite3.OperationalError をキャッチして N/A / 0 を返す耐障害性を実装。

- パッケージ基礎
  - パッケージのバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

### Changed
- ログ・エラーハンドリングの強化
  - 環境変数パースやプロセス優先度設定で入力不正や権限エラー時に警告を出すように改良（src/kabusys/config.py, src/kabusys/utils/process_priority.py）。
  - run_monitoring / run_execution 起動時に優先度設定を最初に行うよう変更（起動直後にリソース優先度を確保）。

- DB 周りの取り扱い
  - run_execution は paper_trading 環境では paper 用 SQLite を使用して本番データと分離（src/kabusys/run_execution.py）。
  - init_monitoring_db を起動時に冪等に呼び出して監視テーブルが存在することを保証（run_monitoring/run_execution）。

### Fixed
- MONITOR_POLL_INTERVAL の検証を追加。0 以下や非整数入力はログ警告を出してデフォルトへフォールバック（src/kabusys/run_monitoring.py）。
- .env 読み込み失敗時の警告を明示（src/kabusys/config.py）。
- Paper 検証レポートでテーブル未存在時にクラッシュしないよう個別に例外処理してレポートを生成できるように（src/kabusys/tools/paper_verification_report.py）。

### Security
- .env を絶対にリポジトリにコミットしない旨を config_setup の出力ドキュメントに明記（src/kabusys/config_setup.py）。

### Notes / Implementation details
- 多くのモジュールは「DB を直接操作しない」「純粋関数で計算する」方針（ポートフォリオ系）や、DuckDB を分析用に利用する設計（research）など、運用と分析を分離する設計思想を採用しています。
- CLI ツール群はローカル開発・ペーパートレード・本番（live）を意識した挙動（DB 分離、kill/stop フラグ、LINE 通知設定の検査等）を備えています。
- 未実装/要注意箇所はコード内に TODO コメントとして残しています（例: price のフォールバックロジック、銘柄別 lot_size など）。

---

今後の予定（例）
- Strategy / Execution のより詳細なユニットテスト追加
- 銘柄別 lot_size 対応、手数料モデルの明示的導入
- Paper Trading の検証自動化（CI 連携）
- ドキュメント（PortfolioConstruction.md 等）の整備・公開

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴・PR 説明を基に調整してください。）