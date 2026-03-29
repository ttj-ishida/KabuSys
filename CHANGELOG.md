# Changelog

すべての重要な変更点を Keep a Changelog の形式で記載します。日付はリリース日を示します。  
このファイルはソースコードからの推定に基づいて作成しています。

フォーマット:
- Added: 新機能
- Changed: 既存挙動の変更（互換性に注意）
- Fixed: バグ修正
- Security: セキュリティ関連の修正／注意点

------------------------------------------------------------------------

Unreleased
- （現時点で未リリースの変更はありません）

------------------------------------------------------------------------

[0.1.0] - 2026-03-29
（初回リリース）

Added
- パッケージ基盤
  - kabusys パッケージを公開。トップレベルで data / research / ai / monitoring 等のサブモジュールをエクスポートする準備を実装。
  - バージョン情報を __version__ = "0.1.0" として設定。

- 環境設定・ロード
  - .env / .env.local からの自動環境変数読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - export KEY=val 形式やクオート文字列、行コメント（インラインコメント）に対応した柔軟な .env パーサを実装。
  - OS 環境変数を保護する protected 機構を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - Settings クラスを実装し、J-Quants / kabu ステーション / Slack / DB パス /システム設定（env, log_level, is_live 等）をプロパティ経由で取得可能に。

- AI（自然言語処理）モジュール
  - news_nlp モジュールを実装（score_news）。
    - 前日15:00 JST ～ 当日08:30 JST のニュースを対象に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を ai_scores テーブルへ書き込む。
    - バッチサイズ、記事数・文字数上限、リトライ（指数バックオフ）、レスポンス検証、±1.0 へのクリップ等を実装。
    - JSON Mode を用いた厳密なレスポンス期待と、余計な前後テキスト混入に対する復元ロジックを実装。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。

  - regime_detector モジュールを実装（score_regime）。
    - ETF (1321) の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする。
    - マクロキーワードによる記事抽出、OpenAI 呼び出し（独立実装）、リトライ、フェイルセーフ（API失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアスを防ぐ設計（date 引数ベース、datetime.today() を参照しない）。

- Data（データ基盤）
  - calendar_management モジュールを実装（JPX カレンダー管理）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定・取得 API を提供。
    - market_calendar が未登録の場合は曜日ベースでフォールバック。DB 登録値を優先する一貫したロジックを実装。
    - calendar_update_job により J-Quants API から差分取得して冪等保存（バックフィルと健全性チェックを含む）。
  - pipeline ETL モジュールを実装（ETLResult データクラス等）。
    - 差分取得、保存、品質チェックのためのインターフェースを用意。
    - ETL 結果を集約する ETLResult（品質問題のシリアライズを含む）。

- Research（リサーチ）モジュール
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を用いたファクター計算（モメンタム / ATR / 流動性 / PER/ROE 等）。
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank を実装。外部依存を持たずに統計解析を実行可能。
  - zscore_normalize を data.stats から再エクスポートする仕組み（research.__init__）。

- DuckDB を用いたデータアクセスを前提に、SQL と Python の併用により効率的な集計を実装。

Changed
- 設計上のポリシー・振る舞いを明確化
  - 主要な分析 / ETL / AI 呼び出し関数は datetime.today() / date.today() を直接参照しない設計（引数で日付を受け取る）に統一し、ルックアヘッドバイアスを排除。
  - OpenAI 呼び出しの失敗は基本的に例外を投げずフォールバックする設計（可用性優先: スコアは 0.0 などで継続）。ただし DB 書き込み失敗時は例外を伝播して呼び出し元へ通知。

Fixed
- DuckDB executemany の空リスト制約への対応
  - ai_scores 書き込み時に executemany に空リストを渡してエラーになる事象に対して空チェックを追加（DuckDB 0.10 の互換性対策）。

- OpenAI レスポンスパースの堅牢化
  - news_nlp の JSON パースで前後に余計なテキストが混ざるケースを復元（最外側の {} を抽出）してスキップ率を低減。

Security
- 環境変数保護
  - .env 読み込み時に OS 環境変数を protected として上書きから保護する動作を実装。
  - 必須環境変数が未設定の場合は Settings のプロパティで ValueError を発生させ、起動時に明確なエラーを出す。

Notes / 実装上の特徴（重要な設計判断）
- IDempotent な DB 書き込み:
  - market_regime / ai_scores 等の書き込みは既存レコードを削除してから挿入することで冪等性を保証（BEGIN / DELETE / INSERT / COMMIT）。
- テスト容易性:
  - OpenAI 呼び出しの箇所は内部関数（_call_openai_api）を通すことで unittest.mock.patch により差し替え可能に設計。
- フェイルセーフ:
  - LLM 呼び出しや外部 API の一時的失敗はリトライ（429, ネットワーク, タイムアウト, 5xx 対応）して最終的にはスコアを 0.0 にフォールバックすることで全体処理を継続可能にしている。
- ログ:
  - 主要処理に対して INFO/DEBUG/WARNING/EXCEPTION レベルで詳細なログ出力を実装。

Deprecated
- なし

------------------------------------------------------------------------

今後の提案（推奨改善点）
- OpenAI クライアント抽象化: 将来の API 変更や別 LLM の導入に備え、クライアントインターフェースをさらに抽象化することでコードの保守性を向上できる。
- メトリクス収集: リトライ回数・API レイテンシ・スコア分布などを Prometheus 等で収集すると運用性が向上する。
- テストカバレッジ: DuckDB を使った統合テスト・モックを用いた単体テストの整備を推奨。

------------------------------------------------------------------------

（注）本 CHANGELOG は提供されたコードを解析して推測に基づき作成しています。実際のリリース履歴やコミットログがあればそれに基づいて更新してください。