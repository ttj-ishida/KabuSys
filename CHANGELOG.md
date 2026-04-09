# CHANGELOG

このプロジェクトは Keep a Changelog の形式に準拠して変更履歴を管理します。

全般的な方針:
- 互換性のない変更は明示的に Breaking Changes として記載します。
- リリース日には YYYY-MM-DD 形式を使用します。

### [Unreleased]
- 現在未リリースの変更はありません。

### [0.1.0] - 2026-04-09
初回リリース。主要な機能群を実装しました。

Added
- 基本メタ情報
  - パッケージバージョンを src/kabusys/__init__.py の __version__ = "0.1.0" として設定。
  - パッケージ公開における主要サブモジュールを __all__ で指定（data, strategy, execution, monitoring）。

- 環境設定/ロード機能（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは __file__ を起点に上位ディレクトリを探索して .git または pyproject.toml を検出して特定。
    - ルートが特定できない場合は自動ロードをスキップ。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト用）。
  - .env パース機能強化:
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォート、バックスラッシュエスケープを考慮した値抽出。
    - インラインコメントの取り扱い（クォートあり/なしでの挙動差異）に対応。
  - .env の読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は override=True）。
  - OS 環境変数を保護するため protected key セットを用意し、override 動作から除外。
  - 必須環境変数取得ヘルパ _require を実装（未設定時は ValueError を投げる）。
  - 設定プロパティ群（Settings クラス）を実装:
    - J-Quants / kabuステーション / LINE / DB パス（DuckDB / SQLite） / Paper trading 用設定 / 監視設定（PID ファイル/キルフラグなど） / リソース閾値 / システム環境・ログレベル判定。
    - PAPER_FILL_MODE の検証（有効値: instant, partial, never, reject）。不正値は ValueError。
    - KABUSYS_ENV の検証（development, paper_trading, live）。不正値は ValueError。
    - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。不正値は ValueError。

- ポートフォリオ構築（src/kabusys/portfolio）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順、同点時は signal_rank 昇順でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分（各銘柄 weight = 1/N）。
    - calc_score_weights: スコア比率で配分。全銘柄スコア合計が 0 の場合は等金額にフォールバックし WARNING ログ出力。
  - risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別時価を計算し、1 セクターの比率が閾値を超える場合に同セクターの新規候補を除外（"unknown" セクターは制限の対象外）。
    - calc_regime_multiplier: レジーム（'bull'/'neutral'/'bear'）に応じた投下資金の乗数を返す（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジーム時は 1.0 でフォールバックし WARNING を出力。
  - position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数計算を提供。allocation_method により以下をサポート:
      - risk_based: リスク額（portfolio_value * risk_pct）と stop_loss_pct に基づく株数計算。最大保有比率（max_position_pct） と lot_size による丸め。
      - equal / score: weight に応じた割当。max_utilization により per-position 上限を適用。
    - 集約キャップ（aggregate cap）処理:
      - 全銘柄の合計コストが available_cash を超える場合にスケールダウン。
      - cost_buffer により手数料・スリッページを保守的に見積もる（price に乗じる）。
      - スケール時の残差は lot_size 単位で fractional 残差の大きい順に追加配分し、上限を超えないよう安全弁を設ける。
    - ログ出力や価格欠損時のスキップ処理を実装。
  - パッケージレベルで必要関数を __all__ に公開。

- リサーチ（src/kabusys/research）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（MA200）を DuckDB の prices_daily テーブルから計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、ATR 比率（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を厳密に扱い、窓内行数チェックで条件満たさない場合は None。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し PER/ROE を計算（EPS が 0 または欠損なら PER は None）。
  - feature_exploration.py
    - calc_forward_returns: target_date の終値から指定ホライズン（デフォルト [1,5,21] 営業日）先までのリターンを一括取得。horizons の入力検証あり。
    - calc_ic: ファクターと将来リターンのスピアマン（順位）相関を計算。有効レコード数が 3 未満なら None。
    - rank: 同順位は平均ランクとするランク関数（round(...) による丸めで ties の漏れを軽減）。
    - factor_summary: count/mean/std/min/max/median を算出（None 値は除外）。
  - research パッケージの __init__ にて zscore_normalize（kabusys.data.stats 由来）等を再公開。

