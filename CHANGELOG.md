# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従っています。  
このファイルは、ソースコードの内容から推測できる導入機能・改善点・修正点を元に作成した推定の変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-20
初回リリース。KabuSys 自動売買フレームワークの基礎機能を実装。

### Added
- 全体
  - パッケージの初期バージョンを追加（__version__ = "0.1.0"）。
  - DuckDB/SQLite を併用するローカル分析・監視基盤を導入（duckdb_path / sqlite_path 設定）。
  - 統一的ログ設定ユーティリティを追加（kabusys.utils.logging_setup.setup_logging）。
  - プロセス優先度・CPU affinity を抽象化するユーティリティを追加（kabusys.utils.process_priority）。
  - 環境変数管理と Settings クラスを追加（kabusys.config）。.env の自動読み込み（.env → .env.local）機能を実装。
  - 環境設定ウィザード CLI を追加（kabusys.config_setup）: 対話式で .env を生成/更新できる。
  - 設定検証 CLI を追加（kabusys.validate_config）: 必須環境変数、パス、config/*.yaml の存在／パースをチェック。--strict オプションを実装。
  - 実行エンジン起動スクリプトを追加（run_execution.py）:
    - KABUSYS_ENV=paper_trading 時には Paper Trading 用の専用 SQLite を使用し、MockBroker を使った分離動作をサポート。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine 起動。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）を用いたプロセス管理。
  - 監視ポーリングループ起動スクリプトを追加（run_monitoring.py）:
    - SystemMonitor を定期実行し system_status 等を記録。MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート（デフォルト 60 秒）。
    - 監視用 DB 初期化（init_monitoring_db）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計を明示。
  - Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）:
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（P95 など）を集計して評価／判定（PASS/FAIL）を出力。
    - P95 計算ロジックと期間フィルタ（--from / --to）を実装。
  - ポートフォリオ構築モジュールを追加（kabusys.portfolio）:
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア配分（calc_score_weights）。
    - セクター集中制限（apply_sector_cap）とレジームに応じた投下資金乗数（calc_regime_multiplier）。
    - ポジションサイズ計算（calc_position_sizes）:
      - risk_based / equal / score の割当方式をサポート。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金によるスケーリング）、cost_buffer を考慮した保守的見積り。
      - スケーリング後の残差を lot 単位で再配分するアルゴリズムを実装し、再現性のため安定ソートを使用。
  - 研究/ファクター計算基盤を追加（kabusys.research.factor_research）:
    - モメンタム、移動平均乖離、ATR、出来高等のファクター設計方針を実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。
    - （注）一部関数はスニペット段階で継続実装が必要。
  - 公開 API の入力検証と設定の妥当性チェックを強化（Settings 内の各種バリデーション、PAPER_FILL_MODE の有効値チェックなど）。
  - .env パーサーを強化:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート内でのバックスラッシュエスケープに対応。
    - クォートなしの行でインラインコメントを適切に無視するルールを実装。

### Changed
- ロギング挙動の統一:
  - 全起動スクリプトから共通の setup_logging を呼び出すことでログ出力先・フォーマットを統一。
  - コンソールは stdout を使用（cron 等で stdout/stderr をまとめてリダイレクトする運用を想定）。
  - 日次ローテートと 30 日保持を標準設定に導入。

### Fixed
- 環境変数読み込みの堅牢化:
  - .env 読み込み時のファイル IO エラーで警告を出し処理を継続するよう改善。
  - 自動ロード時に OS 環境変数を保護するための protected 処理を実装。
- run_monitoring と run_execution のリソース管理改善:
  - 例外/終了時に SQLite / DuckDB のコネクションを確実に close するように変更。
  - モニターループで停止フラグ検出時に安全に終了する処理を追加。
  - MONITOR_POLL_INTERVAL が不正（0 や負数、文字列等）の場合にデフォルト値へフォールバックし、警告を出力するように変更。
- process_priority の安定化:
  - Windows / POSIX の差分を吸収する実装とし、権限不足や未対応 OS の場合は警告を出してスキップするように改善。
- logging_setup の堅牢化:
  - ログディレクトリ作成失敗時にファイルハンドラをスキップしてコンソール出力のみ継続するフォールバックを追加。
  - 既存ハンドラを flush/close してから削除することで二重登録を防止。
- portfolio モジュールの挙動改善:
  - calc_score_weights で全スコアが 0 の場合に等金額配分へフォールバックし、警告を出すように修正。
  - apply_sector_cap で sector_map に存在しない銘柄を "unknown" 扱いし、unknown セクターは上限適用対象外とする仕様を明確化。
  - calc_position_sizes で価格欠損（0/None）を検出した場合にスキップしてログ出力するように改善。

### Security
- 初版リリースにつき特に公開済みのセキュリティ修正は無し。ただし、.env を絶対に Git にコミットしない旨を config_setup の生成ヘッダに明記。

### Notes / Known limitations
- factor_research モジュールは設計段階からの実装を含むが、完全実装（全ファクターの SQL/計算ロジック）は継続作業が必要。
- 単元株（lot_size）は現状全銘柄共通の設定を想定。将来的に銘柄別単元対応へ拡張予定（TODO コメントあり）。
- position_sizing の価格フォールバック（前日終値や取得原価等）は未実装（TODO）。価格欠損時の過少見積りに注意。
- 本リリースは推測に基づき作成した CHANGELOG です。実際のコミット履歴やリリースノートと異なる可能性があります。

---

（この CHANGELOG はコードベースの内容から推測して作成しています。必要であれば実コミット履歴・タグ情報に基づく正確な差分で更新します。）