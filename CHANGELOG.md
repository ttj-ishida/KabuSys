# Keep a Changelog — CHANGELOG.md (日本語)

すべての日付はコミット履歴がないためコード内容から推測しています。  
フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-11 (Initial release)
初回リリース。システム全体のコア機能・CLI・ユーティリティ・ポートフォリオ構築ロジック・バックテスト/検証ツールを含む。

### Added
- 全体
  - パッケージ初期化とバージョン定義を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - デフォルトのファイルパスを data/ 以下に設定（DuckDB/SQLite 等）。
- 環境設定・管理
  - 環境変数自動読み込み機能を実装（.env / .env.local をプロジェクトルートから自動読み込み）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応（src/kabusys/config.py）。
  - 柔軟な .env パーサを実装：コメント、export プレフィックス、シングル/ダブルクォート、エスケープを考慮（src/kabusys/config.py）。
  - Settings クラスを追加し、アプリケーション設定（DB パス、API トークン、環境フラグ、監視閾値など）を環境変数から取得する API を提供（src/kabusys/config.py）。
  - 対話式環境設定ウィザードを追加（.env の初期作成・更新を支援）（src/kabusys/config_setup.py）。
  - 設定検証 CLI を追加：必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや config/*.yaml の存在・パース（PyYAML が利用可能な場合）（src/kabusys/validate_config.py）。
- 実行系 / 監視
  - 実行エンジン起動スクリプトを追加（run_execution）。paper_trading 環境では MockBrokerClient と専用 SQLite DB（data/paper_trading.db）を使用し、本番 DB と分離（src/kabusys/run_execution.py）。
  - 監視ポーリングループ起動スクリプトを追加（run_monitoring）。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用する点を明示（src/kabusys/run_monitoring.py）。
  - 停止フラグ / PID 管理に対応（data/stop_requested.flag, data/execution.pid 等を参照/生成するためのロジックを導入）。
- ブローカー・実行関連
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の組立てロジック呼び出し（run_execution での組み立てフローを実装）。RiskConfig の初期設定と broker.get_available_cash() を用いた初期資金取得に対応（src/kabusys/run_execution.py）。
- 監視 DB 初期化
  - 監視用 SQLite DB（monitoring）の初期化呼び出しを実装（init_monitoring_db を使用）（run_monitoring/run_execution 内で呼び出し）。
- ツール
  - Paper Trading 検証レポート生成ツールを追加。期間指定で稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計し PASS/FAIL 判定を出力（src/kabusys/tools/paper_verification_report.py）。
- ポートフォリオ構築
  - 候補選定・重み付け関数を追加（select_candidates, calc_equal_weights, calc_score_weights）（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中排除とレジームに基づく乗数（apply_sector_cap, calc_regime_multiplier）を追加（src/kabusys/portfolio/risk_adjustment.py）。
  - ポジションサイズ計算ロジックを追加（calc_position_sizes）。複数配分方式（risk_based, equal, score）に対応し、単元株丸め、max_position_pct, max_utilization、cost_buffer による集約キャップ／スケーリングを実装（src/kabusys/portfolio/position_sizing.py）。
  - portfolio モジュールのエクスポートを整備（src/kabusys/portfolio/__init__.py）。
- リサーチ / ファクター
  - DuckDB を用いたファクター計算モジュールを追加（momentum / volatility 等の定量ファクター）。prices_daily テーブルを参照して mom_1m/mom_3m/mom_6m、MA200乖離、ATR20、平均売買代金、volume_ratio 等を算出（src/kabusys/research/factor_research.py）。
- ユーティリティ
  - プロセス優先度設定と CPU affinity ユーティリティを追加（set_process_priority, set_cpu_affinity）。Windows / POSIX の差分を吸収しアクセス権限エラーは警告でスキップ（src/kabusys/utils/process_priority.py）。

### Changed
- なし（初回リリースのため新規追加中心）

### Fixed
- .env 読み込み失敗時の警告（ファイル読み込み例外を警告して続行する実装）を導入（src/kabusys/config.py）。
- ポーリング間隔の不正値対策：MONITOR_POLL_INTERVAL の不正値は警告してデフォルト値（60秒）へフォールバック（src/kabusys/run_monitoring.py）。
- Paper Verification レポートでデータ欠損やテーブル未作成時に sqlite3.OperationalError を捕捉し、N/A 等で安全に出力するよう耐障害性を強化（src/kabusys/tools/paper_verification_report.py）。
- position_sizing の集約スケール処理で小数端数処理を安定化：lot_size 単位での再配分アルゴリズムを実装し再現性確保（src/kabusys/portfolio/position_sizing.py）。
- apply_sector_cap: unknown セクターの扱いを明確化（unknown はセクター上限の対象外）および当日売却予定銘柄をエクスポージャー計算から除外するオプションを追加（src/kabusys/portfolio/risk_adjustment.py）。

### Notes
- run_monitoring は監視用 DB に常に本番 sqlite_path を使う設計（開発・paper_trading でも監視対象は本番 DB を参照する点に注意）。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用して発注履歴を本番 DB から分離する。
- Settings.paper_fill_mode は "instant" / "partial" / "never" / "reject" のみ有効。無効値は起動時に例外を投げる。
- config_setup ウィザードで生成される .env はセキュリティのため絶対に Git にコミットしない旨が明記される。
- 実行環境（KABUSYS_ENV）が live の場合、validate_config は追加の安全ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を警告する。

## 未解決 / 今後の改善候補（コード中の TODO 等）
- position_sizing: 銘柄ごとの単元株数（lot_size）の外部マスタ化（stocks マスタからの読み込み）対応。
- apply_sector_cap: price が欠損した場合のフォールバック（前日終値や取得原価）を導入するとエクスポージャー評価が安定する。
- factor_research: データ不足時の扱いや欠損値ポリシーの明文化・テスト整備。
- CPU affinity / nice 設定は環境依存で失敗する可能性があるため、運用ドキュメントに権限要件を追記推奨。

---

（参考）重要なエントリファイル:
- src/kabusys/config.py, config_setup.py, validate_config.py
- src/kabusys/run_execution.py, run_monitoring.py
- src/kabusys/portfolio/*.py
- src/kabusys/research/factor_research.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/utils/process_priority.py

以上。必要ならリリースノートの英語版や日付・細部を実際のコミット履歴に合わせて調整します。