# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

最新リリース
-------------

### [0.1.0] - 2026-04-20
初回リリース — KabuSys の基本機能を実装しました。以下はコードベースから推測した主要な追加・設計ノートです。

Added
- コアランタイム/起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV による paper_trading モード対応（MockBrokerClient を利用し paper_trading 用 DB へ記録）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルによる安全停止対応。
- 環境設定 / 設定管理
  - config.py: Settings クラスを実装。.env の自動読み込み（.env, .env.local の順。OS 環境変数を保護）・KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化・複数の設定プロパティ（DB パス、紙取引用パス、しきい値、ログ設定等）を提供。
  - config_setup.py: 対話式ウィザード（.env 作成/更新）を追加。シークレット値はマスク表示して保存する。
  - validate_config.py: 起動前の設定検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パス・config/*.yaml の存在チェック、--strict モードをサポート。
- DB / 永続化
  - DuckDB と SQLite を併用するアーキテクチャを採用（duckdb_path / sqlite_path / paper_trading 用 sqlite の分離）。
  - 監視テーブルの初期化ユーティリティ init_monitoring_db を各プロセス起動時に呼び出して存在を保証（冪等）。
- ポートフォリオ構築モジュール（純関数）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 発注株数計算ロジックを実装（risk_based, equal, score）。単元株（lot_size）単位で丸め、aggregate cap（利用可能現金）超過時のスケーリング・端数処理を実装。cost_buffer による保守的コスト見積り対応。
- ユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを実装。stdout（StreamHandler）と日次ローテートファイル（TimedRotatingFileHandler、30日保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL からの解決、ファイル出力失敗時のフォールバックを考慮。
  - utils/process_priority.py: psutil ベースでプロセス優先度（high/normal/low）および CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収してフォールバックを実装し、権限エラーは警告でスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成 CLI を追加。稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計して PASS/FAIL を判定するしきい値を実装。P95 の算出、期間フィルタ、DB 存在チェックを提供。
- リサーチ（骨組み）
  - research/factor_research.py: ファクター計算モジュールのスケルトン実装（モメンタム、MA200、ATR、出来高等）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。将来的な因子群計算の基盤を準備。

Changed
- （新規リリースのためなし。実装に伴う設計方針や命名規約をコード内に明記）

Fixed
- .env パーサーの改良（config._parse_env_line）
  - export KEY=val 形式のサポート、クォート付き値のバックスラッシュエスケープ対応、コメント扱いの改善（クォートあり/なしの挙動を厳密化）。
- Logging 設定の堅牢化
  - 既存ハンドラをクリアしてから再設定することで二重登録を防止。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
- 起動時の安全性向上
  - 起動直後にプロセス優先度を上げる処理を追加（set_process_priority("high") を各起動スクリプトで最初に呼び出す）。
  - 停止フラグ（data/stop_requested.flag）や実行中 PID ファイルによる安全停止・二重起動抑止の処理を追加。

Security
- .env の取り扱いについて注意喚起を追加（config_setup が .env を生成する際に "絶対に Git にコミットしないこと" を明示）。
- シークレット入力はウィザードでマスク表示。

Notes / Known issues / TODOs
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に欠損（0.0）がある場合、エクスポージャーが過小見積りされる可能性あり。将来的に前日終値等のフォールバック実装を検討中（TODO コメント）。
- position_sizing:
  - 単元株数 lot_size は現状グローバル定数。将来的に銘柄ごとの lot_size を受け取る設計への拡張を検討中。
- research/factor_research は実装の途中（ファイル末尾が未完）や細かな最適化余地が残る可能性あり。
- monitoring は環境に関わらず「監視用 SQLite（settings.sqlite_path）」を使用する設計になっているため、意図的に監視データを本番 DB に残す場合は注意が必要。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップする（警告）。CI 等では PyYAML をインストールしておくことを推奨。

開発者向けメモ
- 自動 .env ロードはプロジェクトルート検出（.git または pyproject.toml）に依存するので、パッケージ配布後やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。
- LOG_LEVEL/LOG_DIR/各種パスは環境変数で上書き可能。ログはデフォルトで logs/<app>.log に日次ローテーションで出力され、30 日分保持する設定。
- paper_trading モードでは paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番データとの完全分離を目指している。

今後の検討事項（優先度順、推奨）
1. factor_research の完全実装とユニットテスト追加
2. 銘柄ごとの lot_size 対応（stocks マスターの導入）
3. 価格欠損時のフォールバックロジック実装（前日終値等）
4. run_monitoring/run_execution の統合的な supervisord/systemd ユニット例のドキュメント化
5. テスト用モックや CI ワークフローの整備（validate_config を CI に組み込む）

— End of changelog —