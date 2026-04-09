Changelog
=========

すべての重要な変更をこちらに記載します。本ファイルは Keep a Changelog の形式に準拠します。

[Unreleased]
------------

（現在のリリース以降の変更はここに記載してください）

[0.1.0] - 2026-04-09
-------------------

Initial release — 日本株自動売買システムのコアライブラリを公開。

Added
- 基本情報
  - パッケージバージョンを src/kabusys/__init__.py の __version__ = "0.1.0" として設定。
  - パッケージエクスポート: data, strategy, execution, monitoring（__all__）。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイル（.env, .env.local）や環境変数から設定を自動ロード（プロジェクトルートを .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - export KEY=val, コメント、クォート／エスケープ処理等に対応した .env パーサーを実装。
  - 環境変数取得用 Settings クラスを追加。J-Quants / kabuステーション / LINE / DB パス /監視閾値 等のプロパティを提供。
  - バリデーション機能:
    - KABUSYS_ENV（development/paper_trading/live のみ許容）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容）
    - PAPER_FILL_MODE（instant/partial/never/reject のみ許容）
  - Path 型でのパス解決（expanduser を使用）。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順＋タイブレークで選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等分配にフォールバック（WARNING ログ）。
  - risk_adjustment
    - apply_sector_cap: セクター毎の既存エクスポージャーから新規候補を除外するセクター上限機能（"unknown" セクターは制限除外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルトフォールバック含む、未知レジームは警告ログ）。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer による保守見積り、残差処理による追加配分ロジックを実装。
    - 価格欠損時のスキップやログ出力、max_per_stock 計算、整数丸めの再現性確保など。

- リサーチ（src/kabusys/research/*）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離の計算（DuckDB を用いた SQL 実装）。データ不足時の None 処理。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。true_range 計算で欠損制御。
    - calc_value: raw_financials から最新財務を結合して PER / ROE を算出（EPS 欠損で PER は None）。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons のバリデーションあり。
    - calc_ic / rank: スピアマンランク相関（IC）計算と同順位処理（平均ランク）。ties 対応のため丸めを導入。
    - factor_summary: count/mean/std/min/max/median の統計サマリー（None 値除外）。
  - research パッケージは zscore_normalize の再エクスポートを含む（kabusys.data.stats 依存）。

- AI / NLP（src/kabusys/ai/*）
  - news_nlp
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）によりセンチメントスコアを算出して ai_scores に書き込む。
    - タイムウィンドウ設計（前日15:00 JST 〜 当日08:30 JST を UTC 換算）や記事トリム（記事数／文字数上限）を実装。
    - バッチ処理（最大20銘柄／リクエスト）、JSON Mode を利用した厳密なレスポンス期待、レスポンスのバリデーションと ±1.0 へのクリップ。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、その他エラーはフェイルセーフでスキップ。
    - DuckDB への書き込みは部分的破壊を避けるため対象コードのみ DELETE → INSERT（executemany を利用、空リストの扱いに注意）。
    - テスト容易性のため _call_openai_api を差し替え可能（ユニットテスト用フック）。
  - regime_detector
    - ETF 1321 の ma200 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - マクロニュースはキーワードマッチで抽出。LLM 呼び出しは記事がある場合のみ行う。API 失敗時は macro_sentiment=0.0 で継続。
    - レジームスコア合成式、閾値判定、market_regime テーブルへの冪等書き込みを実装。
    - news_nlp と同様に OpenAI 呼び出しロジックは内部実装でテスト差替え可能。

- モニタリング永続化（src/kabusys/monitoring/monitoring_db.py）
  - SQLite を用いた監視ログ永続化層を提供。system_status / trade_logs / positions / risk_logs 等のテーブルとインデックスを冪等的に作成する init_monitoring_db 関数を実装（読み書き専用、ビジネスロジックを持たない）。

Security / Safety / Usability
- ルックアヘッドバイアス防止: AI モジュール・レジーム判定・ニューススコアリングは datetime.today() / date.today() を参照しない設計（すべて引数の target_date を基準に処理）。
- 環境変数未設定時は明確な例外メッセージを出す（例: OpenAI API キー、必須トークン）。
- API 呼び出し失敗時はフェイルセーフ（代替値やスキップ）で継続する設計。
- ログ出力（警告・情報・デバッグ）を適切に配置して問題診断を支援。

Notes / Implementation details
- DuckDB を用いた SQL ベースの計算が多く用いられており、本番データベース（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）との整合性を前提としている。
- .env パーサーはクォートやエスケープ、コメント形式の取り扱いに対応するが、特殊ケースでは挙動に注意。
- position_sizing の将来拡張点として、銘柄別 lot_size をサポートする設計を想定（現状は全銘柄共通の lot_size を引数で指定）。
- 一部関数内に TODO / 将来の拡張に関する注記あり（例: price 欠損時のフォールバック価格、銘柄別単元管理）。

Breaking Changes
- なし（初期リリース）。

Acknowledgements
- 本リリースはコードベースからの推測により主な変更点と機能をまとめています。実際の変更履歴／コミット履歴と差異がある場合があります。