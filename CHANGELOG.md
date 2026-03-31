# Changelog

すべての重要な変更は Keep a Changelog の仕様に従って記載しています。  
このプロジェクトの初期リリースとして、バージョン 0.1.0 を公開します。

全般的な方針
- ルックアヘッドバイアスを避けるため、日付参照に datetime.today()/date.today() を極力用いず、関数呼び出し側から target_date を受け取る設計にしています。
- DuckDB をデータレイヤーに利用し、各モジュールは基本的に DuckDB 接続を受け取って SQL と Python を組み合わせて処理します。
- OpenAI（gpt-4o-mini）を利用する NLP 部分は JSON Mode 出力を期待し、レスポンスの堅牢なバリデーションとリトライ（指数バックオフ）を実装しています。
- DB 書き込みは可能な限り冪等（idempotent）に設計されています（DELETE→INSERT、ON CONFLICT など）。

## [0.1.0] - 2026-03-31

Added
- パッケージ基盤
  - 初期パッケージ `kabusys` を追加。バージョンは 0.1.0。
  - パッケージ公開 API を `__all__` で定義（data, strategy, execution, monitoring）。

- 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーはコメント、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントなどの実用的なケースに対応。
  - 読み込み時の上書き制御（override）と OS 環境変数保護（protected set）に対応。
  - Settings クラスを提供し、主要な環境変数をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト付き）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（Path 型で展開）
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）、LOG_LEVEL（DEBUG 等のバリデーション）
    - ヘルパー: is_live, is_paper, is_dev

- AI（自然言語処理）機能 (kabusys.ai)
  - ニュースセンチメント (news_nlp)
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI に送信しセンチメントを算出。
    - タイムウィンドウ（JST 前日15:00 ～ 当日08:30、内部は UTC naive に変換）を明確化する calc_news_window を提供。
    - gpt-4o-mini を用いた JSON Mode を利用し、1チャンクで最大 20 銘柄（_BATCH_SIZE）を処理。
    - 1銘柄あたりのトリム制御（最大記事数 _MAX_ARTICLES_PER_STOCK, 最大文字数 _MAX_CHARS_PER_STOCK）。
    - リトライ戦略を実装（429、ネットワーク断、タイムアウト、5xx に対して指数バックオフ）。
    - レスポンスバリデーション（JSON 抽出、results リスト、code の正規化、数値チェック、±1.0 クリップ）。
    - 成果物は ai_scores テーブルへ「部分更新（対象コードのみ DELETE → INSERT）」することで部分失敗時の既存データ保護を実現。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。

  - 市場レジーム判定 (regime_detector)
    - ETF 1321（日経225 連動型）の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の market_regime を生成。
    - MA200 の乖離は _MA_WINDOW=200 を用いて計算。データ不足時は中立（1.0）にフォールバックし警告ログを出力。
    - マクロニュースは raw_news からマクロキーワード（日本・米国・グローバルのキーワード群）で抽出し、最大 _MAX_MACRO_ARTICLES 件を LLM へ送信。
    - LLM 呼び出しは gpt-4o-mini、JSON Mode を利用。API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 最終的な regime_score をクリップしてラベル（bull/neutral/bear）を付け、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API 呼び出しの再試行や 5xx の扱いなど、堅牢なエラーハンドリングを実装。

- データプラットフォーム（kabusys.data）
  - カレンダー管理 (calendar_management)
    - market_calendar を基に営業日判定 utilities を追加（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベース（平日を営業日）でフォールバック。
    - next/prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）を設けることで無限ループ防止。
    - calendar_update_job を実装し、J-Quants API（jquants_client 経由）から差分取得・バックフィル（直近 _BACKFILL_DAYS）・保存（save_market_calendar）を行う。健全性チェックも実装。

  - ETL / パイプライン (pipeline, etl)
    - ETLResult データクラスを追加。ETL 実行結果の集約（取得数、保存数、品質チェック結果、エラー一覧）を表現。
    - pipeline モジュールの ETLResult を再エクスポートする etl.py を追加。
    - 差分更新、バックフィル、品質チェック方針を文書化（コードに反映）。

- 研究用モジュール（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数を追加:
      - calc_momentum, calc_volatility, calc_value
    - SQL ウィンドウ関数を活用し、欠損やデータ不足時の扱い（None 返却）を明確化。
    - ATR 計算で true_range の NULL 伝播を厳密に扱い、カウント判定で不正な評価を防止。

  - feature_exploration
    - 将来リターン計算: calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算: calc_ic（Spearman の ρ をランクで計算、3 件未満で None）。
    - rank ユーティリティ（同順位は平均ランク、丸め処理で ties を安定化）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - すべて標準ライブラリ + DuckDB のみで実装、外部依存を避ける方針。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Notes / Implementation details
- OpenAI クライアント呼び出し部はユニットテストで差し替えやすいように _call_openai_api を各モジュールごとに実装（モジュール間でプライベート関数を共有しない設計）。
- DuckDB の executemany に関する互換性（空リスト渡し不可）に配慮して、INSERT/DELETE の実行前にパラメータ非空チェックを行っている。
- JSON レスポンスの取り扱いでは、JSON Mode でも前後に余計なテキストが混ざるケースを想定して最外の {} を抽出するフォールバック処理を実装。
- ログ出力を充実させ、リトライやフォールバック発生時に原因を追跡しやすくしています。

今後の予定（例）
- strategy / execution / monitoring モジュールの具体的実装（本リリースでは API を公開しているが詳細は未実装）。
- テストカバレッジの拡充（特に OpenAI 呼び出し・DB 書き込みのエッジケース）。
- パフォーマンス改善（大規模データセットでの DuckDB クエリ最適化、並列化検討）。

--- 

（注）この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴やプロジェクト管理情報とは異なる場合があります。