# CHANGELOG

この変更履歴は、提供されたコードベースの内容から推測して作成しています（実際のコミット履歴に基づくものではありません）。各項目はコード内の実装・コメント・ドキュメントに基づきまとめています。

フォーマット: Keep a Changelog 準拠

## [0.1.0] - 2026-04-09

### Added
- 全体
  - 初期リリース。パッケージメタ情報に __version__ = "0.1.0" を設定。
  - パッケージ公開時の主要モジュール群を実装（data, strategy, execution, monitoring を __all__ に公開）。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local または OS 環境変数から設定を読み込む自動ロード実装。
    - プロジェクトルート検出は .git または pyproject.toml を起点に行い、CWD に依存しない設計。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ実装（export 形式、クォート／エスケープ、行内コメントの扱いに対応）。
  - OS 環境変数を保護する protected キー機構（.env.local は上書き、.env は未設定キーのみ設定）。
  - 必須環境変数未設定時に ValueError を送出する _require ユーティリティ。
  - Settings クラスを実装し、アプリケーションで利用する各種設定 getter を提供:
    - J-Quants / kabu API / LINE / DB パス（duckdb, sqlite, paper_trading）など。
    - Paper Trading の fill_mode 検証（instant/partial/never/reject）。
    - 監視関連のファイルパス・閾値（PID, kill flag, CPU/Mem/Disk）。
    - 環境種別（KABUSYS_ENV）・ログレベル（LOG_LEVEL）検証と is_live/is_paper/is_dev のヘルパー。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank でブレーク）で切り出す関数。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で配分。全スコアが 0 の場合は等分にフォールバックし WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター別既存保有比率が閾値を超える場合、新規候補をブロック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を返す（未知はフォールバック）。
  - position_sizing:
    - calc_position_sizes: 各種 allocation_method（risk_based / equal / score）に対応した発注株数計算。
      - 単元株（lot_size）丸め、per-position / aggregate cap、cost_buffer（手数料・スリッページ見積り）、利用可能現金に合わせたスケーリングを実装。
      - 価格欠損時のスキップやログ出力、最大保有上限の考慮。
      - aggregate スケーリング時に端数の再配分アルゴリズムを実装（fractional remainder に基づく安定な追加配分）。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200 日移動平均乖離（ma200_dev）を DuckDB の prices_daily を使って計算。十分な履歴がない場合は None を返す設計。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高変化率を計算。true_range の NULL 伝播を適切に制御。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（target_date 以前の最新財務データを取得）。
  - feature_exploration:
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。horizons のバリデーションあり。
    - calc_ic: ファクターと将来リターンのスピアマン（ランク相関）を計算。有効レコードが少なければ None を返す。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸めで ties 対策）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー関数。
  - DuckDB 接続を受け取り、prices_daily / raw_financials のみ参照する非破壊的な設計（ルックアヘッドに配慮）。

- AI / NLP (kabusys.ai)
  - news_nlp:
    - calc_news_window: ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC naive datetime で計算するユーティリティ。
    - score_news: raw_news と news_symbols を集約して各銘柄のセンチメント（ai_scores テーブル）を OpenAI（gpt-4o-mini）へ問い合わせて算出・書き込み。
      - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、1銘柄あたりの記事数／文字数トリム、JSON Mode による厳密 JSON 応答想定。
      - RateLimitError / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフリトライ、その他エラーはスキップ（フェイルセーフ）。
      - レスポンスの厳密なバリデーション（results キー・型・既知コード・数値変換）を行い、スコアを ±1.0 にクリップ。
      - 書き込みは部分失敗に備えて対象コードのみ DELETE → INSERT の冪等処理を行う（DuckDB executemany の制約に配慮）。
  - regime_detector:
    - score_regime: ETF 1321 の ma200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルに冪等書き込み。
    - マクロ記事抽出はキーワードベース。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - LLM 呼び出しは news_nlp とは別実装でモジュール分離されている。
  - OpenAI クライアントは OpenAI(api_key=...) を使用。API キーは引数または環境変数 OPENAI_API_KEY で指定。

- 監視 DB (kabusys.monitoring.monitoring_db)
  - init_monitoring_db: SQLite 接続に対して監視用テーブル群（system_status, trade_logs, positions, risk_logs など）と必要なインデックスを冪等に作成するスクリプトを実装。

### Changed
- 初期バージョンのため該当なし（最初の機能追加）。

### Fixed
- 初期バージョンのため該当なし。実装中に防御的なエラーハンドリングやフォールバック（データ不足、API失敗、価格欠損等）を組み込んでいるため、運用上の安全性を高めている。

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用。キー未設定時は ValueError を送出する箇所あり（明示的なエラー）。
- 環境設定ロードは OS 環境変数を保護する仕組み（protected set）を採用。

### Notes / Known issues / TODO（コード内コメントより）
- position_sizing: price が欠損（0.0）の場合にエクスポージャーやサイズが過少見積もられる問題を指摘する TODO。前日終値や取得原価によるフォールバックを検討。
- 将来的に銘柄ごとの lot_size を導入する設計拡張の TODO。
- research / factor 計算は現時点で PBR・配当利回り等を未実装（calc_value に記載）。
- DuckDB executemany は空リストを受け付けない制約に合わせた実装になっている（互換性考慮）。
- news_nlp / regime_detector: LLM 呼び出しのテスト時置換ポイント（_call_openai_api の patch）が用意されている。

---

今後のリリース向けには、テストカバレッジ、エッジケース・性能チューニング、銘柄別 lot_size 対応、欠損価格のフォールバック実装などが想定されます。必要であれば、この CHANGELOG をベースにより詳細なリリースノート（各ファイルの差分や設計判断の補足）を作成します。