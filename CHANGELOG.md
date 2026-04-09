CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------
- なし（初回リリースは 0.1.0）

[0.1.0] - 2026-04-09
--------------------
Added
- 基本パッケージ構成を追加。
  - kabusys パッケージのバージョンを 0.1.0 として設定。
- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出を .git または pyproject.toml を基準に行い、CWD に依存しない自動ロードを追加。
  - .env パースの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートの中でのバックスラッシュエスケープ処理をサポート。
    - インラインコメントの取り扱い（クォート外の '#' は直前が空白・タブのときのみコメントとして扱う）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - 必須環境変数取得時に未設定なら ValueError を投げる _require ユーティリティを追加。
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等に対する入力バリデーションを実装。
  - パス設定は Path.expanduser を使用してチルダ展開に対応。

- ポートフォリオ構築 (kabusys.portfolio)
  - 銘柄選定:
    - select_candidates: スコア降順、同点は signal_rank の昇順で上位 N を選択するロジックを実装。
  - 重み計算:
    - calc_equal_weights: 等金額配分を実装。
    - calc_score_weights: スコア加重配分を実装。全スコアが 0 の場合は等金額配分へフォールバックし、WARNING ログを出力。
  - リスク調整:
    - apply_sector_cap: セクター別エクスポージャーを計算し、1 セクター比率が閾値を超える場合に該当セクターの新規候補を除外する機能を実装（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知レジームは 1.0 でフォールバックし警告ログを出力。
  - 株数決定:
    - calc_position_sizes: risk_based / equal / score の割当方式をサポート。単元株丸め、1銘柄上限、aggregate cap（available_cash）に応じたスケールダウン、cost_buffer（手数料・スリッページ見積り）を考慮した保守的な見積り、残差配分ロジック（lot_size 単位での追加配分）を実装。

- リサーチ・ファクター計算 (kabusys.research)
  - calc_momentum: mom_1m/3m/6m と 200 日移動平均乖離（ma200_dev）を DuckDB の prices_daily を用いて算出。
  - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
  - calc_value: raw_financials から最新財務データを取得し PER（EPS が無効な場合は None）、ROE を計算。
  - calc_forward_returns: 指定ホライズン先の将来リターン（デフォルト [1,5,21]）を一度のクエリで取得。
  - calc_ic / rank / factor_summary:  
    - calc_ic: スピアマンのランク相関（IC）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクで扱う実装。浮動小数の丸め誤差対策として round(..., 12) を用いる。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー機能。
  - 設計上の注意:
    - DuckDB 接続を受け取り SQL+Python で完結。prices_daily / raw_financials のみ参照。外部 API や pandas 等に依存しない実装。

- AI 関連 (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp):
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む機能を実装（score_news）。
    - バッチサイズ、最大記事数、最大文字数制限、時間ウィンドウ（JST ベースを内部で UTC に変換）などの制約実装。
    - API 呼び出しのリトライ（RateLimit / 接続エラー / Timeout / 5xx）や指数バックオフ、レスポンス検証（JSON 抽出・形式チェック・スコア型チェック）を実装。失敗時は該当チャンクをスキップしてフェイルセーフ動作。
    - 書き込みは冪等操作（DELETE → INSERT）で、部分失敗時に既存スコアを保護するため更新対象コードを限定して実行。
  - レジーム判定 (kabusys.ai.regime_detector):
    - ETF 1321 の ma200 乖離（70% 重み）とマクロニュースの LLM センチメント（30% 重み）を合成し、日次で 'bull'/'neutral'/'bear' を判定して market_regime テーブルへ書き込む機能を実装（score_regime）。
    - メカニズム: ma200_ratio の算出（ルックアヘッド防止で target_date 未満のデータのみ使用）、マクロ記事抽出（キーワードマッチ）、LLM スコア取得（リトライ含む）、スコア合成と閾値判定、DB への冪等書き込み。
    - LLM 呼び出しは失敗時に macro_sentiment = 0.0 でフォールバックするフェイルセーフを実装。
    - news_nlp の calc_news_window を再利用して時間ウィンドウを統一。

- 監視DB 永続化層 (kabusys.monitoring.monitoring_db)
  - SQLite 接続に対して監視用テーブル群（system_status, trade_logs, positions, risk_logs など）とインデックスを作成する init_monitoring_db を追加（冪等実行）。

Changed
- モジュール構成を整理し、各機能を分割（config / portfolio / research / ai / monitoring）。
- 可能な限り副作用を抑えた純粋関数（ポートフォリオ・リサーチ系）として設計。多くの関数は DB 接続や入力データを引数で受け取り副作用を持たない。

Fixed
- .env 読み込みでファイルオープン失敗時に warnings.warn を出すようにして明示化。
- ai_scores / market_regime への書き込みで executemany に空リストを渡すと問題になる点を回避（空チェックを追加）。

Security
- OpenAI API キーは引数で与えるか環境変数 OPENAI_API_KEY を使用する設計とし、未設定時は明示的に ValueError を投げることで意図せぬ無効実行を防止。

Notes / Implementation details
- 多くの関数は DuckDB / SQLite 接続を外部から受け取るためテストが容易。
- デフォルト挙動は保守的（例: データ不足時は中立値やフォールバックを使用）で、本番環境での安全性を重視。
- 今後の拡張点として、銘柄別の lot_size を受け取る設計や価格フォールバック（前日終値等）等の TODO がソース内に記載されています。

References
- 各モジュール内に PortfolioConstruction.md / StrategyModel.md 等の設計参照が明記されています（ドキュメント準拠で実装）。

--- 
注: 上記は提供されたソースコードからの推測に基づく CHANGELOG です。実際のリリースノートや履歴管理に合わせて適宜編集してください。