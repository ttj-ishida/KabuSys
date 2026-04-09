CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

[0.1.0] - 2026-04-09
--------------------

Added
- 基本情報
  - パッケージの初期バージョンとして公開。__version__ = "0.1.0"。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を追加。
  - 自動ロードの探索はパッケージ内の __file__ を基点に親ディレクトリを辿り .git または pyproject.toml をプロジェクトルートと判定（CWD に依存しない）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env/.env.local の上書きを制御。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env パーサーが次をサポート・堅牢化:
    - "export KEY=val" 形式、
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、
    - インラインコメントの扱い（クォート外で直前が空白/タブの '#' をコメントとして扱う）、
    - 無効行の無視。
  - 必須環境変数取得ヘルパー _require()（未設定時は ValueError）。
  - 各種設定プロパティを用意（J-Quants / kabuステーション / LINE / DB パス / 監視阈値 / システム設定等）。
  - 設定値の検証:
    - PAPER_FILL_MODE の有効値チェック（"instant","partial","never","reject"）、
    - KABUSYS_ENV の有効値チェック（"development","paper_trading","live"）、
    - LOG_LEVEL の有効値チェック（"DEBUG","INFO","WARNING","ERROR","CRITICAL"）。
  - Path を返す設定は expanduser() を適用。

- ポートフォリオ構築 (src/kabusys/portfolio/*.py)
  - 候補選定 (portfolio_builder.select_candidates)
    - buy_signals を score 降順でソート、同点は signal_rank の昇順でタイブレーク。max_positions で上位を選択。
  - 重み計算
    - calc_equal_weights: 等金額配分（1/N）を返す。
    - calc_score_weights: スコアに応じた正規化配分を返す。全スコアが 0 の場合は等金額へフォールバックし WARNING ログを出力。
  - リスク調整 (risk_adjustment.apply_sector_cap, calc_regime_multiplier)
    - apply_sector_cap: 現在ポジションのセクター別時価総額比率が max_sector_pct を超えるセクターの新規候補を除外。sell_codes（当日売却予定）をエクスポージャー計算から除外。sector_map に無い銘柄は "unknown" として扱い、"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: レジーム（"bull"/"neutral"/"bear"）に応じて投下資金乗数を返す。未知レジームは 1.0 でフォールバックし WARNING を出力。
  - 株数決定 (position_sizing.calc_position_sizes)
    - allocation_method に応じて "risk_based" / "equal" / "score" をサポート。
    - risk_based: risk_pct / (price * stop_loss_pct) に基づくポジションサイズ。
    - equal/score: weight ベースで per-position 上限と aggregate 上限を考慮して算出。
    - 単元株（lot_size）で丸め、単元ごとの端数処理・再配分ロジックを実装（コストバッファを考慮して安全側に見積もる）。
    - aggregate cap 超過時はスケーリングし、scale 後の端数を lot_size 単位で残差順に追加配分（安定ソートで再現性確保）。
    - 価格欠損や price<=0 の場合はその銘柄をスキップしてログ出力。

- リサーチ / ファクター計算 (src/kabusys/research/*.py)
  - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。ウィンドウ不足時は None を返す。
  - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range の NULL 伝播を正しく扱い、データ不足時は None を返す。
  - calc_value: raw_financials から target_date 以前の最新財務データを取得して PER、ROE を計算（EPS が 0 または NULL の場合は PER を None）。
  - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。horizons のバリデーションあり（1〜252）。
  - calc_ic / rank / factor_summary: Spearman（ランク相関）による IC 計算、同順位は平均ランクとする rank ユーティリティ、列ごとの基本統計量サマリーを標準ライブラリのみで実装。
  - 全関数は DuckDB 接続を受け取り prices_daily / raw_financials を参照。データ不足・非有限値等の扱いが明示されている。

- AI: ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini、JSON Mode）で銘柄ごとのセンチメント（-1.0〜1.0）を付与して ai_scores テーブルへ書き込む機能を実装。
  - ニュース収集ウィンドウの計算（JST 前日15:00〜当日08:30 を UTC に変換）を calc_news_window として提供。
  - 処理の特徴:
    - 1銘柄あたり最大記事数 / 最大文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 最大 _BATCH_SIZE（20）銘柄を1バッチで API 呼び出し。
    - 429 / ネットワーク断 / タイムアウト / 5xx サーバエラーは指数バックオフでリトライ（最大回数あり）。その他エラーはリトライせずスキップ。
    - レスポンスの堅牢なバリデーション（JSON パース復元ロジック、results リストの存在、各 item の code/score 検証、スコアの数値化、スコアのクリップ）。
    - 書き込みはトランザクション内で部分置換（DELETE WHERE date & code → INSERT）を実施し、部分失敗時に既存スコアを不要に消さない工夫あり。
    - API キーは引数優先、未指定時は環境変数 OPENAI_API_KEY を参照（未設定なら ValueError）。
    - テスト容易性のため OpenAI 呼び出し部を別関数化（ユニットテストでモック可能）。

- AI: 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経連動）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で regime_label を判定（'bull' / 'neutral' / 'bear'）。
  - マクロニュースはタイトルをキーワードで抽出（_MACRO_KEYWORDS）し最大件数まで取得。記事が無い場合は LLM 呼び出しせず macro_sentiment=0.0 を採用。
  - LLM 呼び出しは冗長なエラー処理（リトライ・5xx 判定）と JSON パースエラーハンドリングを実装し、失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
  - レジームスコア合成後にしきい値判定（_BULL_THRESHOLD / _BEAR_THRESHOLD）でラベル付与し、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - API キーは引数優先、未指定時は環境変数 OPENAI_API_KEY を参照（未設定なら ValueError）。

- 監視ログ永続化 (src/kabusys/monitoring/monitoring_db.py)
  - SQLite 接続向けに監視用 DB スキーマ作成ユーティリティを追加（init_monitoring_db）。
  - system_status / trade_logs / positions / risk_logs 等のテーブルとインデックスを冪等に作成する SQL を実装。

Changed
- （初版）公開版のため変更履歴は追加のみ。

Fixed
- （初版）バグ修正は履歴なし。

Notes / Implementation details / 安全策
- ルックアヘッドバイアス防止のため、日付参照は外部から与える target_date ベースで統一、datetime.today()/date.today() を直接参照しない設計。
- DuckDB / SQLite との互換性を考慮し、executemany による空リストバインドや ANY(?) の挙動を避ける実装を採用。
- OpenAI API 呼び出しは JSON Mode を使い厳密な JSON を期待するが、実運用でのノイズを考えフォールバックパースを実装。
- ロギングを各所に配置し、データ不足や想定外入力時には WARNING/DEBUG を出力して安全にフォールバックする挙動を採用。

Breaking Changes
- なし（初回リリース）。

Acknowledgments
- ドキュメント内で参照される仕様ファイル: PortfolioConstruction.md、StrategyModel.md（実装コメントに従う）。