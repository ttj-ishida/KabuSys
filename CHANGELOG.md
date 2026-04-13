KEEP A CHANGELOG
すべての重要な変更を時系列で記述します。フォーマットは "Keep a Changelog" に準拠しています。

注: 本 CHANGELOG は提供されたコードベースの内容から機能追加・実装意図を推測して作成しています。実際のコミット履歴と異なる場合があります。

Unreleased
----------
Added
- run_monitoring:
  - システム監視ポーリングループ起動スクリプトを追加。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下や非整数）の場合は警告を出してデフォルトにフォールバックする。
  - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用して起動するように実装。
  - プロセス優先度を起動時に "high" に設定する仕組みを追加。

- run_execution:
  - 実取引エンジン起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading 時は paper 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
  - ブローカークライアントの抽象化（BrokerClientFactory）を使用してテスト/実取引を切り替え可能に。
  - ExecutionEngine 起動前に依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler）を組み立てる処理を実装。
  - 起動時にプロセス優先度を "high" に設定。

- 設定管理 (kabusys.config):
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護され上書きされない。
  - .env ファイルのパースを強化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等に対応）。
  - 各種環境変数の取得プロパティを実装（DB パス、OpenAI/LINE/その他トークン、監視閾値、PID/kill フラグパス、KABUSYS_ENV/LOG_LEVEL の検証など）。
  - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）を追加。

- utils/process_priority:
  - Windows / POSIX (Linux, Darwin, FreeBSD) に対応したプロセス優先度設定ユーティリティを追加。
  - CPU affinity を最初の N コアに固定する機能を追加。
  - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップするように実装。

- portfolio:
  - 銘柄選定・配分ロジックを純粋関数群として実装。
  - select_candidates: スコア降順、同点は signal_rank でタイブレーク。
  - calc_equal_weights / calc_score_weights: 等配分およびスコア正規化配分（全スコア 0 の場合は等配分にフォールバック）。
  - apply_sector_cap: 既存保有を考慮したセクター集中制限（unknown セクターは上限適用除外）。売却予定銘柄を露出計算から除外可能。
  - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
  - calc_position_sizes: risk_based / equal / score の各配分手法を実装。単元株（lot_size）丸め、単銘柄上限、aggregate cap によるスケールダウン（残差処理で lot 単位の再配分）をサポート。コストバッファ考慮。

- research:
  - factor_research: DuckDB 接続を受けて prices_daily / raw_financials からファクター（モメンタム、ボラティリティ、バリュー）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（スピアマン順位相関）計算（calc_ic）、ファクター統計サマリ（factor_summary）などを実装。外部ライブラリに依存せず標準ライブラリのみで動作する設計。

- ai/news_nlp:
  - raw_news を OpenAI API（gpt-4o-mini を想定）でスコアリングして ai_scores に書き込む処理を実装。
  - ニュース収集ウィンドウの算出（JST ベース → UTC 変換）を実装。
  - 銘柄ごとに記事を集約してトークン肥大化を防ぐ制限（記事数・文字数）を導入。
  - バッチ送信（最大 20 銘柄 / チャンク）、バックオフ・リトライ（429/ネットワーク/5xx を対象）、レスポンスバリデーション、スコアの ±1.0 クリップ、部分置換（失敗時に他銘柄スコアを保護）などを設計。

- tools/paper_verification_report:
  - Paper Trading 用の検証レポート生成スクリプトを追加。
  - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出して PASS/FAIL 判定を出力。
  - デフォルト DB は data/paper_trading.db。--from/--to/--db コマンドラインオプションに対応。

Changed
- DB 接続の開閉を try/finally で明示的に行い、プロセス終了時に sqlite3/duckdb 接続を確実にクローズするように改善。
- run_monitoring の例外ハンドリングを強化（check_once() の例外はログを出力して次回ポーリングまで待機）。
- 設定読み込みの挙動: プロジェクトルートが特定できない場合は自動で .env を読み込まないように変更。

Fixed
- 環境変数パースの細かい不具合対応（未設定キーやコメント含む行の扱い、クォート内のエスケープ処理など）。
- process_priority / set_cpu_affinity で権限不足や未実装 API に遭遇した際にクラッシュしないように例外処理を追加。

[0.1.0] - 2026-04-13
--------------------
Added
- 初回リリース。
  - コア機能:
    - 実行エンジン起動スクリプト (run_execution)
    - 監視ポーリング起動スクリプト (run_monitoring)
    - 環境設定管理モジュール (kabusys.config)（.env 自動読み込み・バリデーション）
    - プロセス優先度 / CPU affinity ユーティリティ
  - ポートフォリオ構築:
    - 銘柄選定、重み計算、ポジションサイズ決定、セクター上限、レジーム乗数等のアルゴリズム
  - リサーチ:
    - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB ベース）
    - 将来リターン、IC、統計サマリ等の解析ユーティリティ
  - AI ニューススコアリング:
    - raw_news → OpenAI API → ai_scores へのバッチスコアリング処理（設計段階の実装）
  - ツール:
    - Paper Trading 検証レポート生成スクリプト

Changed
- パッケージメタ:
  - パッケージバージョンを __version__ = "0.1.0" に設定。

Notes / Known limitations
- news_nlp 実装は OpenAI クライアントを直接使用するため、API キーやネットワーク環境に依存します。失敗時はログ記録・部分スキップのフェイルセーフが組み込まれていますが、運用時には API 使用量とエラー挙動の確認を推奨します。
- position_sizing の価格欠損時の扱い（price が 0.0 の場合の見積り）は警告を残す実装になっており、将来的にフォールバック価格（前日終値等）を導入する余地があります。
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布後やパッケージ化された環境では期待通りに動作しない可能性があります。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを無効化してください。

配布・リリースについて
- ここに記載した変更はコードベースから推測したものであり、実際のコミット単位の履歴（作者、日付、コミットメッセージ）は含みません。細かな差分やリリースノートの精査が必要な場合は、実際のバージョン管理履歴（git log 等）を参照してください。