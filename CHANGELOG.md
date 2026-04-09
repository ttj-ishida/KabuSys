Keep a Changelog
===============

すべての公開変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

0.1.0 - 2026-04-09
------------------

Added
- 初期リリース。
- パッケージ基本情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
  - __all__ に主要サブパッケージを公開（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env / 環境変数の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は .env を上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサの実装: export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い等をサポート。
  - Settings オブジェクトを提供（settings）:
    - 必須値取得時に未設定なら ValueError を送出する _require() を利用（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - 多数の設定プロパティを公開（KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, DB パス（DUCKDB/SQLite）、Paper Trading 関連、監視閾値、PID/KILL フラグファイルパス等）。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL による入力バリデーションと明確なエラーメッセージ。

- ポートフォリオ構築 (src/kabusys/portfolio)
  - portfolio_builder.py
    - select_candidates(): buy シグナルをスコア降順・タイブレークは signal_rank でソートして上位 N を選択。
    - calc_equal_weights(): 等金額配分を返す。
    - calc_score_weights(): スコア加重配分。全スコアが 0 の場合は等金額配分へフォールバックして WARNING を出力。
  - risk_adjustment.py
    - apply_sector_cap(): セクター集中制限を適用して候補をフィルタ。既存保有のセクター時価を計算し上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier(): market regime（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは警告を出して 1.0 でフォールバック。
  - position_sizing.py
    - calc_position_sizes(): allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。単元（lot_size）丸め、1 銘柄上限・aggregate cap、cost_buffer（スリッページ・手数料）を考慮したスケーリング、残差分の lot 単位での再配分ロジックを実装。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research.py
    - calc_momentum(): 1M/3M/6M リターンと 200 日移動平均乖離（ma200_dev）を計算。DuckDB の prices_daily を参照。
    - calc_volatility(): 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を算出。
    - calc_value(): raw_financials から最新財務を取得して PER・ROE を計算（prices_daily と結合）。
    - すべて DuckDB 接続を受け、外部 API に依存しない設計。
  - feature_exploration.py
    - calc_forward_returns(): 指定ホライズン先の将来リターンを一回のクエリで取得（LEAD を使用）。入力検証（ホライズンは 1〜252 の正整数）。
    - calc_ic(): Spearman ランク相関（IC）を計算。有効レコード 3 件未満では None を返す。
    - rank(): 同順位は平均ランクにするランク変換（浮動小数の丸めを行い ties の検出精度を確保）。
    - factor_summary(): count/mean/std/min/max/median を標準ライブラリのみで計算。

- AI 関連 (src/kabusys/ai)
  - news_nlp.py
    - calc_news_window(): target_date に対するニュース収集ウィンドウ（JST→UTC 変換）を返す。
    - score_news(): raw_news を銘柄別に集約し OpenAI（gpt-4o-mini）でセンチメント評価を行い ai_scores テーブルへ書き込む。主な特徴:
      - 1 銘柄あたり記事数と文字数をトリム（上限定義あり）。
      - 最大 _BATCH_SIZE（20）銘柄ずつバッチ送信。
      - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
      - レスポンスの厳密なバリデーション（JSON 抽出、results リスト、型チェック、既知コードのみ採用、スコアの有限性チェック）。
      - スコアは ±1.0 にクリップ。
      - DuckDB への書き込みはトランザクション（BEGIN / DELETE（対象コードのみ） / INSERT / COMMIT）。部分失敗時に既存スコアを保護するため、削除対象を絞って処理。
      - DuckDB executemany の空リスト制約に対する回避（空の params は実行しない）。
  - regime_detector.py
    - score_regime(): ETF 1321 の直近 200 日 MA 乖離（ma200_ratio）とマクロニュースの LLM センチメントを合成して market_regime テーブルに冪等書き込みを行う。
      - ma200_ratio は target_date 未満のデータのみを使用してルックアヘッドを防止。データ不足時は 1.0（中立）でフォールバック。
      - マクロニュース抽出はキーワードによるフィルタ（複数キーワード、ILIKE）。
      - LLM 呼び出しはリトライ/フォールバックを実装。API 失敗時は macro_sentiment = 0.0 を採用して継続。
      - 合成した regime_score に閾値を当てはめて regime_label を決定（'bull'/'neutral'/'bear'）。
      - DB 書き込みはトランザクションで行い、失敗時は ROLLBACK を試行。

- 監視ログ永続化 (src/kabusys/monitoring/monitoring_db.py)
  - init_monitoring_db(): SQLite 接続に対して冪等的にテーブルとインデックスを作成するユーティリティを実装。
    - system_status, trade_logs, positions, risk_logs などの初期テーブルを作成（インデックス含む）。

Changed
- （初回リリースのため該当なし）

Fixed / Robustness improvements
- .env パーサで引用符内部のバックスラッシュエスケープ処理や export プレフィックス、インラインコメント境界の扱いを明確化しているため、.env の多様な書式に対して堅牢性を向上。
- news_nlp のレスポンスパースで JSON 以外の余計な前後テキストが混入するケースを想定し、最外の波括弧ペアを抽出して復元を試みる処理を追加（それでも失敗すれば該当チャンクはスキップ）。
- OpenAI API 呼び出しまわりで 5xx とそれ以外を区別してリトライ方針を採用。重大な API エラーでもシステム全体を停止させずフォールバック値（例: macro_sentiment=0.0）を使って継続処理する設計。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で供給すること。未設定時は ValueError を送出して早期に通知。
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により明示的に無効化可能（テストや CI の安全性向上）。

Notes / Implementation details
- DuckDB を用いるリサーチ API は SQL ウィンドウ関数（LAG/LEAD/AVG OVER 等）を活用し、パフォーマンスを考慮して日付スキャン範囲を制限している。
- position_sizing.calc_position_sizes() において lot_size は現状全銘柄共通の整数値で処理。将来的には銘柄別 lot_map を受け取る拡張を想定したコメントを残している。
- 一部関数（特に AI 周り）の内部 API 呼び出しラッパーはテスト容易性を考慮して外部からモック差替え可能（例: unittest.mock.patch で _call_openai_api を差し替えられる設計）。

Removed / Deprecated
- （初回リリースのため該当なし）

Security disclosures
- 本リリースに既知の重大なセキュリティ脆弱性はありません。API キー等の機密情報は環境変数で管理し、.env を使用する場合は適切に権限管理してください。

Acknowledgements / References
- 各モジュールの実装はリポジトリ内のドキュメント（PortfolioConstruction.md, StrategyModel.md 等）設計に準拠しています（コメントと docstring で参照）。

今後の予定
- 単元株数を銘柄別に扱う拡張（lot_map）。
- バリューファクターの PBR / 配当利回りの実装。
- news_nlp / regime_detector の LLM モデル切替と評価パイプラインの整備。