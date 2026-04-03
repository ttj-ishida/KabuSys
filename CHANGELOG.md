Keep a Changelog
=================

すべての変更履歴はこのファイルに記載します。  
本プロジェクトは「Keep a Changelog」準拠のフォーマットで管理しています。

フォーマット
----------
- バージョンは [リンク] スタイル（将来的なリリースページへリンク可能）で管理します。
- セクションは Added / Changed / Fixed / Deprecated / Removed / Security を使用します。

[0.1.0] - 2026-04-03
--------------------

Added
- 初回公開: KabuSys 日本株自動売買システム のコア機能群を追加。
  - パッケージメタ情報
    - kabusys.__version__ = "0.1.0"
    - __all__ に主要サブパッケージを公開（data, research, ai 等）。
  - 環境設定管理 (kabusys.config)
    - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
      - 自動ロード順序: OS環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
      - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD非依存）。
    - .env パーサ実装:
      - export KEY=val 形式に対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
      - クォート外のインラインコメント判定（直前に空白/タブがある場合のみ）。
    - 環境変数取得ユーティリティ（必須チェック _require）と Settings クラスを提供。
      - J-Quants / kabuステーション / LINE / データベースパス / 監視設定 / システム設定等のプロパティを定義。
      - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の値検証を実施。
      - デフォルト値を適切に指定（例: KABU_API_BASE_URL, DUCKDB_PATH, PID_FILE_PATH 等）。
  - AI（Natural Language）機能 (kabusys.ai)
    - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
      - raw_news + news_symbols を集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode で一括スコアリング。
      - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事上限・文字トリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
      - 再試行戦略（429/ネットワーク/タイムアウト/5xx を対象に指数バックオフ）を実装。
      - レスポンス検証（JSONパース回復ロジック、results 配列・code/score 検証、スコアの ±1.0 クリップ）。
      - 部分失敗に備え、ai_scores テーブルへの書き込みは取得済みコードのみ置換（DELETE→INSERT）して他コードを保護。
      - テスト容易性を考慮し、OpenAI 呼び出し部分を差し替え可能（ユニットテスト向けの patch 想定）。
    - 市場レジーム判定 (kabusys.ai.regime_detector)
      - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定・保存。
      - マクロニュースはタイトルをフィルタ（日本・米国等のマクロキーワードリスト）して最大 20 件まで LLM に渡す。
      - OpenAI 呼び出しに対する堅牢なリトライ（同様に指数バックオフ）とエラーフェイルセーフ（失敗時 macro_sentiment=0.0）。
      - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。失敗時はROLLBACKを試行して上位へ例外伝播。
      - lookahead バイアス防止設計（date.today()/datetime.today() を直接参照しない、prices_daily クエリに date < target_date を使用）。
  - Research（因子・特徴量解析） (kabusys.research)
    - ファクター計算 (factor_research)
      - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER, ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高比率）を実装。
      - DuckDB の SQL ウィンドウ関数活用による効率的な計算。データ不足時は None を返す。
    - 特徴量探索 (feature_exploration)
      - 将来リターン calc_forward_returns（任意ホライズン、入力検証あり）。
      - IC（Information Coefficient）計算 calc_ic（Spearman のランク相関を実装、最小有効レコード数をチェック）。
      - ランク化ユーティリティ rank（同順位は平均ランク、丸め処理で ties の誤検出を防止）。
      - 統計サマリー factor_summary（count/mean/std/min/max/median）。
    - zscore_normalize は data.stats から再エクスポート。
    - すべての研究機能はローカル DB（prices_daily / raw_financials 等）のみ参照し、外部発注等にはアクセスしない設計。
  - Data（データ基盤） (kabusys.data)
    - マーケットカレンダー管理 (calendar_management)
      - market_calendar テーブルを基に is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - DB データがない場合は曜日（土日）ベースのフォールバックを使用して一貫性を保つ。
      - カレンダー夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
      - 最大探索日数やバックフィル日数等の安全策を実装（_MAX_SEARCH_DAYS/_BACKFILL_DAYS/_SANITY_MAX_FUTURE_DAYS）。
    - ETL パイプライン (pipeline / etl)
      - ETLResult データクラスを公開（取得数/保存数/品質問題/エラーの集約）。
      - 差分フェッチ・保存（jquants_client の save_* 関数で idempotent に保存）・品質チェックのフローを想定。
      - デフォルトのバックフィルやカレンダー先読みなど運用を考慮した設計。
    - DuckDB 互換性や実装上のワークアラウンド（executemany の空リスト回避など）を取り入れた実装。
  - 監視・運用関連
    - デフォルトの PID ファイル / KILL フラグパスや CPU/メモリ/ディスク閾値を Settings で定義。
    - KILL_FLAG_CLEAR_ON_START 等の運用フラグを追加。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 設計方針（ドキュメント的補足）
- ルックアヘッドバイアス防止: すべてのバッチ関数は target_date を明示的に受け取り、内部で現在時刻を参照しない方針を徹底。
- フェイルセーフ: 外部 API（OpenAI/J-Quants）が失敗しても致命的失敗とせず、部分結果やデフォルト値で継続する設計（ログ出力で検知可能）。
- テスト容易性: OpenAI 呼び出しポイントを patch できるように設計し、テストでネットワーク呼び出しを差し替えやすくしている。
- DuckDB の互換性: executemany の空リストバインド等、実運用で遭遇した DuckDB 特有の制約に配慮した実装を行っている。

Acknowledgements
- 初期実装: コードベースの各モジュール（data, research, ai, config, monitoring 等）。
- 使用想定外部サービス: OpenAI（gpt-4o-mini）、J-Quants（市場データ API）、kabuステーション API。

未解決 / 将来の改善候補
- PBR・配当利回り等のバリューファクター追加（現状は PER/ROE のみ）。
- ai_scores / market_regime などの更新戦略のより詳細なトランザクション最適化。
- OpenAI 呼び出しのメトリクス収集・レート制御の強化。
- calendar_update_job の J-Quants API 呼び出し失敗時のリトライポリシー強化。

[0.1.0]: https://example.com/release/0.1.0