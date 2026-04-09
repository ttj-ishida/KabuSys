# CHANGELOG

この CHANGELOG は Keep a Changelog のフォーマットに準拠しています。  
コードベースから推測可能な変更・初期実装内容を記載しています。

全般的な注記
- 多くのモジュールは DuckDB 接続や環境変数を受け取り動作する設計になっており、本番の注文 API 呼び出し等には直接アクセスしない（純粋関数 / DB 読み取り中心の実装が多い）。
- AI 周りは OpenAI（gpt-4o-mini）を利用するが、API 呼び出し部分はテスト差し替えしやすいよう分離されている。
- ルックアヘッドバイアス対策として各所で date/datetime の取得を外部から渡す設計（datetime.today() 等を直接参照しない）が採用されている。

Unreleased
- （なし）

v0.1.0 - 2026-04-09
-------------------

Added
- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。プロジェクトルートは __file__ を起点に .git / pyproject.toml を探索して特定。
  - .env のパース機能を強化：
    - コメント行 / 空行無視、`export KEY=val` 形式対応。
    - シングル・ダブルクォート内のエスケープ処理を考慮した値抽出。
    - クォートなし値では行内のインラインコメントを条件付きで無視。
  - 読み込み優先順位：OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - Settings クラスを導入し、アプリの各種設定をプロパティ経由で取得可能にした（J-Quants, kabuステーション API, LINE, DB パス, Paper Trading 設定, 監視閾値, 環境/ログレベルなど）。
  - 複数の設定でバリデーションとデフォルト値を定義（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）。

- パッケージメタ情報 (src/kabusys/__init__.py)
  - __version__ = "0.1.0"
  - 基本的な __all__ エクスポートを定義。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソート、同スコア時は signal_rank の昇順でタイブレーク。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率に基づく配分。全銘柄のスコアが 0.0 の場合は等金額配分へフォールバック（WARNING ログ）。
  - risk_adjustment.py
    - apply_sector_cap: 現在保有のセクター時価を計算し、セクター集中が max_sector_pct を超える場合にそのセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す（デフォルトフォールバックと WARNING ログあり）。
  - position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した株数計算。lot_size（単元）で丸め、per-position 上限・aggregate cap（利用可能現金）に基づくスケーリング、cost_buffer による保守的見積り、余剰キャッシュに対する残差配分アルゴリズムを実装。
    - risk_based では stop_loss_pct と risk_pct を使った許容ポジション計算を実装。

- 研究 / ファクター計算 (src/kabusys/research/)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（MA200）を DuckDB の SQL ウィンドウ関数で計算。MA200 のデータ不足時は None を返す。
    - calc_volatility: 20日 ATR（true range の平均）、相対 ATR (atr_pct)、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を慎重に扱う実装。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算。EPS が 0/欠損の場合は PER を None にする。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD による単一クエリで計算。horizons の入力検証あり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（記録数が 3 未満なら None）。ランク付けは平均ランク（同順位は平均ランク）で処理。
    - rank, factor_summary: ランク付けユーティリティと基本統計量集計（count/mean/std/min/max/median）を標準ライブラリのみで実装。
  - research パッケージ __init__ で zscore_normalize を含む主要関数を再エクスポート。

- AI 関連 (src/kabusys/ai/)
  - news_nlp.py
    - score_news: raw_news と news_symbols を用いて銘柄ごとにニュースを集約、OpenAI（gpt-4o-mini）で銘柄別センチメントを取得して ai_scores テーブルへ書き込み。主な機能・特長:
      - ニュース時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で UTC に変換。
      - 1 銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 最大バッチサイズ _BATCH_SIZE（20）で OpenAI に送信。JSON Mode を利用しレスポンスをバリデーションしてスコアを抽出。
      - 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。その他エラーはフェイルセーフで空スコア（無視）にする。
      - レスポンス復元ロジック（JSON デコード失敗時に外側の { ... } を抽出）や LLM が整数で code を返すケースへの対応など堅牢性を確保。
      - スコアは ±1.0 にクリップ。DB 書き込みは部分失敗対策として該当コードのみ DELETE → INSERT（トランザクション）を実施。
      - API キー未設定時は ValueError を送出。
    - テスト容易性のため _call_openai_api を分離（テストで patch 可能）。
  - regime_detector.py
    - score_regime: ETF 1321 の ma200 乖離（_calc_ma200_ratio）とマクロニュースの LLM センチメント（_score_macro）を合成して日次の market_regime を決定。設計上の特徴:
      - ma200 計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。データ不足時は中立（1.0）にフォールバックし WARNING ログ。
      - マクロニュースはキーワードフィルタでタイトルを取得（上限あり）。記事が無ければ LLM 呼び出しは行わず macro_sentiment=0.0。
      - 合成式: 0.7*(ma200_ratio - 1)*10 + 0.3*macro_sentiment を -1..1 にクリップ。閾値で 'bull' / 'neutral' / 'bear' を判定。
      - API キー未設定時は ValueError を送出。DB 書き込みは冪等（DELETE→INSERT）でトランザクション内で行う。
    - news_nlp と同様に API 呼び出し部分を分離している（モジュール間で private 関数を共有しない設計）。

- AI パッケージ __init__ で score_news を再エクスポート。

- 監視ログ用 DB ユーティリティ (src/kabusys/monitoring/monitoring_db.py)
  - init_monitoring_db: SQLite 接続を受け取り、system_status / trade_logs / positions / risk_logs 等のテーブルとインデックスを冪等的に作成するスクリプトを実装（監視ログ永続化層）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を使用。未設定時は明示的にエラーを出す箇所あり（安全策）。

Notes / 今後の改善メモ（コード内コメントより推測）
- position_sizing.calc_position_sizes: 銘柄毎の lot_size を将来的にサポートする設計に拡張予定（現状は共通 lot_size）。
- apply_sector_cap: price が欠損した場合のエクスポージャー過少見積りの補完（前日終値や取得原価を用いるフォールバック）の検討。
- AI モジュール: レスポンス整形・堅牢性や retry のパラメータ調整は運用に合わせてチューニングが必要。
- DuckDB executemany に関する互換性対策（空リスト回避）を実装済み。

以上。