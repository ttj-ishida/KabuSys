# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

すべてのリリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-28

### Added
- 初期リリースとしてパッケージ全体を追加。
- パッケージメタ情報
  - kabusys.__version__ = "0.1.0" を追加。
  - パブリックサブモジュールの __all__ を定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env / .env.local からの自動読み込み機能を実装。
    - プロジェクトルートは .git や pyproject.toml を基準に自動検出（カレントワーキングディレクトリ非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - 読み込み時に既存 OS 環境変数を保護するための保護セットを実装。
  - .env 行のパース機能を実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
  - Settings クラスを提供し、必要な設定値をプロパティ経由で取得可能：
    - J-Quants / kabuAPI / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等
  - 必須環境変数未設定時に明示的なエラーを返す _require() を実装。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとにニューステキストを結合し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメント（ai_score）を算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）を実装。
    - バッチ処理（最大 20 銘柄 / リクエスト）、記事数上限 (_MAX_ARTICLES_PER_STOCK)、文字数トリム (_MAX_CHARS_PER_STOCK) を実装。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）を実装。
    - レスポンスの堅牢なバリデーションとスコアクリッピング（±1.0）を実装。
    - 成果を ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。DuckDB 0.10 の executemany 空リスト制約を考慮。
    - API 呼び出し点はテスト用にパッチ可能（_call_openai_api をパッチ可能に設計）。
    - API キー未設定時は ValueError を送出。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily / raw_news を参照し、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - マクロキーワードによる raw_news のフィルタリング、LLM 呼び出し、JSON パース、スコアのクリップ、しきい値判定を実装。
    - LLM 呼び出しは独立実装（news_nlp とプライベート関数を共有しない）でモジュール結合を低減。
    - API エラー時は安全装置として macro_sentiment = 0.0 にフォールバックし処理を継続。
    - API 呼び出しのリトライ/バックオフ、ロギングを実装。
    - API キー未設定時は ValueError を送出。

- Research（kabusys.research）
  - factor_research モジュール
    - モメンタム、ボラティリティ、バリュー等のファクター計算関数を追加:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA 乖離）
      - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio
      - calc_value: per / roe（raw_financials と prices_daily を結合）
    - DuckDB + SQL ウィンドウ関数を利用した実装。
    - データ不足時の None ハンドリング、ログ出力を実装。
  - feature_exploration モジュール
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得するクエリを実装。
    - calc_ic: スピアマンランク相関（IC）を実装。データ不足（有効レコード < 3）時は None を返す。
    - rank: 同順位は平均ランクとするランク変換（丸めによる ties 対策を実装）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算する集計ユーティリティ。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- Data（kabusys.data）
  - calendar_management
    - JPX カレンダー管理・夜間バッチ更新（calendar_update_job）を実装。
      - J-Quants クライアント経由で差分取得し market_calendar に冪等保存（保存件数を返す）。
      - バックフィル、健全性チェック（未来日異常検出）を実装。
    - 営業日判定ユーティリティを実装:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - 市場カレンダー未取得時の曜日ベースのフォールバックを提供。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループを防止。
  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl で再エクスポート）。
    - ETLResult は取得件数・保存件数・品質問題・エラーリスト等を保持し、to_dict() により品質問題をシリアライズ可能。
    - ETL パイプライン内部ユーティリティ（テーブル存在チェック、最大日付取得、market calendar 調整ロジック等）を実装。
    - ETL の設計方針として差分更新、バックフィル、品質チェックの収集（Fail-Fast ではなく呼び出し元で判断）を採用。

- その他
  - DuckDB を想定した実装上の互換性配慮（日付型変換ユーティリティ、executemany の空リスト回避など）。
  - ロギング（logger）を各モジュールに導入し、情報・警告・例外ログを適切に出力。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の取り扱いに関する注意書き:
  - 必須キー未設定時に明示的に例外を送出することで安全性を高める（例: OPENAI_API_KEY, SLACK_BOT_TOKEN 等）。
  - 自動 .env 読み込みは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）で、テスト・CI 環境へ配慮。

### Notes / Design decisions
- ルックアヘッドバイアス回避:
  - AI スコアリング・レジーム判定・ETL 等の主要関数は datetime.today()/date.today() を内部で参照せず、外部から target_date を受け取る設計になっている。
- フェイルセーフ:
  - OpenAI 等の外部 API が失敗した場合、処理を中断せず中立スコア（0.0）やスキップによって継続する方針を採用。
- テストしやすさ:
  - OpenAI 呼び出しは内部 _call_openai_api をパッチ可能にしており、ユニットテストでモックを注入しやすい設計。
- DB 書き込みの冪等性:
  - market_regime / ai_scores 等は冪等的に置換する（DELETE → INSERT）構成で部分失敗時に既存データを保護。

---

今後のリリースでは、以下のような改善を予定しています（例）:
- strategy / execution モジュールの具体的な注文ロジックとテストカバレッジの追加
- J-Quants / kabu API クライアントの堅牢化と統合テスト
- モデルやプロンプトのチューニング、パフォーマンスの最適化

フィードバックやバグ報告は issue を通じてお願いします。