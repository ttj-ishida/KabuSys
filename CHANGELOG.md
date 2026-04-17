# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。項目はコードベースから推測して記載しています。

全般的な注記
- 今回のログはソースコードの内容から推測して作成しています。実際の変更履歴やコミットメッセージがある場合はそれに合わせて更新してください。

Unreleased
- 進行中 / 要確認
  - kabusys.ai.news_nlp モジュールの実装が途中（score_news の記事取得部分や内部ヘルパーの一部が未完了の痕跡あり）。OpenAI API 呼び出し周りは設計済み（バッチ、リトライ、JSON 検証、スコアのクリップ等）だが、記事集約取得や処理の一部が未完了のため運用前に追加実装・テストが必要。
  - 一部ファイル内に TODO コメントあり（position_sizing の lot_size 拡張、risk_adjustment の価格フォールバック等）。将来的な機能拡張・堅牢化対象。

[0.1.0] - 2026-04-17
Added
- 実行/監視用エントリポイントスクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するランナー。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV に応じて paper_trading 用 DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てる。
    - デーモンスレッドで engine.run_session を実行し、data/stop_requested.flag により安全に停止可能。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するランナー。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知による終了、KeyboardInterrupt のハンドリング、例外発生時もループを継続するフェイルセーフ設計。

- 設定管理 / 環境変数ローダを追加・強化
  - config.py
    - プロジェクトルートを .git または pyproject.toml で探索し、自動で .env / .env.local を読み込む（OS 環境変数を優先、.env.local は上書き）。
    - .env パースを厳密化（コメント、クォート、export 形式、エスケープ対応）。
    - Settings クラスを提供し各種設定値（API トークン、DB パス、閾値、環境モード判定、paper_trading 用設定など）をプロパティで取得。入力検証（列挙値チェックや数値変換）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。

- ポートフォリオ構築関連の純粋関数群を追加
  - portfolio/portfolio_builder.py
    - シグナル選別（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" をサポート、未知レジームはフォールバックで 1.0）。
    - 既存ポジションや売却予定銘柄を考慮したセクター露出計算。unknown セクターは上限適用外。
  - portfolio/position_sizing.py
    - allocation_method ("risk_based", "equal", "score") に応じた株数決定ロジック。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン処理と端数処理（残余キャッシュで lot 単位配分）。
    - コストバッファ（手数料・スリッページ）を考慮した保守的見積り。

- リサーチ / ファクター計算モジュールを追加
  - research/factor_research.py
    - モメンタム（1M/3M/6M リターン、MA200乖離）、ボラティリティ（ATR20、相対ATR、平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB を使って計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None ハンドリング、ウィンドウ幅やスキャン範囲を安全に設定。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（情報係数）の計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク関数（rank）を実装。
    - 外部依存ライブラリに頼らず標準ライブラリと DuckDB で完結する設計。

- AI ニュース NLP スコアリング（骨子を実装）
  - ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI に投げ、銘柄別スコアを ai_scores テーブルに書き込む設計。
    - バッチ（最大 20 銘柄 / 呼び出し）、トークン肥大化対策（記事数・文字数の上限）、OpenAI のエラーに対する指数バックオフリトライ、結果の厳密な JSON バリデーション、スコア ±1.0 クリップなどの設計方針を実装。
    - ニュースの時間ウィンドウ（JST 基準 → UTC に変換）を calc_news_window で明示的に算出（ルックアヘッドバイアス回避の配慮）。
    - 注意: 実装は途中（記事取得関数等が未完）。

- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading データベースを読み取り、稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計して検証レポートを標準出力に出力する CLI スクリプトを実装。
    - デフォルト DB は data/paper_trading.db。--from / --to / --db オプションをサポート。
    - Pass/Fail 基準を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定(set_process_priority)を Windows と POSIX(Linux, macOS, FreeBSD) に対応して実装（psutil を使用）。
    - CPU affinity 固定(set_cpu_affinity)機能を追加。
    - アクセス権限や未対応プラットフォーム時は警告ログでスキップする安全設計。

- パッケージ情報
  - kabusys/__init__.py に __version__ = "0.1.0" を追加。

Changed
- 設計上のフェイルセーフ、ログ出力を強化
  - 実行・監視スクリプト、AI モジュール、position_sizing などで入力チェックや例外ハンドリングを明確化。例外時はログを残して継続する設計の箇所が複数追加。

Fixed
- なし（コードからは新規実装・設計の追加が中心と推測）。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY 参照または明示的に引数で渡す設計（秘匿の扱いに関する注意書きあり）。実運用ではキー管理・権限制御を厳格に行うことを推奨。

Known issues / Notes
- ai/news_nlp.py の記事取得部分・一部処理が未完（score_news の末尾が途中で切れている）。本番運用前に実装完了と入念な API エラー／レートリミットテストが必要。
- position_sizing の lot_size に関する拡張（銘柄ごとの単元サイズマスタ導入）は TODO。現状は全銘柄共通の単元を前提。
- risk_adjustment.apply_sector_cap は price_map に欠損（0.0）がある場合に露出を過少見積もる可能性があると注記あり（将来的にフォールバック価格を検討）。
- process_priority や set_cpu_affinity は実行権限・プラットフォーム制約で失敗することがある（警告ログでスキップされる設計）。

補足
- 本 CHANGELOG はソースコードの解析に基づく推測です。実際のコミット履歴・リリースノートがある場合は、そちらを正本としてください。必要であれば、実際の Git コミットログからより正確な CHANGELOG へ変換するお手伝いをします。