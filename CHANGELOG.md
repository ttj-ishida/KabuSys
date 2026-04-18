# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。

全てのリリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-18

### Added
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV に応じて本番 DB / ペーパートレード用 DB を切り替え、BrokerClientFactory で適切なブローカークライアント（Mock を含む）を生成してエンジンをスレッドで実行する。停止フラグ（data/stop_requested.flag）検知時に安全に停止する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計にした。
- 設定管理
  - config.py: .env 自動ロード機構を実装（プロジェクトルート検出・.env/.env.local 読み込み）。複雑な .env のパースに対応（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなど）。Settings クラスを導入し、各種環境変数に対するプロパティを提供（J-Quants、kabu API、DB パス、Paper Trading 設定、監視閾値、ログ設定など）。
- 設定補助ツール
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI。主要項目（KABUSYS_ENV、トークン、DB パス、ログレベル、Kill Switch の設定など）を対話的に設定可能。
  - validate_config.py: 起動前設定検証用 CLI。必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在チェック、KABUSYS_ENV=live 時の追加ガード等を実装。--strict オプションで警告を FAIL 扱いにできる。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成する CLI。期間指定により稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（平均・最大・P95）などを集計し PASS/FAIL を判定する。閾値はコード内定義（稼働率>=99%、成立率>=90%、送信率>=95%、P95<=200ms）。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based、equal、score に対応）、単元株（lot_size）丸め、aggregate cap（利用可能現金に応じたスケーリング）や cost_buffer を加味した保守的見積り。
  - portfolio/__init__.py: 上記関数群をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定関数 setup_logging を提供。stdout ストリームハンドラ + 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定。LOG_DIR 設定・ディレクトリ作成失敗時のフォールバックをサポート。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティ。Windows / POSIX の差分を吸収し、set_process_priority(level)・set_cpu_affinity(n) を提供。アクセス権や未サポート環境では警告を出してスキップする。
- 研究用モジュール
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタム、移動平均乖離、ATR、出来高などを想定）。DuckDB 接続を受け prices_daily / raw_financials を参照して因子を計算する設計。モメンタム計算の基盤を実装（実装の一部は継続開発を要する旨の設計コメントあり）。
- パッケージ化
  - __init__.py にバージョン定義 __version__ = "0.1.0" を追加。

### Changed
- DB の扱い
  - 監視（run_monitoring）は KABUSYS_ENV に依存せず常に本番 sqlite_path を使用する仕様に。これにより監視データは環境ごとに混在することがないよう意図されているが、運用時の期待と異なる場合は注意が必要。
- ログ出力
  - logging_setup のデフォルトを stdout に統一し、ファイル出力は logs/<app_name>.log に日次ローテーションで保持（30 日）。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続する。

### Fixed
- .env パースの堅牢化
  - config._parse_env_line にてクォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメント処理などを正しく扱うようにしたことで、複雑な .env 値の読み込みミスを防止。
- ExecutionEngine 起動時の監視
  - run_execution.py が停止フラグを早期に検知して起動を中止するロジックを追加（既に停止フラグが立っている場合はエンジンを起動しない）。

### Security
- 秘匿情報取り扱い
  - config_setup.py の出力ではシークレット項目はマスク表示を行い、.env ファイルに関して「絶対に Git にコミットしないこと」を明記。

### Deprecated
- なし

### Removed
- なし

### Notes / Known issues
- factor_research.py は設計上のコメントと計算方針を含むが、関数の実装（特に外部依存なしでの全ファクター計算）は継続した検証・テストが必要。  
- run_monitoring が常に本番 sqlite_path を使用する点は意図的だが、開発環境でのテスト目的で分離したい場合は Settings や起動スクリプトの変更が必要となる。  
- process_priority の設定は OS 権限や環境に依存するため、実行環境で許可がない場合は警告が出力され、処理はスキップされる。

---

今後のリリースでは、以下を予定しています（例）:
- factor_research の完全実装とテスト
- ExecutionEngine / SystemMonitor 周りの単体テスト強化
- 戦略・実行コンポーネントのドキュメント化およびサンプル設定ファイルの追加

もし CHANGELOG に追加・修正してほしい点があれば指示してください。