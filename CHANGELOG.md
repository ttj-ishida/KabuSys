KEEP A CHANGELOG — KabuSys

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠しています。

注: 以下の履歴は提供されたコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-04-19
初回公開リリース。

### Added
- 実行 / 監視エントリポイント
  - run_execution.py：ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（data/paper_trading.db を使用）。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを起動。
    - engine はスレッドで実行し、 data/stop_requested.flag による停止制御・PID ファイル管理を実装。
    - 起動時に monitoring 用テーブルの存在を保証する init_monitoring_db を呼び出し冪等性を確保。
  - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず production の sqlite_path を使用する設計。
    - stop flag 検知、例外時のログ出力、DuckDB 接続管理などを実装。

- 設定・環境管理
  - config.py：.env 自動読み込み機能と Settings クラスを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml 起点）。
    - .env / .env.local の読み込み順序、OS 環境変数保護（protected）をサポート。
    - .env 行パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - Settings に各種プロパティを実装（DB パス、paper_trading 用パス、paper_fill_mode のバリデーション、閾値、環境判定等）。
    - settings = Settings() によりモジュールレベルでインスタンスを提供。

  - config_setup.py：対話式の .env 作成ウィザードを追加。
    - 秘匿入力マスク、選択肢サポート、既存 .env の読み込みと Enter での再利用、.env への書き出しを実装。

  - validate_config.py：起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査。
    - DUCKDB/SQLITE のパス存在チェック（親ディレクトリの存在確認と警告）。
    - config/*.yaml の存在確認と PyYAML によるパース検証（PyYAML 未インストール時はスキップ）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ツール
  - tools/paper_verification_report.py：Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出。
    - 閾値を定義して PASS/FAIL 判定を出力。
    - 日付フィルタ（--from/--to）および DB パス指定（--db / 環境変数）をサポート。

- ポートフォリオ構築関連（純関数群）
  - portfolio/portfolio_builder.py：
    - select_candidates（スコア降順・タイブレークロジック）を追加。
    - calc_equal_weights、calc_score_weights（スコアが全て 0 の場合のフォールバックロジック含む）を追加。
  - portfolio/risk_adjustment.py：
    - apply_sector_cap（セクター集中上限の適用）を実装。既存ポジションを考慮し、売却予定銘柄を除外可能。
    - calc_regime_multiplier（market regime に応じた投下資金乗数）を実装（bull/neutral/bear および未知レジームのフォールバック）。
  - portfolio/position_sizing.py：
    - calc_position_sizes を実装。allocation_method（risk_based / equal / score）をサポート。
    - 単元株（lot_size）丸め、銘柄ごとの上限、aggregate cap（全体投資金額が available_cash を超えた場合のスケールダウン）、コストバッファの考慮、残差処理ロジックを含む。

- ユーティリティ
  - utils/logging_setup.py：
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）を設定する共通ユーティリティを追加。
    - ログディレクトリ作成失敗時のフォールバック（コンソール出力のみ）を考慮。
    - レベル解決順（引数 > 環境変数 > デフォルト）やログディレクトリ解決順を実装。
  - utils/process_priority.py：
    - psutil を使ったプロセス優先度設定（Windows / POSIX の差異吸収）を追加。
    - CPU affinity 設定関数 set_cpu_affinity の実装。
    - 権限不足や未対応 OS を想定した警告処理・フォールバックを実装。

- パッケージメタ情報
  - __init__.py に __version__ = "0.1.0" を設定。

- 研究用モジュール（スケルトン）
  - research/factor_research.py：ファクター計算モジュールの骨格を追加。
    - Momentum/Value/Volatility/Liquidity の設計方針と定数を定義。DuckDB を用いた計算を想定。
    - calc_momentum のインターフェースとドキュメントを追加（実装は部分的）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （現時点で特記事項なし）

### Notes / Known issues
- research/factor_research.py の calc_momentum は途中で実装が切れているように見える（スケルトン・未実装部分あり）。今後の実装が必要。
- run_monitoring.py は「監視は環境にかかわらず本番 sqlite_path を使用する」挙動がドキュメント化されているため、意図的な設計だが運用時に混乱しないよう注意が必要。
- .env 自動読み込みはデフォルトで有効。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化できる。
- logging_setup はログディレクトリ作成失敗時にファイル出力を無効化してコンソール出力にフォールバックする設計になっている。

もし特定ファイルごとにより詳細な changelog 行を分けたい、あるいは想定日付やバージョン命名規則を変更したい場合は指示してください。