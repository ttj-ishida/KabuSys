CHANGELOG
=========

すべての重要な変更はここに記録します。  
このファイルは Keep a Changelog の形式に準拠します。  

[Unreleased]
------------

- （現在のリリース履歴は下記の初期リリースを参照してください）

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージルート: src/kabusys/__init__.py にバージョンと公開 API を定義。
- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数からの設定読み込み機能を実装。
  - プロジェクトルートの自動検出: .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - .env パーサ実装:
    - export プレフィックス対応、シングル/ダブルクォートおよびバックスラッシュエスケープ対応。
    - インラインコメント処理（クォート外での # を条件付きでコメントとして扱う）。
  - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数保護: OS 環境変数を保護する protected セットを使用した上書き制御。
  - Settings クラスを公開 (settings):
    - J-Quants / kabu ステーション / Slack / DB パス 等のプロパティを提供。
    - 必須キー未設定時にわかりやすい ValueError を発生。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェックと is_live/is_paper/is_dev ヘルパ）。
    - デフォルト値（例: KABUS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）を明示。

- AI 関連機能 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを算出。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたり最大記事件数・文字数制限でトークン肥大化を抑止。
    - JSON Mode レスポンスのバリデーション・復元ロジック（前後ノイズが混在する場合でも {} を抽出）。
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフ）。
    - スコアの ±1.0 クリップ、失敗時は個別にスキップして継続するフェイルセーフ設計。
    - ai_scores テーブルへの冪等的置換（DELETE → INSERT、部分失敗時に他銘柄を保護）。
    - テストしやすさを考慮し、OpenAI 呼び出し部分を差し替え可能（_call_openai_api を patch 可能）。
    - calc_news_window( target_date ) ユーティリティ（JST ベースのニュース収集ウィンドウを UTC naive datetime で返却）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロニュース LLM センチメント (重み 30%) を合成。
    - マクロキーワードによる raw_news のフィルタリング、LLM（gpt-4o-mini）で macro_sentiment を取得。
    - レジーム合成ロジック: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)
      - 閾値により 'bull' / 'neutral' / 'bear' を判定。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とエラーハンドリング（ROLLBACK 保護）。
    - API エラー時は macro_sentiment=0.0 とするフェイルセーフ。
    - OpenAI 呼び出しは独立実装でモジュール結合を避ける設計（テスト容易性を確保）。

- データ基盤（DuckDB）ユーティリティ (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを参照する営業日判定ユーティリティ:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 未取得時は曜日ベース（土日除外）でフォールバックする堅牢な設計。
    - 最大探索範囲（_MAX_SEARCH_DAYS）で無限ループを防止。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等に更新（バックフィルと健全性チェックを実装）。
  - ETL / パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得、バックフィル、品質チェック（quality モジュール）を想定した ETL 設計。
    - テーブル存在チェック、最大日付取得ユーティリティを実装。
    - ETL 実行結果の辞書化ユーティリティ（品質問題を簡潔に出力）を提供。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）、
      流動性指標を DuckDB の prices_daily / raw_financials から計算する関数を提供: calc_momentum, calc_volatility, calc_value。
    - データ不足時の None 処理やログを整備。
  - feature_exploration:
    - 将来リターン計算 (calc_forward_returns)（任意ホライズン対応、引数検証あり）。
    - IC（Information Coefficient）計算（スピアマン ρ、ランクの tie 処理を平均ランクで実装）。
    - 統計サマリー関数 (factor_summary) および rank ユーティリティ。
  - 研究用ユーティリティを kabusys.research.__init__ でまとめて公開。

- 共通実装上の設計方針・堅牢性強化
  - ルックアヘッドバイアス防止: 全てのアルゴリズムで datetime.today()/date.today() を直接参照しない設計（target_date ベース）。
  - DuckDB に対する冪等書き込み（DELETE→INSERT／ON CONFLICT を想定）とトランザクション管理（BEGIN/COMMIT/ROLLBACK）。
  - OpenAI API 呼び出しのリトライ／バックオフ戦略を明示（Retry 回数、base 秒等を定数化）。
  - テスト容易性のため外部 API 呼び出し箇所を差し替え可能に設計（内部 _call_openai_api の patch を想定）。
  - ロギングを各モジュールに配置し、失敗時は例外を上位に伝播させつつログで詳細を記録。

Security
- 環境変数の自動ロードで OS 環境変数を保護する仕組みを導入（.env 上書き時に protected set を考慮）。
- 必須のシークレット（OpenAI, Slack, Kabu API など）は明示的に required として ValueError を発生させ、安全な運用を促進。

Changed
- 初版なので該当なし。

Fixed
- 初版なので該当なし。

Removed
- 初版なので該当なし。

Deprecated
- 初版なので該当なし。

Notes / 注意事項
- OpenAI のモデルは現時点で gpt-4o-mini を指定しているが、将来のモデル変更が可能。
- DuckDB 0.10 の executemany 空リスト制約を回避するため、空ケースをハンドリングしている箇所がある（互換性維持）。
- 外部 API（J-Quants, OpenAI）呼び出しは例外発生時にフェイルセーフで継続する実装が多いため、呼び出し元での監視・アラートが推奨される。

Authors
- 初期実装チーム（コードベースのコメント/実装から推定）

----

（補足）本 CHANGELOG は提示されたコードベースの内容から機能と設計意図を推測して作成しています。必要であれば、リリース日や細かい項目を実際のコミットログ・リリースノートに合わせて調整してください。