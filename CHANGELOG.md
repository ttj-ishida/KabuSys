CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
タグ付けはリリースバージョン（__version__ = "0.1.0"）に合わせています。

フォーマットの説明:
- Added: 新機能
- Changed: 既存機能の変更（互換性あり）
- Fixed: バグ修正（もしあれば）
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

Unreleased
----------

- いくつかの設計上の TODO / 改良ポイントを将来対応予定として記載
  - position_sizing: 銘柄ごとの単元株 (lot_size) を stocks マスタ等から取得する拡張
  - risk_adjustment: 価格欠損時のフォールバック（前日終値・取得原価等）の導入検討
  - research.factor_research: 実装続行（ファイル末尾が途中で切れているため追加実装が必要）
  - 監視・実行エンジンのより細かな稼働テスト・例外ハンドリング改善

[0.1.0] - 2026-04-24
-------------------

Added
- 基本アーキテクチャと起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI。KABUSYS_ENV により paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。停止フラグ（data/stop_requested.flag）検知による安全停止、実行 PID ファイル出力をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知でループ停止。監視は常に本番用 sqlite_path を使用する設計。
- 設定管理・初期化用ユーティリティ
  - config.py: Settings クラスを導入。環境変数の自動読み込み（.env, .env.local をプロジェクトルートから探索）を実装。強力な .env パーサ（export 対応、クォート内のエスケープ、インラインコメント処理等）を備え、保護された OS 環境変数を上書きしない仕組みを実現。
  - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI。シークレット値のマスク表示や選択肢サポートを提供。
  - validate_config.py: 起動前チェック CLI。必須環境変数の未設定検出、KABUSYS_ENV の妥当性チェック、YAML 設定ファイルの存在とパース検証（PyYAML がインストールされている場合）、本番環境（live）向けのガード等を実施。--strict モードあり（警告を FAIL 扱い）。
- ポートフォリオ構築関連の純粋関数群（DB 参照なし）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルの選定（スコア降順、同点は signal_rank でブレーク）
    - calc_equal_weights: 等重配分
    - calc_score_weights: スコア正規化配分（スコア合計が 0 の場合は等重にフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限ロジック。既存保有のセクター別時価を算出し上限超過セクターの新規候補除外（"unknown" セクターは除外しない設計）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく資金乗数を提供（未知レジームは警告を出して 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に対応した株数計算。単元株丸め、per-position 上限、aggregate cap（利用可能現金）を考慮したスケールダウンロジック、cost_buffer（手数料・スリッページ見積）を考慮。
- ユーティリティ
  - utils.logging_setup: ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保持）を統一設定する関数を提供。ログレベル/ログディレクトリの解決順を明確化し、ファイル作成失敗時はコンソール出力にフォールバック。
  - utils.process_priority: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。CPU affinity の設定ユーティリティも実装。権限不足や未対応 OS では安全に警告してスキップ。
- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレーディング用 SQLite DB を解析して各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を算出・表示する CLI。閾値判定（PASS/FAIL）と詳細なレポート出力を実装。P95 計算、日付フィルタ (--from / --to)、DB パス指定オプション（--db）に対応。
- 監視/実行と分析向け DB 接続
  - run_* スクリプトやツール類で sqlite3 と DuckDB の接続を利用する構成を追加。monitoring 用 DB 初期化関数 init_monitoring_db の呼び出しを各所で行い、監視テーブル等の存在を保証（冪等）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- 環境変数の取り扱い強化: .env 自動ロード時に既存の OS 環境変数を保護する設計を導入（.env の上書きは .env.local + override によってのみ行われ、protected set による保護あり）。
- .env を生成する際にシークレット項目は表示をマスクして扱う UI を提供。

Notes / 実装上の既知の制限
- position_sizing.calc_position_sizes:
  - 価格が欠損（0.0）だと計算をスキップするため、価格欠損時に想定より保守的な結果になる可能性がある（TODO: 前日終値等のフォールバックを導入予定）。
  - 単元株数は現在グローバルな lot_size 引数で扱う。将来的に銘柄別単元対応を検討中。
- risk_adjustment.apply_sector_cap:
  - "unknown" セクターには上限を適用しない設計（意図的）。必要に応じて設定で扱いを変更可能。
- research.factor_research.py:
  - ファイルの末尾が途中で切れている（calc_momentum の実装が途中）。本格運用前に残りのファクター計算（Value / Volatility / Liquidity）を完成させる必要あり。
- run_monitoring の監視 DB は「環境にかかわらず本番 sqlite_path を使用」する仕様。開発環境で監視のために分離したい場合は sqlite_path を明示的に設定するか将来的に設定追加を検討。

開発者向けメモ
- ログ出力:
  - stdout を標準出力に使用する設計（cron や OS タスクでのリダイレクト運用を考慮）
  - ログディレクトリ作成に失敗した場合はファイルハンドラが無効化され、コンソールのみで動作する
- プロセス優先度設定:
  - set_process_priority("high") を run_* スクリプトの最初に呼び出しているため、権限のない環境では警告が出るが動作自体は継続される
- 設定検証:
  - validate_config は --strict を指定すると警告でも exit(1) として失敗扱いになるので CI や本番デプロイ先での事前チェックに便利

今後の改善案（優先順、推奨）
- research/factor_research の完了（Momentum の続き + Value/Volatility/Liquidity 実装）
- position_sizing の銘柄別 lot_size 対応と価格フォールバック実装
- 監視・実行のユニットテストとエンドツーエンドテストの整備（特に停止フラグ・PID 管理・例外ハンドリング）
- DuckDB / SQLite まわりの接続リソース管理の強化（タイムアウトや再接続戦略）
- ペーパートレーディングの検証スイート自動化（tools.paper_verification_report を CI に統合）

--- 

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリース履歴や日付はプロジェクトのリリースポリシーに合わせて調整してください。）