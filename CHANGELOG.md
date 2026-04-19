CHANGELOG
=========

このファイルは Keep a Changelog の形式に従って作成しています。  
重大な変更点はすべてここに記載します。

フォーマット:
- Unreleased: 今後の変更（まだリリースされていないもの）
- 各リリースは日付を付与

Unreleased
----------
- 研究モジュール kabusys.research.factor_research の実装が途中（ファイル末尾が途中で切れている）。追加のファクター計算ロジックとテストを予定。
- 一部の TODO（price フォールバック、銘柄毎の lot_size サポートなど）が残存。将来的な改良予定。

0.1.0 - 2026-04-19
------------------

Added
- 基本アプリケーション設定管理を追加（kabusys.config.Settings）。
  - .env / .env.local の自動読み込み（プロジェクトルートを自動検出、環境変数で自動ロード無効化可）。
  - 環境変数の詳細な検証（必須変数、KABUSYS_ENV / LOG_LEVEL の妥当性チェックなど）。
  - Paper Trading 用の分離された SQLite パス（PAPER_TRADING_SQLITE_PATH / paper_sqlite_path）。
  - PAPER_FILL_MODE のバリデーション（instant / partial / never / reject）。
- 環境設定ウィザード CLI を追加（kabusys.config_setup）。
  - 対話形式で .env ファイルを作成 / 更新する機能を提供。
- 起動前設定検証 CLI を追加（kabusys.validate_config）。
  - 必須環境変数・YAML 設定ファイル・データベースパス等のチェックを実施。
  - --strict オプションで警告をエラー扱いにできる。
- 実行・監視プロセス起動スクリプトを追加。
  - run_execution.py: ExecutionEngine 起動用。KABUSYS_ENV=paper_trading の場合は MockBrokerClient（分離 DB に記録）を想定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL で間隔上書き可能（デフォルト 60 秒）。
  - 両スクリプトでプロセス優先度を最初に "high" に設定する処理を追加。
  - stop/kill フラグ（data/stop_requested.flag 等）と PID ファイルの処理を組み込み。
- ロギングユーティリティを追加（kabusys.utils.logging_setup）。
  - stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（30 日保持）をルートロガーに設定。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
- プロセス優先度・CPU affinity ユーティリティを追加（kabusys.utils.process_priority）。
  - Windows / POSIX を抽象化して nice 値や優先度クラスを設定。
  - set_cpu_affinity により最初の N コアにピン止め可能（権限不足などは警告でスキップ）。
- Portfolio 構築関連の純粋関数群を追加（kabusys.portfolio）。
  - portfolio_builder: 候補選定（select_candidates）、配分（calc_equal_weights / calc_score_weights）。スコア合計が 0 の場合は等配分へフォールバック。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、レジーム乗数計算（calc_regime_multiplier: bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - position_sizing: 株数算出ロジック（risk_based / equal / score）、単元株丸め、aggregate cap（利用可能現金でスケールダウン）、cost_buffer を考慮した保守的見積り、端数配分ロジックを実装。
- Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）。
  - 稼働率、注文成功率、送信率、レイテンシ（P95 など）を計算して PASS/FAIL を判定する CLI。
  - デフォルト DB は data/paper_trading.db。--from / --to / --db オプションをサポート。
- DuckDB / SQLite 接続サポートを導入。
  - 監視・実行でそれぞれ sqlite3（監視／ペーパートレード専用 DB）と duckdb を利用。
  - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
- パッケージバージョン設定（kabusys.__version__ = "0.1.0"）。

Changed
- 環境ファイルパーサ（kabusys.config._parse_env_line）を堅牢化。
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、クォートなしのコメント取り扱いロジックを実装。
- .env の読み込み順序と保護ロジックを導入。
  - 優先順: OS 環境 > .env.local > .env。OS 側の既存キーは protected として上書きされない。
- ログ出力はコンソールに stdout を使うように変更（cron / scheduler でのリダイレクトとの相性向上）。
- run_monitoring の挙動:
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用（監視データは共通 DB に集約）。
  - MONITOR_POLL_INTERVAL が不正（0 以下や非数）な場合、デフォルト（60 秒）にフォールバックして警告を出力。
- process_priority で権限エラーや未対応 OS を安全に扱うよう警告にフォールバックする仕様に。

Fixed
- .env 読み込みでファイルオープンに失敗した場合に警告発生しつつ処理継続するよう改善（テスト環境対策）。
- ロギングセットアップ時、既存ハンドラを安全に flush/close してから削除するよう修正（重複ハンドラ防止）。
- calc_score_weights: 全銘柄スコアが 0 の場合に 0 で割る問題を防止し、等金額配分にフォールバックして warning を出す。
- position_sizing における aggregate scale-down ロジックで小数端数処理の再現性を確保（端数が大きい順に lot 単位で再配分する実装）。

Documentation / Comments
- 各モジュールに用途・設計方針・引数仕様・戻り値説明を詳細に追記（PortfolioConstruction.md / StrategyModel.md に基づく設計参照の旨を明記）。
- run スクリプトやツールに使用例と環境変数説明をコメントで追記。

Notes / Known issues
- research.factor_research.py が途中で切れており、モメンタム等のファクター計算ロジックが完全実装されていない。リリース後に続きの実装・テストを予定。
- position_sizing の price フォールバック（前日終値や取得原価を使う等）は TODO。価格欠損時にエクスポージャーやサイズが過小見積もられる可能性あり。
- 単元株数の取り扱いは現状グローバルな lot_size パラメータのみ。将来は銘柄別 lot_map に拡張予定。

Security
- 機密情報（J-Quants トークン、KABU API パスワード等）は .env に保存する前提。.env を Git にコミットしないよう README / .env テンプレートで注意喚起。

Acknowledgements
- 初期リリースとして実用に必要な主要機能（設定管理、起動ランチャ、ログ、プロセス制御、ポートフォリオ構築ロジック、検証ツール）を実装。今後はテスト追加、factor 計算の完成、実稼働向けの細かいチューニングを進めます。

-----