# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
このファイルはコードベースからの実装内容を推測して作成したリリースノートです。

## [0.1.0] - 2026-04-20

### 追加 (Added)
- 基本パッケージ初期リリース（__version__ = 0.1.0）。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、DB 接続、ブローカークライアント生成、ExecutionEngine の起動／停止監視（stop flag による制御）を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
- 設定管理
  - config.py: 環境変数・設定管理クラス Settings を追加。.env 自動読み込み（.env および .env.local、OS 環境変数保護）と各種設定プロパティ（DB パス、ペーパートレード設定、監視閾値、環境種別判定など）を提供。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを提供（秘密値マスク、デフォルト・選択肢サポート、ファイル出力）。
  - validate_config.py: 設定検証 CLI を追加。必須環境変数、KABUSYS_ENV, LOG_LEVEL, DB パス、config/*.yaml の存在と YAML パース検証、live 環境向けガード等を実行。
- ポートフォリオ構築モジュール（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder: 候補選定(select_candidates)、等配分(calc_equal_weights)、スコア加重(calc_score_weights、全スコア 0 の場合は等配分にフォールバック)。
  - portfolio.risk_adjustment: セクター集中制限の適用(apply_sector_cap)、市場レジームに応じた投下資金乗数(calc_regime_multiplier)。
  - portfolio.position_sizing: 発注株数計算(calc_position_sizes)。risk_based / equal / score の割当メソッド、単元株丸め(lot_size)、max_position や aggregate cap に基づくスケーリング、cost_buffer を考慮した保守的なコスト推定、残差処理による再配分を実装。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、LOG_DIR 環境変数対応、30日保持）を設定。既存ハンドラのクリア処理を行う。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを追加（Windows / POSIX 対応、権限不足時は警告でスキップ）。
- モニタリング関連
  - monitoring 側で使用する DB 初期化処理（init_monitoring_db を各起動時に呼び出し、監視テーブル存在を保証）。
  - SystemMonitor を用いたポーリングと停止フラグ検出のフローを提供。
- ブローカーファクトリとペーパートレード
  - run_execution は KABUSYS_ENV=paper_trading 時に paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient（Factory により生成）との分離を実現。
  - PAPER_FILL_MODE 環境変数をサポート（instant/partial/never/reject）。
- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加（稼働率、注文成功率、送信率、P95 レイテンシ等を算出・閾値比較して PASS/FAIL 判定を出力）。コマンドライン引数で期間指定と DB パス指定をサポート。
- リサーチ基盤
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの基礎を追加（モメンタム、MA200 乖離、ATR, ボリューム系の計算方針。関数 calc_momentum の骨子を実装中）。
- パッケージ内エクスポート
  - kabusys.portfolio のトップレベル import を整備（主要関数を __all__ で公開）。

### 変更 (Changed)
- ログ周りの扱いを統一:
  - 起動スクリプトは setup_logging(app_name=...) を最初に呼び出し、以降のログ出力を統一している。
- 環境変数の自動ロード挙動:
  - OS 環境変数を保護（.env の上書きを制御）し、.env.local を上書きモードで読み込む優先順位を採用。

### 修正 (Fixed)
- .env パーサーの堅牢化:
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い、無効行のスキップ等を実装。
- 監視ループと実行エンジンの安全停止:
  - data/stop_requested.flag（停止フラグ）および pid ファイルを用いた起動・停止挙動を実装し、安全にシャットダウンできるようにした。

### 既知の制約・注意点 (Known issues / Notes)
- monitoring はコード内の設計により「環境にかかわらず本番 sqlite_path を使用」する実装になっている（意図的な設計だが運用時の注意が必要）。
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に欠損（0.0）がある場合、セクターエクスポージャーが過少評価される可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO を残しています。
- research/factor_research.calc_momentum はファイル末尾で途中まで実装されている（継続実装が必要）。
- ファイル出力用ログディレクトリの作成に失敗した場合、ログはコンソール出力のみで継続。エラーは警告出力される。
- process_priority や CPU affinity の設定は権限やプラットフォームに依存し、失敗時は警告でスキップされる。

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

---

今後の予定（提案）
- factor_research の残実装完了（ファクター計算の完全化）。
- モニタリング DB とペーパートレード DB の運用ドキュメント整備（監視が本番 DB を使う挙動の明文化）。
- 銘柄別の lot_size 管理対応（stocks マスタの導入）および手数料・スリッページの詳細モデル化。
- config の stricter validation オプションに対する自動テスト整備。

（本 CHANGELOG はコードベースの実装内容から推測して作成したものであり、実際のコミット履歴や意図とは差異がある可能性があります。）