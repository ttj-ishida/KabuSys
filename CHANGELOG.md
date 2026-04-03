CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。
このファイルにはパブリック API・実装上の重要な設計判断・フェイルセーフ動作など
ユーザーあるいはメンテナが知っておくべき事柄を記載しています。

Unreleased
----------
（現在未リリースの変更はありません）

0.1.0 - 2026-04-03
-----------------

Added
- パッケージ基礎
  - kabusys パッケージを追加。パッケージバージョンは 0.1.0。
  - パッケージ公開 API（__all__）として data, research, ai, strategy, execution, monitoring 想定のモジュール構成を定義。

- 環境設定 / config
  - 環境変数読み込みユーティリティを追加（kabusys.config.Settings）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
    - .env.local は .env を上書き（override）する挙動。OS 環境変数は保護（protected）され上書きされない。
    - 必須変数を取得する _require (未設定時は ValueError) を提供。
    - 各種設定プロパティを提供（J-Quants, kabu API, LINE, DB パス, 監視閾値, 環境/ログレベル等）。env 値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を含む。

- AI モジュール（kabusys.ai）
  - ニュース NLP（news_nlp.score_news）
    - raw_news と news_symbols を銘柄ごとに集約して LLM（gpt-4o-mini）でセンチメント評価し、結果を ai_scores テーブルへ書き込む処理を実装。
    - ニュースウィンドウは JST 基準で「前日 15:00 ～ 当日 08:30」（内部は UTC naive datetime に変換）。calc_news_window を公開。
    - 1チャンク最大 20 銘柄（_BATCH_SIZE=20）でバッチ呼び出し。1銘柄あたりの記事数上限と文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトークン肥大化を防止。
    - OpenAI JSON Mode を利用し、厳密な JSON レスポンスを期待。レスポンスの頑健なバリデーション（JSON 抽出、"results" 構造検証、コード整合性、数値検証）を実装。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ（最大 _MAX_RETRIES）。その他の API エラーやパース失敗はスキップしてフェイルセーフ（例外にせず空スコア）で継続。
    - スコアは ±1.0 でクリップ。部分失敗時にも他コードの既存スコアを保護するため DELETE（個別 executemany）→ INSERT の置換方式で書き込み（DuckDB の executemany 空リスト制約に配慮）。
    - score_news は書き込み銘柄数を返す。API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照。

  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次判定を保存。
    - ma200_ratio の算出は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。データ不足時は中立（1.0）でフォールバックし WARNING を出力。
    - マクロ記事は news_nlp.calc_news_window を使ってウィンドウを計算し、マクロキーワードでフィルタ（上限 _MAX_MACRO_ARTICLES）。
    - OpenAI 呼び出し（モデル gpt-4o-mini）には独自のラッパーを用意。API 失敗時は macro_sentiment=0.0 にフォールバックし処理継続。
    - レジームスコア合成後は label を bull/neutral/bear に分類し、market_regime へ冪等に（BEGIN/DELETE/INSERT/COMMIT）保存。DB 書き込み失敗時は ROLLBACK を試みて例外を上位に伝播。

  - 共通の実装特徴
    - OpenAI 呼び出しで発生する各種エラー（RateLimitError, APIConnectionError, APITimeoutError, APIError）の取り扱いを明示。
    - レスポンスパース失敗や想定外レスポンスは警告ログを出しフェイルセーフで代替値を使用。

- データ処理 / data
  - ETL パイプライン（data.pipeline）
    - DataPlatform の設計に沿った差分取得・保存・品質チェックのための骨組みを実装。
    - ETLResult dataclass を追加。ETL 実行メタ（取得数・保存数・quality_issues・errors）を保持し、has_errors / has_quality_errors プロパティ、辞書変換 to_dict を提供。
    - jquants_client と quality モジュールを介した差分フェッチ / 保存 / 品質チェックの処理方針を実装（差分単位・backfill・部分失敗対策など）。

  - カレンダー管理（data.calendar_management）
    - market_calendar を利用した営業日判定ユーティリティを追加。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未取得または欠損値がある場合の曜日ベースのフォールバック（週末を休場扱い）を採用し、next/prev/get の挙動が一貫するよう設計。
    - calendar_update_job を追加。J-Quants API から夜間に差分取得して market_calendar を冪等で更新。バックフィル日数や健全性（遠すぎる last_date の検出）チェックを実装。
    - 最大探索範囲（_MAX_SEARCH_DAYS）など無限ループ対策を実装。

  - ETL 公開インターフェース（data.etl）
    - pipeline.ETLResult を再エクスポート。

- 研究 / research
  - ファクター計算（research.factor_research）
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）や相対 ATR（atr_pct）、20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。必要データ不足時は None を返す。
    - calc_value: raw_financials から最新財務（report_date <= target_date）を取得し PER・ROE を算出（EPS=0 の場合は None）。PBR 等は未実装。
    - DuckDB 上の SQL + Python で計算し、(date, code) をキーとした dict のリストを返す設計。
  - 特徴量探索（research.feature_exploration）
    - calc_forward_returns: target_date から指定ホライズン後のリターンを一括取得。horizons の検証（正の整数かつ <=252）を行う。
    - calc_ic: Spearman（ランク）相関による Information Coefficient を実装。利用可能レコードが 3 件未満なら None を返す。
    - rank / factor_summary: ランク化（同順位は平均ランク）や統計サマリー（count/mean/std/min/max/median）を提供。浮動小数点の丸めで ties 対応。

Other
- モジュール公開調整
  - ai.__init__ で score_news を公開。
  - research.__init__ で主要関数（calc_momentum 等）と zscore_normalize を公開。
  - data.etl は ETLResult の薄い再エクスポートを提供。

Security / Notes
- OpenAI API キーは外部に依存するため、score_news / score_regime の呼び出し時は api_key 引数で注入するか環境変数 OPENAI_API_KEY を設定する必要があります。未設定時は ValueError を送出する仕様。
- .env の自動ロードはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化できます。
- DuckDB の executemany に空リストを渡すとエラーになる制約に配慮した実装を多数含みます（部分書き込み戦略）。

Fixed
- （初回リリースのため無し）

Changed
- （初回リリースのため無し）

Deprecated
- （初回リリースのため無し）

Removed
- （初回リリースのため無し）

Security
- （現バージョンでの既知のセキュリティ脆弱性は報告されていません。ただし外部 API キー・ネットワーク通信を伴うため運用時のキー管理・接続セキュリティは必須です。）

-- EOF --