# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

※ 日付はコードベースから推測したリリース日を付与しています。

## [Unreleased]

- 改善予定 / TODO を記載
  - apply_sector_cap: 価格データ欠損時のフォールバック（前日終値や取得原価）を実装してエクスポージャー計算の過少評価を防ぐ。
  - position_sizing: 銘柄ごとの単元（lot_size）を銘柄マスタで管理する拡張（現状は一律単元を仮定）。
  - monitoring/run: 停止・Kill フラグや PID 管理の運用ガイド整備。
  - research モジュールの追加ファクターや Z スコア正規化の公開インタフェース整備。
  - バックエンド（DuckDB / SQLite）周りのマイグレーション/スキーマ管理ツールの追加検討。

---

## [0.1.0] - 2026-04-17

### Added
- 初期リリース: KabuSys v0.1.0 を追加。
  - 日本株自動売買システムのコア機能群（環境管理、実行/監視スクリプト、ポートフォリオ構築、ポジションサイズ計算、リスク調整、ファクター研究、ツール類、ユーティリティ）を実装。

- CLI / スクリプト
  - config_setup: .env の対話式ウィザードを追加（python -m kabusys.config_setup）。既存 .env の読み込み・上書き、秘密項目のマスク表示、保存確認をサポート。
  - validate_config: 起動前の設定検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数・環境種別・ログレベル・DB パス・config/*.yaml の存在とパース検証（PyYAML がない場合は警告）などをチェック。--strict モードをサポート。
  - run_execution: ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を設定し、BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでの ExecutionEngine.run_session 実行、停止フラグ・PID 管理を実装。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db デフォルト）を使用し、本番 DB と完全分離する。
  - run_monitoring: SystemMonitor 起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境に関わらず本番 sqlite_path を使用する設計。

- 環境・設定管理
  - config: プロジェクトルート自動検出機能を導入（.git または pyproject.toml を探索）。.env 自動読み込みロジックを追加（OS 環境変数を保護しつつ .env, .env.local を読み込み）。.env パースを強化（export プレフィックス対応、クォート内エスケープ、インラインコメント処理）。
  - Settings クラスを追加し、J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別 等のプロパティを提供。入力検証（KABUSYS_ENV／LOG_LEVEL／PAPER_FILL_MODE の妥当性チェック）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（スコア合計が 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中を制限するフィルタ（既存保有のセクター比率が閾値を超える場合に新規候補を除外）。"unknown" セクターは上限適用対象外とする挙動を明記。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を実装（bull/neutral/bear を 1.0/0.7/0.3 にマップ、未知のレジームは 1.0 フォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づいた株数計算を実装。単元（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。cost_buffer を導入して手数料・スリッページを保守的に見積る。スケールダウン後の残差配分ロジックを実装。

- 研究（research）
  - factor_research:
    - calc_momentum: DuckDB の window 関数を用いて 1M/3M/6M リターンと MA200 乖離率を算出。データ不足時は None を返す挙動。
    - calc_volatility: ATR（20日）、20日平均売買代金、出来高比率等を計算する SQL 実装を追加。true_range の NULL 伝播制御や窓内データ不足判定を考慮。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを追加。期間フィルタ、稼働率・注文成功率・送信率・P95 レイテンシ等の指標算出と PASS/FAIL 判定（閾値はソース内定義）をサポート。P95 計算の実装を含む。

- データベース / 分析
  - DuckDB を分析用データストアとして導入（デフォルトパス data/kabusys.duckdb）。monitoring / execution の両方で DuckDB 接続を取得する設計。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows (psutil の priority class) と POSIX (nice) を吸収するクロスプラットフォーム API を提供。権限不足や未対応 OS は警告でスキップする。
    - set_cpu_affinity: 指定コア数にプロセスをピン留めするユーティリティを追加（未指定時は noop）。例外時は警告でスキップ。

- その他
  - パッケージメタ情報: __version__ = "0.1.0" を設定。
  - パッケージ API エクスポートを整備（kabusys.portfolio の __all__ 等）。

### Changed
- アプリケーション設計: Paper Trading と 本番の DB を明確に分離（paper_trading 用 SQLite をサポート）。これによりペーパートレードは本番 DB に影響を与えない。
- 実行コンポーネントの分離: ExecutionEngine を中心に Broker / OrderManager / RiskManager / Reconciler / OrderRepository を組み立てる構成を採用し、単体テスト・差し替え可能性を高めた。
- 設定ファイル読み込み順序を OS 環境変数 > .env.local > .env の優先順位で実装。

### Fixed
- .env 解析の堅牢化:
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いを正しく処理するよう改善。
- run_monitoring:
  - MONITOR_POLL_INTERVAL の不正値に対するデフォルトフォールバックを追加（無効値・0 以下は 60 秒に戻す）。
  - 停止フラグ検知・KeyboardInterrupt による安全な終了と DB 接続クローズを確実に行うようにした。
- paper_verification_report:
  - データが存在しない場合の各種クエリ例外を捕捉して N/A 表示にフォールバックするようにした。

### Known issues / Notes
- apply_sector_cap 内で price_map に欠損（0.0）がある場合、エクスポージャーが過少見積りされてブロックが緩くなる可能性がある（TODO にてフォールバック実装予定）。
- position_sizing は現時点で銘柄毎単元の差異を考慮していない（将来の拡張ポイント）。
- process_priority / cpu_affinity は権限やプラットフォーム依存で失敗するケースがあり、その際は警告でスキップされる。
- validate_config は PyYAML 非インストール時に YAML 検証をスキップする（警告を出力）。

### Security
- 特に重大なセキュリティ修正は含まれていません。環境変数（.env）に API トークン等を保存するため、.env をリポジトリにコミットしないよう README 等で明確に注意喚起することを推奨します（config_setup でも同様の注意文を出力）。

---

（以降のバージョンでは新機能・変更・修正点をここに追記してください）