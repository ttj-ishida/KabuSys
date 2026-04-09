CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/

Unreleased
----------

- （なし）

0.1.0 - 2026-04-09
------------------

Added
- パッケージ初回公開
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"、主要サブパッケージを __all__ で公開。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込み（優先順: OS 環境変数 > .env.local > .env）。
    - プロジェクトルート検出ロジック: __file__ を起点に .git または pyproject.toml を探索。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パーサ実装（コメント・export 句・クォート・エスケープ対応）。
    - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス /監視閾値 / システム設定等をプロパティとして取得。
    - 必須設定取得時の検証（_require による ValueError 送出）。
    - 入力値検証:
      - PAPER_FILL_MODE（instant/partial/never/reject）
      - KABUSYS_ENV（development/paper_trading/live）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - OS 環境変数を保護するため読み込み時に protected set を利用（.env による上書きを制御）。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順で候補選定（同点は signal_rank でブレーク）。
    - calc_equal_weights: 等金額配分の重み算出。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額にフォールバックし WARNING を出力。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有時価を集計して新規候補を除外、"unknown" セクターは適用外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルト値・未知レジームのフォールバックと警告）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: 発注株数計算（allocation_method: "risk_based" / "equal" / "score" をサポート）。
      - risk_based: 許容リスク率 / 損切り率を用いたサイズ計算。
      - equal/score: 重みと価格・利用可能現金等を考慮した配分。
      - 単元（lot_size）丸め、1 銘柄上限・アグリゲート上限の評価、cost_buffer による保守的見積り。
      - 投資合計が available_cash を超える場合の縮小アルゴリズム（スケーリングと端数配分ロジック）。

- リサーチ（DuckDB ベース、標準ライブラリのみ）
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離等の計算（prices_daily を参照）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等の計算。
    - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE 計算（最新財務レコード取得ロジック含む）。
    - 全関数は不足データ時に None を返すなど堅牢な挙動。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（SQL で LEAD を使用、horizons 検証あり）。
    - calc_ic: スピアマンランク相関（IC）計算（結合・欠損値除外・最小サンプルチェック）。
    - rank: 同順位は平均ランクで処理（丸めにより ties 検出を安定化）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。

- AI / LLM 統合
  - src/kabusys/ai/news_nlp.py
    - score_news: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）でニュースセンチメントを取得し、ai_scores テーブルへ書き込み。
    - 特徴:
      - ニュース収集ウィンドウを UTC で決定（JST ベースの固定ウィンドウ: 前日 15:00 ～ 当日 08:30）。
      - 銘柄毎に記事数・文字数上限でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 最大 _BATCH_SIZE（20）銘柄ずつバッチ送信、JSON Mode を利用した厳密な JSON レスポンス期待。
      - レート制限(429)、ネットワーク断、タイムアウト、5xx を対象とした指数バックオフによるリトライ。
      - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列・型チェック、未知コードは無視、スコアを ±1.0 にクリップ）。
      - DuckDB に対する冪等な書き込み（DELETE → INSERT）を実装、部分失敗時に他銘柄スコアを保護。
      - テスト容易性: _call_openai_api をパッチ可能に設計。
      - API キーは引数優先、未指定時は OPENAI_API_KEY 環境変数参照。未設定時は ValueError。
  - src/kabusys/ai/regime_detector.py
    - score_regime: ETF 1321 の MA200 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム判定（'bull'/'neutral'/'bear'）を market_regime テーブルへ書き込み。
    - 特徴:
      - _calc_ma200_ratio: ルックアヘッドを避けるため target_date 未満のデータのみを利用し、不足時は中立 (1.0) にフォールバック。
      - _fetch_macro_news: マクロキーワードフィルタでタイトルを抽出（キーワードリストあり）。
      - _score_macro: LLM 呼び出しのリトライとフェールセーフ（失敗時 macro_sentiment=0.0）。
      - API キーは引数優先、未指定時は OPENAI_API_KEY 環境変数参照。未設定時は ValueError。
      - LLM 呼び出し部は news_nlp と別実装にしてモジュール結合を回避。

- 監視ログ永続化層（SQLite）
  - src/kabusys/monitoring/monitoring_db.py
    - init_monitoring_db: system_status / trade_logs / positions / risk_logs 等を含むテーブルとインデックスを作成する冪等スクリプトを提供。
    - （注）スキーマの主なカラム・インデックスを定義し、監視用途の永続化をサポート。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- .env ロード時に OS 環境変数を protected として扱い、意図しない上書きを防止する仕組みを導入。

Notes / Limitations / TODO
- position_sizing: price が欠損（0.0）の場合のフォールバック（前日終値や取得原価など）は TODO コメントあり。
- 将来的に銘柄毎の lot_size をサポートするための拡張案がコメントで残されている（現状はグローバル単元固定）。
- OpenAI 仕様や SDK バージョン差異に備え、APIError の status_code 取得は getattr を用いて安全に扱っているが、SDK 変更時は挙動確認が必要。
- news_nlp / regime_detector は外部 API 呼び出しを含むため、実行環境での API キー設定とコストに注意。

参考
- 環境変数例や .env 設定方法は README / .env.example を参照してください（リポジトリ配布時に同梱される想定）。
- 各モジュールは DuckDB / SQLite のテーブル構造に依存します。実運用前にデータマートの準備が必要です。