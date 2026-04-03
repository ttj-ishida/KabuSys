CHANGELOG
=========

すべての注目すべき変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- なし

0.1.0 - 2026-04-03
------------------

Added
- 初回リリース: KabuSys — 日本株自動売買／データ研究用ライブラリを公開。
  - パッケージメタ:
    - バージョン: 0.1.0
    - パッケージエクスポート: data, strategy, execution, monitoring（src/kabusys/__init__.py）
- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理などを考慮した .env パーサ実装。
  - OS 環境変数を保護する protected 機構（.env.local は override=True だが protected に含まれるキーは上書きしない）。
  - 必須環境変数未設定時は明示的な ValueError を送出する _require。
  - 各種設定プロパティを提供（J-Quants, kabu API, LINE, DB パス, 監視設定, CPU/MEM/DISK閾値, env/log_level 判定など）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
- データ層（src/kabusys/data/*）
  - ETL パイプラインの公開型 ETLResult（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETL 実行結果の構造化（フェッチ/保存件数、品質問題リスト、エラー等）、辞書化ユーティリティを提供。
  - calendar_management（JPX カレンダー管理）
    - market_calendar に基づく営業日判定ロジック（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB 未取得日は曜日（週末）ベースのフォールバック。
    - calendar_update_job: J-Quants から差分取得して冪等的に保存（バックフィル・健全性チェック付き）。
  - pipeline / ETL 設計
    - 差分取得、保存（idempotent）、品質チェックの統合方針を実装（jquants_client / quality と連携する想定）。
- 研究用モジュール（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離などを計算（prices_daily のみ参照）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。
    - DuckDB 経由で SQL とウィンドウ関数を活用する実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン取得（複数ホライズン対応、入力検証あり）。
    - calc_ic: スピアマンのランク相関（IC）計算（結合・None除外・最小サンプル数チェック）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）算出。
    - rank: 同順位の平均ランク処理（丸め対策あり）。
  - research パッケージ公開を整備（主要関数を __all__ で再エクスポート）。
- AI 関連（src/kabusys/ai/*）
  - news_nlp.score_news:
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）に基づき raw_news と news_symbols を集計し、銘柄ごとに記事を結合。
    - OpenAI（gpt-4o-mini）へ最大20銘柄/チャンクでバッチ送信。JSON Mode を想定したレスポンス検証。
    - 429・ネットワーク切断・タイムアウト・5xx に対する指数バックオフによるリトライ実装。
    - レスポンスの厳密なバリデーション（results 配列・code の存在・数値スコア・既知コードのみ採用）と ±1.0 クリップ。
    - 部分失敗に備え、ai_scores への書き込みは該当コードのみ DELETE→INSERT で上書き（他コードを保護）。
    - テスト容易性: _call_openai_api のパッチ差替えを想定。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事はマクロキーワードでフィルタ（キーワード一覧実装）。
    - OpenAI 呼び出しは独立実装（news_nlp と共有しない）で、API の失敗時は macro_sentiment=0.0 を採用するフェイルセーフ設計。
    - レジームを market_regime テーブルに対して冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - LLM 呼び出しのリトライ/エラー処理、JSON パース例外ハンドリングを含む。
- 実装上の安全設計・テスト配慮
  - ルックアヘッドバイアス回避: datetime.today()/date.today() を内部ロジックで参照せず、関数に target_date を渡す設計。
  - OpenAI API キーは引数注入を許容（テスト時に環境変数依存を排除可能）。
  - API 呼び出し失敗時のフェイルセーフ動作（空リスト／0.0 フォールバック、警告ログ）。
  - DuckDB を主要ストレージとして使用。各種 SQL クエリは DuckDB の互換性を考慮して実装。
  - デフォルト DB パス（duckdb/sqlite）や PID・フラグファイルパス等のデフォルト値を提供。

Fixed
- .env パース改善:
  - export プレフィックスの許容、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォート有無での違い）を適切に処理することで .env 読み込みの堅牢性を向上。
- OpenAI レスポンス処理の堅牢化:
  - JSON パースに失敗する場合に文字列から最外の {} を抽出して復元を試みる挙動を追加（JSON mode の副次的テキスト混入に対応）。
  - APIError の status_code の有無に対する安全対応（getattr 使用）を追加。

Security
- 環境変数の上書き保護:
  - OS 環境変数は protected として .env による上書きを防止（テストや誤設定による機密情報の上書きを回避）。

Changed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Notes
- Breaking changes: なし（初回リリースのため互換性問題は無し）
- 今後の作業候補:
  - strategy / execution / monitoring パッケージ内の公開 API 実装・ドキュメント追加
  - unit/integration テストの追加（OpenAI モック・DuckDB テストフィクスチャ）
  - ドキュメント（StrategyModel.md, DataPlatform.md など）の参照リンクと使用例の追加

Contributing
- バグ報告・機能提案はリポジトリの Issue を利用してください。