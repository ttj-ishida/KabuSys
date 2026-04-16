CHANGELOG
=========

すべての注目すべき変更はここに記載します。  
このファイルは「Keep a Changelog」準拠の形式で記載しています。  

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

0.1.0 - 2026-04-16
------------------

Added
- パッケージ初回リリース: kabusys v0.1.0 を追加。
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env パーサーを実装し、コメント、export プレフィックス、シングル/ダブルクォート、エスケープをサポート。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを導入し、各種設定（DBパス、APIトークン、監視／閾値等）をプロパティ経由で安全に取得可能に。
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）と PAPER_TRADING_SQLITE_PATH のサポートを追加。
- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を実装し、Windows / POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度を設定。
  - set_cpu_affinity(cpu_count) を実装し、カレントプロセスの CPU affinity を設定可能に。
  - 権限不足や未対応環境での安全なフォールバックとログ出力を行う。
- 監視デーモン起動スクリプト（run_monitoring.py）
  - SystemMonitor を用いるポーリングループを実装。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
  - 停止フラグ (data/stop_requested.flag) を検知してループを安全に終了。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記（運用上の意図）。
- 実行エンジン起動スクリプト（run_execution.py）
  - ExecutionEngine を起動するエントリーポイントを追加。
  - paper_trading 環境時は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト data/paper_trading.db）で完全に分離して動作。
  - リスク管理（RiskManager）や OrderManager、Reconciler、OrderRepository の組み立てコードを追加。
  - 停止フラグ検知でエンジンを停止する制御を実装。起動時に停止フラグが既に立っている場合は起動を中止。
  - エンジンの PID を data/execution.pid に書き込む想定の pid_file サポート。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: 候補選定 select_candidates、等重み calc_equal_weights、スコア加重 calc_score_weights を実装。
  - risk_adjustment: セクター上限適用 apply_sector_cap（既存保有のセクター別エクスポージャ算出、unknown セクターは適用除外）、市場レジーム乗数 calc_regime_multiplier（bull/neutral/bear -> 1.0/0.7/0.3）を実装。
  - position_sizing: 各種配分方式（risk_based / equal / score）に対応した株数決定 calc_position_sizes を実装。lot_size 単位で丸め、aggregate cap（available_cash）を超過する場合のスケーリングと端数配分ロジックを実装。cost_buffer による保守的見積りをサポート。
  - モジュール __all__ を整備して外部公開 API を明示。
- 研究・リサーチモジュール（kabusys.research）
  - factor_research: DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）を実装。prices_daily / raw_financials テーブルのみ参照。MA200、ATR20、各種ホライズンのリターン等を算出。
  - feature_exploration: 将来リターン calc_forward_returns、IC（スピアマンランク相関）calc_ic、rank ユーティリティ、factor_summary（count/mean/std/min/max/median）を実装。外部ライブラリに依存しない実装。
  - DuckDB クエリはスキャン範囲のバッファを設け、パフォーマンスに配慮した実装。
- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に OpenAI（gpt-4o-mini）でセンチメントを算出し、ai_scores テーブルへ書き込むロジックを実装（設計概要を含む）。
  - バッチサイズ、文字数制限、記事数上限、スコアのクリップ（±1.0）、再試行（429/ネットワーク/5xx に対する指数バックオフ）など堅牢化を採用。
  - タイムウィンドウ計算 util calc_news_window（JST基準の前日15:00〜当日08:30 を UTC に変換）を提供。
  - API キー未設定時に ValueError を送出する明示的挙動。
- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading の検証レポート生成スクリプトを追加。コマンドライン実行で期間指定可能（--from / --to / --db）。
  - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を計算。閾値を定義して PASS/FAIL 判定を行う。
  - P95 計算、各種 SQL クエリ、NULL / テーブル欠損時の耐性を実装。
- パッケージ初期化（__init__.py）
  - __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ に列挙。

Changed
- なし（初回リリースのため、既存の変更履歴はありません）。

Fixed
- なし（初回リリース時点での既知のバグ修正履歴はありません）。ただし、各モジュールでエラー時の安全なフォールバック（例: DB テーブル欠損時の N/A 返却、環境変数の未設定検出、psutil の権限エラー時の警告）は組み込まれています。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY で供給する必要があり、未設定時は例外を投げることで誤動作を防止します。

注意事項（運用上の重要点）
- run_monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用します。テスト・Paper 環境と監視 DB を分離したい場合は運用上の設定（環境変数）で sqlite_path を切り替えてください。
- run_execution は paper_trading 環境時に paper_trading 用 DB を使用して本番 DB と完全分離します（PAPER_TRADING_SQLITE_PATH を利用可能）。
- .env の自動ロードはプロジェクトルートの検出に依存するため、配布後や CWD が異なる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動ロードしてください。
- calc_position_sizes 等の数値ロジックは現状 lot_size を全銘柄共通としています。将来的には銘柄別 lot_size を受け取る拡張を想定。

今後の予定（例）
- ニュースNLP の実装完了（API 呼び出し部分 / DB 書き込みの完全実装）。
- Strategy/Execution 周りのユニットテスト充実。
- 銘柄別 lot_size 対応、価格フォールバック（欠損時）改善。

貢献・バグ報告
- バグ報告や改善提案は issue にてお願いします。README / CONTRIBUTING に従ってプルリクエストを送ってください。