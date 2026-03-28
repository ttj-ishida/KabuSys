Keep a Changelog 準拠 — CHANGELOG.md
=================================

すべての変更履歴は「Keep a Changelog」仕様に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

v0.1.0 — 2026-03-28
-------------------

追加 (Added)
- 初回公開リリース。本パッケージは日本株のデータ処理・リサーチ・AI評価・カレンダー管理・ETL を統合する自動化基盤を提供します。
- パッケージのエントリポイントを定義
  - src/kabusys/__init__.py に __version__ = "0.1.0"、主要モジュールを __all__ で公開。

- 環境設定・自動 .env 読み込み
  - src/kabusys/config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env/.env.local の自動ロードを実装（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサーは export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理等に対応。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境・ログレベル等の取得用プロパティを実装。KABUSYS_ENV / LOG_LEVEL の値検証や is_live/is_paper/is_dev の簡易判定を提供。
    - 必須環境変数の未設定時は ValueError を送出する挙動を明確化（例: OPENAI_API_KEY は AI 関連 API 呼び出しで必要）。

- AI モジュール: ニュース NLP（センチメント）および市場レジーム判定
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄別センチメント（-1.0〜1.0）を取得。
    - バッチ処理（_BATCH_SIZE=20）、1銘柄あたり記事数・文字数の上限トリム、JSON レスポンスの堅牢なバリデーションとスコアクリッピングを実装。
    - 429/接続断/タイムアウト/5xx に対する指数バックオフリトライを実装。フェイルセーフ設計により API 失敗時はスキップして処理継続。
    - calc_news_window 関数で JST 基準のニュース集約ウィンドウを計算（テスト・ルックアヘッド回避のため date.today() を直接参照しない設計）。
    - score_news(conn, target_date, api_key=None) を公開し、ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT、部分失敗時の既存スコア保護）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能な設計。

  - src/kabusys/ai/regime_detector.py
    - ETF コード 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、news_nlp により取得したマクロセンチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - _calc_ma200_ratio によるデータ不足時の安全処理（中立=1.0）、_fetch_macro_news によるマクロキーワードフィルタ、OpenAI 呼び出し（gpt-4o-mini）とリトライ、API 失敗時は macro_sentiment=0.0 で継続。
    - score_regime(conn, target_date, api_key=None) により market_regime テーブルへ冪等書き込み（トランザクション: BEGIN/DELETE/INSERT/COMMIT。失敗時は ROLLBACK）。

- リサーチ（Research）モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム（約1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）などのファクター計算を提供。
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB での SQL とウィンドウ関数を活用し、(date, code) 単位で結果を返す。
    - データ不足や計算不能な場合は None を返す（上位でハンドリング可能）。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト horizons=[1,5,21]）。
    - 情報係数（IC）: calc_ic(factor_records, forward_records, factor_col, return_col) で Spearman（ランク相関）を計算。サンプル数が少ない場合は None を返す。
    - ランキング関数 rank、ファクター統計サマリー factor_summary を実装（外部依存なし、標準ライブラリのみ）。

  - 研究用ユーティリティの再公開
    - src/kabusys/research/__init__.py で主要関数をエクスポート（zscore_normalize は data.stats から）。

- データプラットフォーム（Data）モジュール
  - src/kabusys/data/calendar_management.py
    - market_calendar テーブルに基づく営業日判定ロジックを実装（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB にカレンダーがない場合は曜日ベース（土日非営業日）でフォールバック。
    - calendar_update_job(conn, lookahead_days=90) を提供し、J-Quants API から差分取得 → jq.save_market_calendar で冪等保存。バックフィル・健全性チェック（未来日付の異常検知）を実装。

  - src/kabusys/data/pipeline.py
    - ETL の結果を表す ETLResult dataclass を実装（品質問題・エラーの収集、to_dict による整形）。
    - 差分取得のための内部ユーティリティ（_table_exists / _get_max_date 等）を実装。
    - ETL 処理方針、バックフィル挙動、品質チェックの取り扱い（Fail-Fast ではなく収集）を実装方針として明記。

  - src/kabusys/data/etl.py
    - ETLResult を公開インターフェースとして再エクスポート。

設計上の注記 (Highlights)
- ルックアヘッドバイアス防止: AI / リサーチの主要関数は datetime.today() や date.today() を直接参照しない。target_date を明示的に渡す設計。
- DuckDB を想定した SQL 実装: ウィンドウ関数や executemany の制約（空リストの扱い）に配慮した実装。
- API 呼び出しのレジリエンス: OpenAI 呼び出し・J-Quants 呼び出しを想定し、リトライ・フォールバック・ログ出力・トランザクションによる保護を組み込んだ。
- テスト容易性: OpenAI 呼び出し等をモジュール内部関数（_call_openai_api）経由にして patch で差し替え可能にしている。

破壊的変更 (Breaking Changes)
- 初回リリースのため該当なし。

既知の制約・注意点 (Known limitations)
- OPENAI_API_KEY が未設定の場合、score_news / score_regime は ValueError を送出する（実行前に API キーを設定してください）。
- .env 自動読込はプロジェクトルートの検出に依存する（.git または pyproject.toml）。配布後や特殊配置では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して制御してください。
- DuckDB バージョン依存の挙動（埋め込みパラメータや executemany の空リスト等）に注意。

今後の予定 (Future)
- PBR / 配当利回り等、バリューファクターの拡張。
- モデルのキャリブレーションやドメイン固有プロンプト改善。
- ETL / 品質チェックのより詳細なルールセット拡充。
- テレメトリ・監視（monitoring）モジュールの実装拡張。

問い合わせ
- バグ報告や改善提案は Issue を作成してください。README やドキュメント参照でセットアップ方法（環境変数・DB 初期化等）は補足予定です。