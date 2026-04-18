KEEP A CHANGELOG
すべての安定版リリースについて変更履歴を記録します。
このファイルは "Keep a Changelog" のフォーマットに準拠します。
安定版はセマンティックバージョニング (MAJOR.MINOR.PATCH) を使用します。

[Unreleased]
- なし

[0.1.0] - 2026-04-18
Added
- 初期公開リリース。
- 起動/運用用スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、MockBroker を利用して本番 DB と完全分離して動作する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
- 環境設定・検証用 CLI を追加
  - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新するツール。シークレット項目はマスク表示し、保存前に確認を行う。
  - validate_config.py: .env および config/*.yaml の検証ツール。--strict オプションで警告も失敗扱いにできる。
- 設定管理
  - config.py: Settings クラスによる環境変数ラッパを実装。プロジェクトルート検出により .env/.env.local の自動読み込みをサポート（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。.env のパースは export 形式、クォート、インラインコメント等に対応。
- ポートフォリオ構築（pure functions）
  - portfolio.portfolio_builder: シグナル選定 (select_candidates)、等配分 / スコア加重重み算出 (calc_equal_weights, calc_score_weights) を実装。スコア全てが 0 の場合は等配分にフォールバック。
  - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap と、市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。unknown セクターは上限適用の対象外となる挙動を採用。
  - portfolio.position_sizing: risk_based / equal / score ベースの株数決定を実装。単元株（lot_size）丸め、1銘柄上限・総投下上限、コストバッファ考慮によるスケーリングロジックを備える。
- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup: stdout ストリームハンドラと日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに統一的に設定するユーティリティ。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみで継続。
  - utils.process_priority: Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定関数を追加。権限不足や未対応環境では警告を出して安全にフォールバックする。
- 運用ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite データベースから稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL 判定を行うレポートジェネレータを追加。P95 計算、期間フィルタ、しきい値による判定基準を実装。
- 研究モジュール（下地）
  - research.factor_research: ファクター計算モジュールの骨組み（モメンタム等の定義、calc_momentum の実装開始）を追加。DuckDB 接続を受け取り prices_daily/raw_financials を参照して計算する設計。

Changed
- DB パス・分離ポリシーの明示化
  - run_execution は paper_trading 環境時に paper_sqlite_path を優先して使用し、本番監視 DB とは分離して動作するよう設計。
  - run_monitoring は監視用に常に sqlite_path（本番想定）を使用する旨を明記。
- .env 自動読み込みの挙動
  - プロジェクトルートを .git または pyproject.toml から検出して自動ロードするようにした。OS 環境変数は保護され、.env.local が .env を上書きできるロード順を採用。
- ログ設定の挙動
  - 既存ハンドラは再設定時に flush/close してから削除し、二重設定を回避するように変更。
  - デフォルトログディレクトリやファイル名の仕様を定義（logs/<app_name>.log、日次ローテーション、30日保持）。
- 設定検証の改善
  - validate_config で YAML パーサ未インストール時は YAML 内容検証をスキップし警告を出す。KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START）を実施。

Fixed
- 起動時の頑健性とフォールバック
  - MONITOR_POLL_INTERVAL が不正（整数変換不能や 0 以下）の場合は警告ログを出してデフォルト 60 秒にフォールバックする処理を追加。
  - init_monitoring_db の呼び出しは冪等に行い、テーブル未存在時も安全に初期化できるようにしている（両エンジンで呼び出し）。
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時にサービスを停止させずコンソール出力へフォールバックする動作を実装。
  - process_priority / set_cpu_affinity は権限不足や未対応 OS で例外を握り潰し、警告を出してスキップする安全策を実装。

Security
- .env 取り扱いに関する注意
  - config_setup により生成される .env の先頭に「.env を絶対に Git にコミットしないこと」と明示するテンプレートを追加。
  - 対話ウィザードではシークレット項目をマスクして表示するようにした。

Deprecated
- なし

Removed
- なし

Notes / 今後の作業予定（コードから推測）
- research.factor_research の各ファクター（Value/Volatility/Liquidity）の完全実装と単体テスト追加。
- position_sizing の lot_size を銘柄別に対応する拡張（マスタから取得）や委託コスト見積もりの改善。
- .env 構文の追加エッジケース対応（複雑なエスケープ、マルチライン値等）。
- validate_config の YAML パース結果に対するより詳細な構成検査（必須キーの存在チェックなど）。

---

過去のコミットメッセージ等があれば、より正確で詳細な CHANGELOG を作成できます。必要ならコミット履歴や追加ファイル（monitoring や execution 内の詳細実装）を提供してください。