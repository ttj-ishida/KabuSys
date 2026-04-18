# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

最新リリース: 0.1.0 (初回公開)

注:
- 本 CHANGELOG は現在のコードベースの内容から推測して作成したもので、実際のコミット履歴やリリースノートとは差異がある可能性があります。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回公開リリース。KabuSys の基礎機能群（起動スクリプト、設定管理、監視・実行ランナー、ポートフォリオ構築、ユーティリティ、分析ツール等）を実装・提供します。

### Added
- 実行・運用関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて本番／ペーパートレードを切り替え、ペーパートレード時は専用 SQLite（data/paper_trading.db）へ記録。実行はスレッドで行い、外部停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を使用する設計。

- 設定管理・検証
  - config.py: Settings クラスによる環境変数取得・検証を実装。.env 自動ロード機能を実装（OS 環境変数 > .env.local > .env の優先順）。複数のヘルパー（PAPER_FILL_MODE のバリデーション、各種パスの Path 型解決など）を提供。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。初期ファイル生成・既存値の引き継ぎ、秘密値マスク表示などの UX を備える。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と YAML パースチェック、KABUSYS_ENV=live 時の追加ガードなどを実装。--strict モードをサポート。

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補選抜（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限の適用（売却予定銘柄の除外、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 等配分・スコア・リスクベースの株数決定ロジックを実装。単元（lot_size）丸め、per-position/max aggregate の制限、cost_buffer を考慮したスケールダウンロジック（切り捨て端数の再配分を含む）を実装。

- データ解析・研究ツール
  - research/factor_research.py: DuckDB を用いたファクター計算モジュール（モメンタム、MA200 乖離、ATR、出来高等の計算方針と一部実装）。（注: ファイル末尾に未完の箇所あり／今後拡張予定）
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、P95 レイテンシ等を集計・判定し、PASS/FAIL を出力。閾値（稼働率 99%、成功率 90% など）を定義。

- 監視用 DB 初期化
  - monitoring/monitoring_db.py（参照されているもの）経由で監視テーブルの初期化を起動スクリプトから行う（冪等に保証）。

- ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、既定 30 日保持）をルートロガーに設定。LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定（Windows の優先度クラス、POSIX の nice 値）と CPU affinity 設定を実装。権限不足時は警告してスキップ。
  - その他小ユーティリティ群（__init__、tools パッケージ初期化等）。

- パッケージ情報
  - __init__.py によりパッケージバージョンを定義（__version__ = "0.1.0"）し、主要サブパッケージを __all__ で公開。

### Changed
- 環境/DB の扱いに関する明示化
  - 監視プロセスは KABUSYS_ENV に依存せず本番用 sqlite_path を使用する仕様に明示（run_monitoring）。
  - 実行エンジンは KABUSYS_ENV=paper_trading 時に paper_sqlite_path を使用して本番 DB と完全分離（run_execution）。

- .env 自動読み込みの挙動
  - OS 環境変数を保護する仕組みを導入（.env の上書きは .env.local のみが可能、既存 OS 環境変数は protected により上書きされない）。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。

- ログ出力のデフォルト
  - ログは stdout に出力されるようにし（cron 等でのリダイレクトを想定）、ファイル出力は logs/<app_name>.log に日次ローテーションで保存する設計（ディレクトリ作成失敗時はファイル出力を無効化）。

### Fixed
- 環境変数の入力耐性向上
  - MONITOR_POLL_INTERVAL（run_monitoring）に不正な値（0以下や非整数）が設定された場合、警告を出してデフォルト（60 秒）にフォールバックするように修正。
  - .env パーサー（config._parse_env_line）を強化し、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。クォートなし値の # がコメントとして認識されるルールも明確化。

- validate_config の堅牢化
  - YAML ライブラリがない場合は YAML の検証をスキップして警告を出すように変更し、config/*.yaml の存在確認およびパース時の例外を適切に報告するようにした。
  - KABUSYS_ENV=live 時の安全チェックを追加（LINE 通知設定の存在確認、KILL_FLAG_CLEAR_ON_START の注意喚起）。

### Deprecated
- なし

### Removed
- なし

### Security
- .env ファイルに機密情報（API トークン・パスワード）が含まれるため、config_setup にて .env を Git にコミットしない旨の注意を出力するように明示。

### Known issues / Notes / TODO
- research/factor_research.py の実装は途中（ファイル末尾で未完の記述あり）。今後の完成が必要。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合のフォールバック（前日終値・取得原価など）は未実装（TODO 注記あり）。現状はその銘柄をスキップする挙動。
  - 将来的には銘柄別の lot_size をサポートする設計への拡張を予定。
- apply_sector_cap:
  - "unknown" セクターは制限対象外としている点を意図的に採用。ただし運用上の検討余地あり。
- run_monitoring/run_execution:
  - 停止フラグ（data/stop_requested.flag）や PID ファイルの扱いはファイルシステム依存であり、コンテナ運用や権限の違いで挙動が異なる可能性あり。運用ルールの明確化を推奨。
- process_priority の設定は権限（root や 管理者）が必要な場合があり、失敗時は警告のみで継続する設計。

---

（今後のリリースでは、research モジュールの完成、各種ユニットテストの追加、ドキュメント整備、さらに細かな運用改善・バグ修正を予定しています）