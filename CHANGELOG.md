# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
フォーマット: "Unreleased" とリリースごとのセクションを用意しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-17

初回公開リリース。主要な機能追加・設計方針を以下にまとめます。

### Added

- 全体
  - パッケージ初期版として各種モジュール・CLI・ユーティリティを追加。
  - パッケージバージョンを __version__ = "0.1.0" に設定（src/kabusys/__init__.py）。

- 実行・監視
  - run_execution: ExecutionEngine 起動用スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 実行制御用に data/execution.pid（デフォルトパス）や stop フラグを利用し、別スレッドでエンジンを実行・停止する仕組みを導入。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期ポートフォリオ値をブローカーから取得して初期化。

  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する（監視データは共通の本番 DB に記録）。
    - 停止検知フラグ（data/stop_requested.flag）の検出でループ終了。例外はログ出力して次のポーリングに進む保守的な実行。

- 設定管理・CLI
  - Settings クラスを実装し、環境変数からアプリケーション設定を取得（src/kabusys/config.py）。
    - .env 自動読み込み機能を実装（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
    - .env ファイルのパースは export プレフィックス、クォート文字列、インラインコメント（スペース直前の#）等に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB / 監視閾値 / システムフラグ等）。
    - paper_fill_mode の入力検証、KABUSYS_ENV / LOG_LEVEL の検証ロジックを搭載。
  - config_setup: 対話式 .env ウィザードを追加（src/kabusys/config_setup.py）。
    - 各設定項目の説明付き入力、シークレットマスク、既存 .env の読み込み・上書き、.env ファイル生成機能を提供。
  - validate_config: 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の妥当性確認、DB パス / config/*.yaml の存在・パースチェック（PyYAML が無ければ警告）等を実行。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: 候補選定と重み計算を追加（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: スコア降順で上位 N を選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
  - risk_adjustment: セクター集中制限とレジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存ポジションを考慮してセクター上限を超える候補を除外（unknown セクターは適用対象外）。
    - calc_regime_multiplier: レジーム ("bull","neutral","bear") に応じた投下資金乗数を返す。未知レジームはフォールバックで 1.0（警告ログ）。
  - position_sizing: 株数決定・リスク制限・単元丸めロジックを追加（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method に応じた計算 ("risk_based","equal","score")。
    - 単元株（lot_size）で丸め、1銘柄上限や aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - スケーリング時の再配分は fractional remainder に基づき lot 単位で追加配分するアルゴリズムを導入。
    - cost_buffer を考慮して手数料/スリッページを保守的に見積もる。

- リサーチ / ファクター計算
  - factor_research: DuckDB を用いたファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M リターン、MA200 偏差）、Volatility（ATR20、相対 ATR）、Liquidity（20日平均売買代金 等）等の計算関数を提供。
    - DuckDB 上でのウィンドウ関数を利用して効率的に集計。

- ツール
  - paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 指標: 稼働率（uptime）, 注文成功率 (fill_rate), 送信率 (send_rate), P95 レイテンシ等を算出。
    - 基準閾値を定義して PASS/FAIL 判定を出力（閾値はソース内定義）。
    - --from/--to/--db オプションと環境変数 PAPER_TRADING_SQLITE_PATH に対応。DB がない場合のエラーメッセージを整備。

- ユーティリティ
  - process_priority: クロスプラットフォームでのプロセス優先度と CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/Mac 等の差分を吸収。psutil を利用して nice 値 / priority class を設定。
    - set_cpu_affinity によりプロセスを先頭 N コアに固定可能。アクセス権限不足時は警告を出してスキップ。

### Changed

- 設計方針の明示
  - ポートフォリオ構築・ポジションサイズ・レジーム制御等の関数は「純粋関数（副作用なし）」として設計し、DBアクセスを行わない方針を明確化。
  - DuckDB を分析用に利用し、prices_daily / raw_financials テーブルに依存することで本番 API へのアクセスを避ける方針を採用。

### Fixed

- 設定読み込みの堅牢化
  - .env パーサを強化し、export キーワード、シングル/ダブルクォート、エスケープ、インラインコメントの扱いを改善（src/kabusys/config.py）。
  - MONITOR_POLL_INTERVAL の不正値に対してフォールバックして警告を出す実装を追加（src/kabusys/run_monitoring.py）。

### Notes / その他

- 監視と実行は stop フラグファイル（data/stop_requested.flag）や PID ファイル経由で外部制御可能。運用時は stop フラグ・kill フラグの取り扱いに注意してください（validate_config にて本番用ガードチェックあり）。
- 一部の機能は環境依存（psutil が必要、PyYAML が無い場合は YAML 検証がスキップされる等）ため、実運用では必要ライブラリのインストールを推奨します。
- 将来の拡張メモ:
  - position_sizing の lot_size を銘柄別に持たせる拡張（stocks マスタの導入）が想定されている箇所があります（TODO コメントあり）。
  - apply_sector_cap の評価で price が欠損した場合の評価不足に関するフォールバック改善案（前日終値等）がコメントで残されています。

---

作成者: 自動生成（コードベースから推測）  
注: 本 CHANGELOG は与えられたソースコードから推測して記載しています。実際のコミット履歴に基づくものではありません。