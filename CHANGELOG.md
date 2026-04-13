CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠して記載しています。  
日付はコードベースから推測可能な最新の状態（ドキュメント作成日）を使用しています。

Unreleased
----------

- Added
  - 監視ポーリングスクリプト run_monitoring.py を追加。
    - 環境変数 MONITOR_POLL_INTERVAL によってポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定する処理を組み込む（utils.process_priority）。
    - SQLite / DuckDB 接続を初期化し、SystemMonitor.check_once() を定期実行するループを実装。例外時はログ記録のうえ次回ポーリングへフォールバック。

  - 実行エンジン起動スクリプト run_execution.py を追加。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント抽象化を導入（paper/live に応じた実装切替）。
    - RiskManager, OrderManager, Reconciler といった依存コンポーネントを組み立て、ExecutionEngine.run_session() を呼び出す起動フローを提供。
    - 起動時にプロセス優先度を "high" に設定。

  - 環境設定管理モジュール kabusys.config を追加／拡充。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env / .env.local の自動読み込み（OS 環境変数を保護）。
    - export 形式やクォート、インラインコメント、エスケープ対応の .env パーサーを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプションを追加。
    - 多数のプロパティを提供（JQUANTS, KABU, DUCKDB / SQLITE パス, PAPER_TRADING_SQLITE_PATH, PID ファイル等）。
    - env / log_level のバリデーション、paper_fill_mode の有効値チェック等の入力検証を実装。

  - ポートフォリオ構築（kabusys.portfolio）モジュールを追加。
    - portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重（calc_score_weights）。
      - スコアが全て 0 の場合は等金額配分にフォールバックして Warning を出力。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
      - apply_sector_cap は売却予定銘柄をエクスポージャー計算から除外可能、"unknown" セクターは上限適用対象外。
      - calc_regime_multiplier は bull/neutral/bear に対応し、未知のレジームは 1.0 でフォールバック。
    - position_sizing: allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算を実装。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、総投下上限（max_utilization）、コストバッファ（cost_buffer）考慮の aggregate スケーリングを実装。
      - risk_based モードではリスク・損切り率（risk_pct / stop_loss_pct）を用いたポジションサイズ計算を提供。

  - 研究（research）モジュール群を追加。
    - factor_research: モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB を用いた SQL 実装）。
      - calc_momentum, calc_volatility, calc_value を実装。データ不足時は None を返す等の安全処理あり。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）・ランク変換（rank）・統計要約（factor_summary）を実装。
      - 外部ライブラリに依存せず標準ライブラリで完結する設計。
    - research パッケージは zscore_normalize を外部（kabusys.data.stats）から再エクスポート。

  - AI ニュース NLP（kabusys.ai.news_nlp）機能を追加。
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores テーブルに書き込む処理を実装。
    - バッチ処理（最大 20 銘柄／回）、トークン肥大化対策（記事数・文字数上限）、429/5xx/ネットワークエラーに対する指数バックオフリトライを実装。
    - 出力 JSON のバリデーション、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（対象コードを絞って DELETE→INSERT）等のフェイルセーフを導入。
    - OpenAI API キーの解決・未設定時の ValueError を実装。

  - ユーティリティ（kabusys.utils.process_priority）を追加／拡張。
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収するプロセス優先度設定（set_process_priority）。
    - CPU affinity 固定ユーティリティ（set_cpu_affinity）を追加。
    - 権限不足や未対応 OS 時は警告を出して安全にスキップする設計。

  - ツール: paper_verification_report を追加（kabusys.tools.paper_verification_report）。
    - Paper Trading DB（既定: data/paper_trading.db）から検証指標（稼働率、注文成功率、送信率、レイテンシ）を集計し CLI でレポート出力。
    - CLI オプション --from / --to / --db を提供、P95 計算、閾値による PASS/FAIL 判定を実装。
    - テーブル不在時や DB ファイル未発見時は適切に N/A / エラー表示。

  - パッケージ初期化とバージョン情報を追加。
    - kabusys.__init__ に __version__ = "0.1.0" を設定。
    - 各サブパッケージの __all__ によるエクスポート整理。

- Changed
  - .env の取り扱いを厳密化（クォート・エスケープ・コメント処理）。
  - DuckDB / SQLite の接続初期化処理を各起動スクリプトで共通化（init_monitoring_db の呼び出しを追加して監視テーブル存在を保証）。

- Fixed
  - position_sizing の aggregate スケーリング処理で lot_size 単位の丸めと残余キャッシュを考慮する実装に改良（不足分の配分を残差順に割当てて再現性を確保）。

- Security
  - OpenAI API キー等の機密情報は環境変数経由で取得するよう明確化し、未設定時は例外で早期検出するように変更。

0.1.0 - 2026-04-13
------------------

- Initial release — 上記 Unreleased に記載の機能群を初回公開。
  - 自動売買の実行・監視・ポートフォリオ構築・研究・ニュース NLP・ユーティリティ・検証ツールを含む包括的なコードベースを提供。
  - 主要な設計方針:
    - DuckDB / SQLite をデータ層に使用し、研究系は外部 API に依存しない。
    - Paper Trading 環境は本番 DB と明確に分離。
    - フェイルセーフ（API 失敗時のスキップ、データ不足時の None 処理等）を多くの箇所で採用。
    - .env 自動ロードと堅牢なパーサーを採用して環境設定を扱いやすく。

注記（実装から推測）
--------------------
- 上記はソースコード内の docstring・コメント・定数・関数仕様から推測してまとめた変更履歴です。  
- 小さな内部リファクタリングやログ出力文の変更、未公開のユニットテスト追加/修正などは含めていません。必要であればより詳細な差分（ファイル別の変更点）を作成します。