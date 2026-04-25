# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
※ 日付・項目はリポジトリ内のコードから推測して記載しています。

全般
- セマンティクス: バージョンはパッケージメタデータに従い `0.1.0` が初期公開バージョンとして扱われます（src/kabusys/__init__.py）。

Unreleased
- 現在未リリースの変更はありません。

[0.1.0] - 2026-04-25
Added
- 実行スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）を検知して安全に終了する実装。監視データベースは環境に依らず本番の sqlite_path を使用して初期化する。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。`KABUSYS_ENV=paper_trading` の場合は専用のペーパートレード用 DB（data/paper_trading.db）を使用し、本番 DB と完全分離する。バックグラウンドスレッドでエンジンを実行し、停止フラグで安全に停止可能。起動時にプロセス優先度を「high」に設定する。

- 設定管理
  - config.py: 環境変数/ .env の自動ロード機能を提供。プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込む（テスト等で無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート）。Settings クラスを通じた各種設定取得と妥当性チェック（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）を提供。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。シークレット項目のマスク表示、デフォルト・選択肢サポート、保存確認を備える。
  - validate_config.py: 起動前に環境変数や config/*.yaml の存在・基本的妥当性をチェックする CLI を追加。`--strict` オプションで警告を FAIL 扱いにできる。PyYAML が未インストールでも警告を出してスキップする。

- ロギング・運用ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定する共通ユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加。Windows と POSIX（Linux/Mac/FreeBSD）を考慮し、CPU affinity 設定もサポート（set_cpu_affinity）。権限不足や未対応環境では警告を出してスキップする。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を追加。スコア全てが 0 の場合に等配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限を行う apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加。未知レジームはフォールバックで 1.0 を返す。
  - portfolio/position_sizing.py: 単元株（lot_size）丸め、risk_based / equal / score の割当方式、per-stock 上限・aggregate cap、cost_buffer を考慮したスケーリング・端数配分ロジックを実装。価格欠損や 0 の扱いに対するログ出力も備える。将来的な拡張（銘柄別 lot_size）について TODO コメントあり。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から期間集計を行い、稼働率・注文成功率・送信率・レイテンシ（P95含む）等を算出するレポート生成スクリプトを追加。閾値による PASS/FAIL 判定、DB が存在しない場合の丁寧なエラーメッセージや、SQL 実行エラー時のフォールバックを実装。

- 研究用ファクターモジュール（途中実装）
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity に基づくファクター計算の設計と一部実装（定数定義、calc_momentum のインターフェース開始）を追加。DuckDB 接続を受け取って prices_daily / raw_financials を参照する想定で設計。

Changed
- ログ出力の標準化
  - すべての起動スクリプトで utils.logging_setup.setup_logging を呼び出す設計にして、ログ管理を統一。ログディレクトリの解決順（引数 > 環境変数 LOG_DIR > デフォルト logs/）とレベル解決順（引数 > LOG_LEVEL > INFO）を明文化。

Fixed
- 環境ファイルパーサの堅牢化
  - config._parse_env_line: クォート文字を含む値のバックスラッシュエスケープや、インラインコメントの取り扱い（クォートあり／なし両対応）を考慮するよう改善。export KEY=val 形式のサポートを明示。

- 起動時の堅牢化
  - DB やログディレクトリ作成に失敗した際に、致命的でなくフォールバックして動作を継続するエラーハンドリングを各所で導入（例: logging_setup, paper_verification_report の SQL 実行例外キャッチ、run_monitoring/run_execution の finally で確実にコネクションを閉じる等）。

Security
- 直接的なセキュリティ修正は無し。ただし設定ウィザード/ログ等でシークレット項目をマスクする運用配慮を実装。

Deprecated
- なし

Removed
- なし

Notes / Known issues / TODO
- portfolio/position_sizing.py:
  - 将来的に銘柄別の単元株（lot_size）を採用するための拡張 TODO が残されている。
  - price が欠損（0.0）の場合、現状はスキップしているが、前日終値や取得原価でのフォールバックが必要になる可能性がある（コメントあり）。
- research/factor_research.py:
  - ファイルの末尾で未完の行（start_da... のような途中）や実装途中の関数が見られるため、このモジュールは部分実装の状態。実運用前にテストと追加実装が必要。
- Settings の自動 .env ロードは便利だが、CI/テストで環境依存を避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できる点に注意。

問い合わせ・貢献
- この CHANGELOG はソースコードの現状から推測して作成しています。詳細な履歴や過去の変更差分は実際の git 履歴を参照してください。