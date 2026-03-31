CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠します。  
安定化・設計方針として「ルックアヘッドバイアスを避ける」「外部への副作用を最小化する」「DB 書き込みは冪等に」「API 呼び出しはフェイルセーフに」という方針が採られています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-31
--------------------

Added
- 基本パッケージ初期リリース。
  - パッケージメタ情報: kabusys v0.1.0
- 環境設定管理:
  - kabusys.config.Settings を導入。J-Quants / kabuステーション / Slack / データベースパス / 実行環境・ログレベル等の環境変数を型付きプロパティで取得。
  - .env/self environment ファイル自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env 行パーサを実装（export プレフィックス対応、クォート内のエスケープ、インラインコメント判定をサポート）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
- AI（自然言語処理）:
  - kabusys.ai.news_nlp.score_news を実装。
    - ニュース記事を銘柄毎に集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、記事数/文字数トリム、429/ネットワーク/タイムアウト/5xx のエクスポネンシャルバックオフリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列・コード照合・数値検証、スコアクリップ）を実装。
    - 部分失敗に備え、書き込みは対象コードのみを DELETE → INSERT で置換することで既存データを保護。
  - kabusys.ai.regime_detector.score_regime を実装。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロ記事フィルタ（キーワード群）、OpenAI 呼び出し、リトライ・フェイルセーフ（API失敗時は macro_sentiment=0.0）を実装。
  - OpenAI 呼び出しはテスト容易性のため内部関数化（テストで差し替え可能）。
- Research（リサーチ）:
  - kabusys.research モジュール群を実装し再公開。
    - factor_research: calc_momentum, calc_value, calc_volatility（prices_daily / raw_financials を参照）。
      - モメンタム（1M/3M/6M）、MA200乖離、ATR、平均売買代金、出来高比などを SQL/duckdb で計算。
    - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
      - 将来リターン計算（horizons 引数あり）、Spearman 相関（IC）計算、統計サマリー等を標準ライブラリのみで実装。
    - zscore_normalize を kabusys.data.stats 経由で利用可能に。
- Data（データ基盤）:
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar が未取得・部分的な場合は曜日ベース（平日）でフォールバック。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェックを実装。
  - ETL パイプライン:
    - kabusys.data.pipeline を実装。差分取得、保存、品質チェック（quality モジュール連携）の設計を提供。
    - ETLResult データクラスを提供（kabusys.data.etl 経由で再エクスポート）。
  - DuckDB への互換性配慮（executemany に空リストを渡さない等）。
- モジュール初期化とエクスポート:
  - kabusys.__init__ で主要サブパッケージを __all__ に登録。
  - ai/research パッケージで公開 API を明確化（__all__）。

Changed
- 設計上の重要方針を明確化（コード内ドキュメント）:
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を推定計算に直接参照しない実装（target_date を明示的に渡す設計）。
  - DB 書き込みは冪等化（主に DELETE → INSERT、BEGIN/COMMIT/ROLLBACK を利用）。
  - 外部 API 呼び出しはフェイルセーフ化（失敗時に処理を継続、主要処理への例外伝播を最小化）。
- OpenAI API 周り:
  - JSON Mode の応答パースで余分な前後テキストが混ざるケースに備え、最外の {} を抽出して復元するフォールバックを導入。

Fixed
- エラー耐性と互換性向上:
  - OpenAI 呼び出しでの 5xx / レート制限 / ネットワークエラー / タイムアウトに対するリトライとログ出力を実装。全リトライ消費時はデフォルト値にフォールバックして続行。
  - API レスポンスパース失敗時に例外を上位に伝播させず、warning ログを残してスコア 0.0（またはスキップ）とすることでバッチ全体の中断を防止。
  - DuckDB 用の executemany 空リスト問題に対応するガードを追加（空の場合は実行しない）。
  - DB 書き込み失敗時は ROLLBACK を試行し、ROLLBACK 自体の失敗は警告ログで報告。
- 環境変数パースの堅牢化:
  - export プレフィックス、クォート内エスケープ、インラインコメント判定などを正しく扱うように改善。

Security
- 特になし（環境変数ベースの機密情報は Settings から参照する設計。OpenAI API キーは引数で注入可能）。

Notes / Usage
- 必須環境変数例:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- OpenAI API キーは関数引数として注入可能（api_key）または環境変数 OPENAI_API_KEY を使用。
- 自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

Breaking Changes
- なし（初期リリース）。

Acknowledgments
- 本リリースでは DuckDB と OpenAI（gpt-4o-mini）を外部依存として利用しています。