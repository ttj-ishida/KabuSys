# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

注: 日付はコードベースから推測して付与しています。

## [Unreleased]

- 特になし

## [0.1.0] - 2026-04-19

### Added
- 起動スクリプトを追加
  - run_execution.py — ExecutionEngine 起動用スクリプトを追加。KABUSYS_ENV による動作分岐をサポート（paper_trading 時は MockBrokerClient を使用して data/paper_trading.db に記録）。プロセス優先度設定、PID ファイル管理、停止フラグ検出、別スレッドでのエンジン実行と安全な停止処理を実装。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能。監視用 DB 初期化、DuckDB 接続、停止フラグ検出、例外保護された poll ループを実装。

- 設定・環境管理
  - config.py — Settings クラスを追加。.env / .env.local の自動読み込み（プロジェクトルート検出）と堅牢な .env パーサ（クォート・エスケープ・export プレフィックス対応）、各種プロパティ（DB パス、API トークン、閾値、環境判定など）を提供。
  - config_setup.py — 対話式ウィザードを追加。.env の初期生成・更新を支援（シークレットマスク、既存値の再利用、書き込み）。生成された .env にコミットしない旨のヘッダを出力。

- 設定検証ツール
  - validate_config.py — 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在および PyYAML によるパース検証（PyYAML 未インストール時はスキップ）、本番環境向けの追加ガードを実装。--strict オプションで警告を失敗扱いにできる。

- ロギング・ユーティリティ
  - utils/logging_setup.py — 共通ログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

- プロセス制御ユーティリティ
  - utils/process_priority.py — プラットフォーム非依存のプロセス優先度設定（Windows/Linux/Mac 対応）および CPU affinity 設定を追加。psutil を利用し、権限不足や未対応 OS は警告でスキップ。

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py — シグナル選定（select_candidates）と配分重み（calc_equal_weights, calc_score_weights）を追加。スコア合計が 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py — セクター集中制限 apply_sector_cap と市場レジーム乗数 calc_regime_multiplier を追加。未知レジームはフォールバックと警告を出力。
  - portfolio/position_sizing.py — position sizing ロジックを追加。risk_based / equal / score の各方式に対応、単元株（lot_size）丸め、per-stock 上限と aggregate cap、cost_buffer を用いた保守的見積りとスケールダウンロジック、残差に基づく追加配分アルゴリズムを実装。

- 紙上検証ツール
  - tools/paper_verification_report.py — Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定を出力。日付フィルタ、CLI オプション、テーブル未存在時の耐性を実装。

- 研究用ファクター計算（骨組み）
  - research/factor_research.py — DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム、MA200, ATR, 出来高指標などの計算方針を実装）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。

- パッケージ情報
  - __init__.py にてパッケージ名/バージョン (0.1.0) を設定。

### Changed
- DB・環境分離の方針を明確化
  - run_execution: paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離。
  - run_monitoring: 監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。

- ロギング動作の安全化
  - logging_setup: ログディレクトリ作成に失敗した場合はファイルハンドラを作らず、コンソール出力のみで継続するように変更（起動失敗を避ける）。

- .env 自動読み込みの優先順位
  - OS 環境変数 > .env.local > .env の順で読み込む仕様を導入（既存 OS 環境変数を保護）。

### Fixed
- 環境変数の堅牢性向上
  - MONITOR_POLL_INTERVAL の不正値（非整数・0 以下）に対してデフォルト値へフォールバックし、警告を出力するように修正（run_monitoring）。
  - .env パーサが export プレフィックス、クォート、エスケープ、インラインコメント等に正しく対応するよう改善（config.py）。

- 起動・停止の回復性強化
  - 各起動スクリプトで停止フラグ（data/stop_requested.flag 等）をチェックし、安全に停止または起動停止を行うように実装。
  - run_execution: engine.run_session を別スレッドで実行し、停止フラグ検出時に engine.stop() を呼ぶことで安全停止を保証。

- 権限・プラットフォーム例外の安全ハンドリング
  - process_priority / set_cpu_affinity: psutil 関連の AccessDenied・NotImplementedError 等を捕捉して警告を出し、処理を継続するように修正。

- validate_config: PyYAML 未インストール時に YAML の検証をスキップして警告を出力するように修正（起動時の不要な ImportError を回避）。

### Security
- config_setup が生成する .env に「決して Git にコミットしないこと」と明記。機密トークンはウィザードでマスク入力可能にして露出を軽減。

### Notes / Known Issues
- research/factor_research.py の一部関数は実装が継続中（ファイル末尾が途切れている箇所あり）。詳細実装は今後のリリースで完了予定。
- portfolio.position_sizing の価格欠損（price が 0.0）に対する注記（TODO）が残っている。将来的に価格フォールバック（前日終値など）を導入する予定。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力を諦める設計だが、運用上はログディレクトリの存在を確認しておくことを推奨。

---

（この CHANGELOG はコード内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。）