- AI 関連（src/kabusys/ai）
  - news_nlp.py
    - raw_news / news_symbols からニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメントを評価し、ai_scores テーブルへ書き込むワークフローを実装。
    - ニュース時間ウィンドウ計算（target_date に対する JST→UTC 変換）を実装。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄ごとに API 呼び出し。
    - 1 銘柄あたりのトークン爆発対策: 最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - API 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで行う（最大 _MAX_RETRIES）。
    - レスポンスバリデーション: JSON 抽出、results リスト、code/score 検証、未知コード無視、スコアを ±1.0 にクリップ。
    - DuckDB への書き込みは冪等に行う（BEGIN / DELETE 対象 code 列 / INSERT / COMMIT）。部分失敗時に他コードの既存データを消さない設計。
    - テスト用に _call_openai_api の差し替え（patch）を想定している。
  - regime_detector.py
    - ETF 1321 の MA200 乖離（直近 200 日）とマクロニュースの LLM センチメントを重み合成して市場レジーム（bull/neutral/bear）を判定する機能を実装。
    - マクロニュースはタイトルでキーワード検索（複数キーワードリスト）し上位 N 件を取得。
    - LLM 呼び出しに対してリトライとフェイルセーフ（失敗時は macro_sentiment = 0.0）を実装。
    - 合成ルール: 0.7*(ma200_ratio-1)*scale + 0.3*macro_sentiment を -1..1 にクリップし閾値でラベル判定（設定可能な定数で調整）。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - news_nlp.calc_news_window を再利用して時間ウィンドウを算出。
  - ai パッケージの __init__ から score_news を公開（ニュース NLP の主要エントリポイント）。

- 監視用 DB 層（src/kabusys/monitoring/monitoring_db.py）
  - SQLite を使った監視ログ永続化レイヤを実装。冪等に 5 テーブル + インデックスを作成する init_monitoring_db を提供（system_status, trade_logs, positions, risk_logs 他）。
  - trade_logs / positions / system_status 等のスキーマと基本インデックスを用意。
  - 監視系データの格納に特化しビジネスロジックを含まない実装。

Other
- テストを容易にする設計:
  - OpenAI API 呼び出し関数はモジュール内で分離しており unit test で patch 可能（_call_openai_api の差し替え想定）。
- ロギングとフェイルセーフ:
  - 多くの箇所で詳細な debug/info/warning ログを記録。LLM/API 失敗時は安全側のデフォルト（例: macro_sentiment=0.0）を使用して処理継続。
- ドキュメント/設計ノート:
  - 各モジュールに設計意図・参照ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）への言及や TODO 注釈を含む。

Known Issues / Notes
- monitoring_db.py はファイル末尾で一部切れている状態（risk_logs 等の続きが含まれる可能性あり）。リリース前に完全なスキーマ確認が必要。
- position_sizing の price 欠損（0.0）の場合の取り扱いは TODO コメントあり。将来的に前日終値や取得原価でフォールバックする検討が残っている。
- lot_size は現時点では全銘柄共通で固定（デフォルト 100）。将来的に銘柄別 lot_map の導入を想定している。
- OpenAI 関連: API バージョン変化により例外属性（status_code 等）が変わる可能性があるため、安全に属性取得しているが、API SDK の大きな変更には追従が必要。
- research モジュールは DuckDB に依存する SQL 実行を行うため、テーブルスキーマ（prices_daily, raw_financials 等）が正しく用意されていることが前提。

Breaking Changes
- なし（初回リリース）。

Security
- なし特記事項。ただし API キー（OPENAI_API_KEY など）は環境変数で管理する想定。

今後の予定（例）
- monitoring_db のスキーマ整備と追加 CRUD ヘルパの実装。
- stocks マスタに基づく銘柄別 lot_size サポート。
- .env 値のより厳密な型検証ユーティリティ追加。
- テストカバレッジ拡充（特に AI モジュールの外部依存をモックした統合テスト）。

--- 

（必要であれば、各モジュールの変更内容をさらに細分化してコミット単位・機能単位で記載できます。）