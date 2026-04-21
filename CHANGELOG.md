CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- （なし）

0.1.0 - 2026-04-21
------------------

Added
- 基本パッケージ初期実装を追加。
  - kabusys パッケージ v0.1.0 を追加（__version__ = "0.1.0"）。
- 実行/監視用エントリポイントを追加。
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルによる安全停止に対応。
- 環境設定・検証用 CLI を追加。
  - config_setup.py: 対話式ウィザードで .env を作成/更新するツールを実装（シークレット入力、選択肢、既存値の再利用など）。
  - validate_config.py: .env および config/*.yaml の事前検証ツールを実装。--strict オプションで警告を FAIL 扱いにできる。
- 設定管理を実装（kabusys.config）。
  - .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml 基準）。.env と .env.local の読み込み順・上書きルール（OS 環境変数保護）を実装。
  - 環境変数のパース改善（export 接頭辞、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いなど）。
  - Settings クラスを追加。各種設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、paper_trading 用設定、しきい値など）を提供し、バリデーションを行う。
- ポートフォリオ構築ライブラリを追加（kabusys.portfolio）。
  - portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - position_sizing: 発注株数決定ロジック（risk_based / equal / score）と aggregate cap、lot 単位丸め、cost_buffer を考慮したスケーリングを実装。
- 監視・検証ツールを追加。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などの指標を集計して PASS/FAIL を判定する。閾値はソース内定義で調整可能。
- ログ・プロセス管理ユーティリティを追加（kabusys.utils）。
  - logging_setup.py: ルートロガー設定ユーティリティ。stdout への StreamHandler と日次ローテーションファイルハンドラ（TimedRotatingFileHandler）を設定。LOG_DIR / LOG_LEVEL に対応。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - process_priority.py: Windows / POSIX の差分を吸収するプロセス優先度設定関数（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。アクセス権限や未対応 OS を考慮したフォールバック処理を持つ。
- データ処理・リサーチ基盤の下地を追加。
  - research/factor_research.py（モメンタム等のファクター計算の骨組みを追加。DuckDB を想定した価格テーブル参照設計。）
- DB 初期化サポート（監視用テーブルの冪等初期化）。
  - monitoring.monitoring_db.init_monitoring_db を使用して sqlite 接続時に監視テーブルを保証する呼び出しを追加（run_execution, run_monitoring）。

Changed
- 設定自動読み込みの挙動を明確化。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化可能。
  - プロジェクトルートが特定できない場合は自動ロードをスキップ。
  - .env.local は .env を上書きする（ただし OS 環境変数は保護）。
- 実行/監視プロセスの優先度をデフォルトで "high" に設定するように変更（起動直後に set_process_priority("high") を呼び出す）。
- run_monitoring の挙動:
  - Monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（本番監視 DB）を使用する旨を明確化。
  - check_once() 実行中の例外はループを止めずログを出力して次のポーリングに継続するようハンドル。
  - MONITOR_POLL_INTERVAL が不正な場合は警告を出しデフォルト値にフォールバック。
- run_execution の DB 選択:
  - settings.is_paper 判定により paper_trading 用の専用 SQLite を使用（settings.paper_sqlite_path）。これによりペーパートレードと本番の DB を完全に分離。
- logging_setup の堅牢化:
  - ログディレクトリ作成に失敗した場合、例外で終了させずコンソール出力のみで継続するフォールバックを実装。
  - 既存ハンドラが設定されている場合は一度 flush/close してから再設定することで二重登録を防止。
- Settings の各種バリデーションを追加/強化:
  - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。
  - KABUSYS_ENV / LOG_LEVEL の許容値チェック。
  - 各種しきい値（CPU/MEM/DISK）を環境変数から float で取得するプロパティを追加。
- position_sizing のスケーリングロジック強化:
  - cost_buffer による保守的コスト見積もりを導入。
  - aggregate cap により総投資額が available_cash を超える場合は比率スケーリングし、その後 lot_size 単位で再配分するアルゴリズムを実装。
- apply_sector_cap の挙動:
  - "unknown" セクターはセクター上限の対象外（除外しない）とし、既存保有の売却予定コードはエクスポージャー計算から除外。
- validate_config の検証強化:
  - 必須環境変数の存在チェックとプレースホルダ値検出（末尾 _here / your_value の警告）。
  - config/*.yaml の存在確認と、PyYAML が利用可能な場合はパース検証を行う。PyYAML 未インストール時は警告を出してスキップ。
  - KABUSYS_ENV=live 時に追加の安全ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）を実施。

Fixed
- 環境変数パーサの不具合対策を実装。
  - クォート内のバックスラッシュエスケープを正しく処理するよう改良し、インラインコメントの誤解釈を回避。
  - export KEY=val 形式のサポートを追加。
- run_execution のエンジン起動時に停止フラグが立っている場合は起動をスキップする安全処理を追加。
- process_priority, set_cpu_affinity で例外（アクセス権限不足や未実装 API）発生時に警告ログを出して処理を継続するように修正。

Notes / Implementation details
- 停止制御
  - 全体で "data/stop_requested.flag" や "data/execution.pid"、"data/kill.flag" 等のファイルベースの停止/管理フラグを用いる設計になっている。実行環境でこれらのファイルの配置/クリアによりプロセス制御を行う想定。
- DuckDB / SQLite
  - 実行コンポーネントは DuckDB（分析用）と SQLite（監視 / 発注ログ）を併用する設計。ファイルパスは Settings で指定可能。
- Paper Trading 分離
  - paper_trading 環境では MockBrokerClient と専用 SQLite（デフォルト data/paper_trading.db）を用いて、本番データと完全に分離して検証できるよう配慮。

Security
- .env の取り扱いに関する注意書きを config_setup の出力に明記（.env を Git に絶対にコミットしない旨）。
- シークレット扱いの環境変数は対話式ウィザードでマスクして表示。

Deprecated
- （なし）

Removed
- （なし）

以上。今後のリリースではリファクタ、単体テストの追加、ファクター計算やストラテジーモジュールの完成、運用監視周りのアラート連携（LINE 通知等）を予定しています。