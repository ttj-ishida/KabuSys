Keep a Changelog に準拠した変更履歴（日本語）

すべての変更は慣例に従いカテゴリ別に記載しています。
フォーマット: https://keepachangelog.com/ja/

Unreleased
---------
- （現時点の未リリース変更はありません）

[0.1.0] - 2026-04-09
-------------------
Added
- パッケージ初期リリース（kabusys v0.1.0）。
- 基本モジュールを実装・公開：
  - 環境・設定管理（src/kabusys/config.py）
    - .env / .env.local の自動読み込み（優先度: OS環境変数 > .env.local > .env）。
    - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env のパースロジック（export 形式、クォート処理、インラインコメント扱い等）を実装。
    - 必須値取得ヘルパー (_require) と各種設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, PAPER_FILL_MODE 等）。
    - 環境値検証（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の有効値チェック）。
  - ポートフォリオ構築（src/kabusys/portfolio/*）
    - 候補選定: select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア加重、全スコア0時は等金額にフォールバック）。
    - ポジションサイズ算出: calc_position_sizes
      - allocation_method = "risk_based" / "equal" / "score" をサポート。
      - リスクベース計算（risk_pct, stop_loss_pct）、lot_size 単位で丸め、max_position_pct 上限、aggregate cap（available_cash に基づくスケーリング）、cost_buffer による保守的見積り、残差処理（fractional remainder に基づく再配分）を実装。
      - 価格欠損時はスキップしてログ出力。
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）
    - セクター集中制限: apply_sector_cap（既存保有を加味してあるセクターが上限超過の場合、そのセクターの新規候補を除外）。"unknown" セクターは除外対象外。
    - 市場レジーム乗数: calc_regime_multiplier（'bull'/'neutral'/'bear' に対して 1.0/0.7/0.3、未知値は 1.0 にフォールバックして警告ログ）。
  - リサーチ / ファクター計算（src/kabusys/research/*）
    - Momentum ファクター: calc_momentum（1M/3M/6M リターン、200日移動平均乖離。DuckDB の prices_daily を使用）。
    - Volatility / Liquidity ファクター: calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）。
    - Value ファクター: calc_value（raw_financials と prices_daily を組み合わせて PER / ROE を算出）。
    - ファクター探索: calc_forward_returns（複数ホライズンの将来リターンを一度のクエリで取得）、calc_ic（Spearman ランク相関による IC 計算、有効レコードが 3 未満の場合は None）、factor_summary（基本統計量）、rank（同順位の平均ランク処理）。
    - DuckDB を前提とした SQL + Python 実装。外部依存（pandas 等）を使用せずに実装。
  - AI 関連（src/kabusys/ai/*）
    - ニュース NLP（src/kabusys/ai/news_nlp.py）
      - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルに書き込む処理を実装。
      - 一度の API 呼び出しで最大バッチサイズ 20 銘柄、1 銘柄あたりの記事上限・文字数上限を設定（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
      - JSON Mode を利用し、レスポンスの厳密なバリデーション（results リスト、code/score 型チェック、未知コードの無視、スコアの ±1.0 クリップ）。
      - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフ（最大リトライ回数設定）。
      - DB 書込みは冪等（DELETE → INSERT）で、部分失敗時に既存スコアを保護する設計。
      - OpenAI クライアントの呼び出し部はテスト用に patch 可能な設計（_call_openai_api を差し替え）。
    - レジーム判定（src/kabusys/ai/regime_detector.py）
      - ETF 1321（日経225 連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して daily レジーム（'bull'/'neutral'/'bear'）を判定。
      - マクロニュースはキーワードベースで抽出（複数キーワード群）。タイトルを LLM に渡して macro_sentiment を算出。
      - レジームスコア合成式、閾値に基づく判定、結果の market_regime テーブルへの冪等書込みを実装。
      - API 呼び出し失敗時は macro_sentiment=0.0 でフェイルセーフ。
  - モニタリング DB（src/kabusys/monitoring/monitoring_db.py）
    - SQLite ベースの永続化層初期化関数 init_monitoring_db を実装（system_status / trade_logs / positions / risk_logs 等のテーブルとインデックス作成）。

Changed
- （初版リリースのため "Changed" は特になし）

Fixed
- （初版リリースのため "Fixed" は特になし）

Security
- OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を参照する。未設定時は明示的に例外を送出して処理者に通知（score_news, score_regime）。

Notes / 実装上の注意点
- ルックアヘッド防止:
  - news_nlp と regime_detector は datetime.today() / date.today() を参照せず、外部から与えた target_date を基準にウィンドウ／クエリを構成します。
  - regime_detector の prices_daily クエリは date < target_date を使いルックアヘッドを防止します。
- DuckDB / SQLite の互換性:
  - executemany に空リストを渡せない制約（DuckDB 0.10）を考慮して、空チェックを行ってから executemany を呼んでいます。
- フォールバック挙動:
  - ファクター計算でデータ不足や不正値がある場合は None を返すか（該当フィールド）、フォールバック値（ma200_ratio=1.0 等）を使い安全側に振る設計。
  - AI 呼び出し失敗時はログを残してスコア計算をスキップ／0.0 フォールバックし、処理継続を優先。
- ロギング:
  - 各モジュールで詳細な debug/info/warning ログを出力するように実装されています（例: calc_score_weights の警告、price 欠損時の debug 等）。

公開 API（パッケージ外から利用される主要関数）
- kabusys.settings（設定読み取りオブジェクト）
- kabusys.__version__ = "0.1.0"
- kabusys.portfolio:
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.research:
  - calc_momentum, calc_volatility, calc_value, zscore_normalize（kabusys.data.stats から）、calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.ai:
  - score_news（news_nlp の公開関数）
- monitoring:
  - init_monitoring_db

既知の制限 / TODO（コード内コメントより）
- position_sizing: lot_size が全銘柄共通（将来的に銘柄別 lot_map に拡張予定）。
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性あり。将来は前日終値や取得原価でフォールバックする検討あり。
- news_nlp と regime_detector はそれぞれ _call_openai_api を独立実装（モジュール間で共有しない）ため、将来の実装整合性や重複削減は検討事項。
- calc_forward_returns の horizons は最大 252 日に制限。

このリリースに関する問い合わせ・改善提案があればお知らせください。