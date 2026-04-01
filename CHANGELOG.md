# Changelog

すべての注目すべき変更は Keep a Changelog の慣習に従って記録しています。  
このファイルはコードベースの内容から推測して作成しています（実装済み機能・設計意図の要約）。

全般的な注意
- バックエンドは DuckDB を想定した実装です。
- LLM（OpenAI）呼び出しは gpt-4o-mini を想定した JSON モードを利用しています。
- 日時参照におけるルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない設計方針が採られています（対象日を明示的に渡す）。
- OpenAI 呼び出し箇所はテスト容易性のためモック差し替え可能な内部関数を用意しています。
- DB 書き込みは冪等性（DELETE→INSERT / ON CONFLICT 等）およびトランザクション（BEGIN/COMMIT/ROLLBACK）を重視しています。

Unreleased
- (なし)

[0.1.0] - 2026-04-01
Added
- パッケージの初期バージョンを定義
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 起点）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env ファイルのパース実装（コメント、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ対応）。
  - 自動ロード時の既存 OS 環境変数保護（protected set）。
  - 必須環境変数取得時は _require() で未設定時に ValueError を送出。
  - 各種設定プロパティを提供（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境判定 / ログレベル等）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値以外は ValueError）。

- AI 関連: ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
  - raw_news + news_symbols を集約し、銘柄ごとのニュースを LLM に渡してセンチメント（ai_score）を算出。
  - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST（UTC変換済み）を採用（calc_news_window）。
  - バッチ処理: 最大 20 銘柄/リクエスト（_BATCH_SIZE）。
  - 1銘柄あたりの記事数上限・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトークン肥大化対策。
  - API 呼び出しは JSON Mode を想定、レスポンスの厳密な検証を行い不正レスポンスはスキップ。
  - 429／ネットワーク断／タイムアウト／5xx を対象に指数バックオフによるリトライ（上限 _MAX_RETRIES）。
  - スコアは ±1.0 にクリップ。取得成功銘柄のみ ai_scores テーブルを置換（部分失敗時に既存スコアを保護するためコードを絞って DELETE→INSERT）。
  - テスト用に _call_openai_api をパッチ可能に設計。
  - APIキーが未設定の場合は ValueError を送出。

- AI 関連: 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定。
  - MA 計算は target_date 未満のデータのみを利用してルックアヘッドを排除。
  - マクロニュースの抽出はマクロキーワードリストに基づいたタイトル検索、最大 _MAX_MACRO_ARTICLES 件を対象。
  - OpenAI 呼び出しは独立した内部実装でモジュール結合を避ける設計。
  - API エラー時は macro_sentiment=0.0（中立）にフォールバックして処理継続。
  - 最終的なスコアを market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）し、失敗時は ROLLBACK。

- データ基盤ユーティリティ (src/kabusys/data/*)
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar を用いた営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - calendar_update_job 実装：J-Quants API からの差分取得・バックフィル（_BACKFILL_DAYS）・健全性チェック（_SANITY_MAX_FUTURE_DAYS）を実行し保存。
  - ETL パイプライン (pipeline.py / etl.py)
    - ETLResult dataclass を導入（ETL 実行結果・品質問題・エラーの集約）。
    - 差分取得・保存・品質チェックを想定した設計（jquants_client 経由の保存、quality モジュールと連携）。
    - _get_max_date / _table_exists のユーティリティ。
    - etl.py で ETLResult を公開再エクスポート。

- Research / ファクター分析 (src/kabusys/research/*)
  - ファクター計算 (factor_research.py)
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（データ不足時は None を返す）。
    - ボラティリティ・流動性: atr_20 / atr_pct / avg_turnover / volume_ratio（必要データ不足時は None）。
    - バリュー: PER / ROE を raw_financials と prices_daily から計算（EPS が 0/欠損時は None）。
    - DuckDB のウィンドウ関数を利用した実装。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（calc_forward_returns、デフォルト horizons=[1,5,21]、引数検証あり）。
    - IC（Information Coefficient）計算（calc_ic）：Spearman ランク相関を実装。十分なデータが無い場合は None。
    - rank() ユーティリティ：同順位の平均ランク処理、丸めによる ties 対応。
    - factor_summary(): count/mean/std/min/max/median を標準ライブラリのみで計算。
  - research パッケージの公開 API を整理（__init__.py で主要関数を再エクスポート）。

Changed
- 新規リリースのため該当なし（初期実装）。

Fixed
- 新規リリースのため該当なし（初期実装）。

Security
- OpenAI API キーは引数注入可能で環境変数 OPENAI_API_KEY の使用を明示。未設定時は明確にエラーを出すことで意図しない公開を抑止。

設計上の注記（重要）
- ルックアヘッドバイアス防止: 各種関数は target_date を引数で受け取る設計。内部で現在日時を直接参照しない。
- フェイルセーフ: LLM/API エラーやパースエラーは可能な限りスコアを中立またはスキップとして継続し、全体のバッチ処理を止めない方針。
- テスト容易性: OpenAI 呼び出しを行う内部関数を明示的に分離しており、unittest.mock などで差し替え可能。
- DuckDB 互換性考慮: executemany の空リスト処理などバージョン差のワークアラウンドあり。

開発者向け
- 必須環境変数例（参考）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env ロードはプロジェクトルート検出に依存するため、パッケージ配布後に自動動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で設定を注入してください。

-- End of changelog for v0.1.0 --