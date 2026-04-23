# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

<!-- 未リリースの変更があればここに記載 -->
## [Unreleased]

---

## [0.1.0] - 2026-04-23

初回リリース。KabuSys の基本的な実行・監視・設定・ポートフォリオ構築ユーティリティを実装しました。

### Added
- 基本パッケージの導入
  - パッケージバージョン: `kabusys` v0.1.0 （src/kabusys/__init__.py）
- 設定管理
  - Settings クラスで環境変数による設定を一元管理（src/kabusys/config.py）
  - .env 自動読み込み機構（プロジェクトルート検出: .git / pyproject.toml ベース）
  - .env パースの堅牢化（クォート・エスケープ・コメント処理対応）
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）
  - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等の Paper Trading 用設定対応
- 対話式設定ウィザード
  - `kabusys.config_setup` により .env を対話的に生成/更新する CLI を提供（src/kabusys/config_setup.py）
- 設定検証ツール
  - `kabusys.validate_config` CLI：.env と config/*.yaml の事前チェック（PyYAML 未導入時は YAML 検証をスキップ）および本番環境向けガードチェックを実装（src/kabusys/validate_config.py）
- 実行・監視ランチャー
  - `run_execution.py`: ExecutionEngine 起動スクリプト（paper_trading モードで MockBroker を使用して本番 DB と分離）  
    - paper_trading 時は専用 SQLite（デフォルト: data/paper_trading.db）を使用
    - 実行中は PID ファイルを書き込み、データフォルダの停止フラグで停止制御
  - `run_monitoring.py`: SystemMonitor のポーリングループ起動スクリプト  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）
    - 監視 DB は環境にかかわらず指定の sqlite_path を使用する旨を明記
- 監視 DB 初期化ユーティリティ
  - monitoring テーブル群の初期化呼び出しを起動時に行う（init_monitoring_db）
- 実行コンポーネント（骨組み）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler（起動スクリプトから組み立てて起動する構成）
  - RiskConfig / EngineConfig のデフォルト値設定（例: rate_limit_per_sec, max_position_pct 等）
- データベース/分析連携
  - DuckDB 連携（duckdb による分析用 DB パス設定: DUCKDB_PATH）
- ロギング / 実行環境ユーティリティ
  - 統一ログ設定ユーティリティ（stdout ストリーム + 日次ローテーションファイル出力 / logs/<app>.log、30日分保持）を実装（src/kabusys/utils/logging_setup.py）
    - LOG_DIR / LOG_LEVEL によるカスタマイズ、ディレクトリ作成失敗時はコンソール出力のみで継続
  - プロセス優先度 & CPU affinity 設定ユーティリティ（クロスプラットフォーム対応、例外は警告でスキップ）を実装（src/kabusys/utils/process_priority.py）
- ポートフォリオ構築ライブラリ（純粋関数群、DB非依存）
  - 銘柄候補選定: select_candidates（スコア降順、signal_rank でタイブレーク）
  - 重み計算: calc_equal_weights, calc_score_weights（スコア全0時は等配分へフォールバック）
  - セクター集中度制限: apply_sector_cap（既存ポジションのセクター比率が閾値を超える場合に候補除外）
  - レジーム乗数: calc_regime_multiplier（bull/neutral/bear => 1.0/0.7/0.3、未知レジームは 1.0 フォールバック）
  - ポジションサイズ計算: calc_position_sizes  
    - allocation_method: "risk_based", "equal", "score" をサポート
    - 単元株（lot_size）丸め、per-asset 最大上限、aggregate cap（available_cash）に基づくスケールダウン、余剰キャッシュに対する端数分配ロジックを実装
    - cost_buffer による保守的コスト見積りを考慮
- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定
    - 日付フィルタ（--from/--to）と DB 指定オプション --db をサポート
- リサーチ（未完のファクタ計算基盤）
  - factor_research モジュールを追加（DuckDB 参照で Momentum / Value / Volatility / Liquidity の計算を想定）  
    - calc_momentum の設計と定数定義を追加（実装継続中）

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- .env ファイルは生成時にコミットしない旨の注意を .env テンプレートに明記（config_setup の出力）

### Notes / Implementation details
- run_monitoring は MONITOR_POLL_INTERVAL が不正（非正数や数値以外）の場合に安全にデフォルトにフォールバックし、警告ログを出力します。
- Settings.env の検証により KABUSYS_ENV の不正値は起動時に例外を投げます。validate_config により起動前検査が可能です。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム非対応時に警告を出し続行します（起動失敗を避ける設計）。
- apply_sector_cap 内で価格が欠損（0.0）の場合に過少評価される可能性があることを注記（将来的な改善点: フォールバック価格の導入）。

### Known issues / TODO
- factor_research.calc_momentum の実装が途中（ファイル末尾で切れている状態）であり、完全なファクター計算ロジックは今後追加予定。
- risk_adjustment.apply_sector_cap の価格欠損に対するフォールバックが未実装（コメントで TODO を残しています）。
- 単元株 (lot_size) を銘柄毎に管理する機能は未実装（全銘柄共通の lot_size を想定）。将来的に銘柄別 lot_map 対応を検討。

---

（リリースノートはコードベースの実装から推測して作成しています。運用上の細かい振る舞いや外部依存の挙動は実行環境や追加のモジュール実装に依存します。）