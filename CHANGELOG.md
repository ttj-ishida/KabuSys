Keep a Changelog
=================

すべての重要な変更はこのファイルに記載します。フォーマットは "Keep a Changelog" に準拠します。

履歴
----

### 0.1.0 - 2026-03-28 (初版)

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ: src/kabusys/__init__.py にバージョンとパブリック API を定義。

- 環境設定 / 初期化
  - 環境変数自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml で探索して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。
    - シェルスタイルの行（export KEY=val）、クォートとエスケープ、行内コメント（'#'）の取り扱いに対応するパーサ実装。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベースパス / システム設定（KABUSYS_ENV, LOG_LEVEL）等のプロパティ経由で安全に取得。
    - 必須設定未提供時は ValueError を発生させる _require 関数。

- AI（自然言語処理）機能
  - ニュースセンチメント分析（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols をソースに、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）に JSON モードでバッチ評価し ai_scores テーブルへ書き込む score_news 関数を提供。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を calc_news_window で明確化。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、1 銘柄あたりの記事数/文字数上限によるトリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳密なバリデーションを実装。
    - レスポンスの差し戻し（前後余分テキスト）に対する復元処理、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護するための部分置換（DELETE → INSERT）。
    - テスト用に _call_openai_api を patch で差し替え可能に設計。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロニュース抽出（キーワードフィルタ）、OpenAI 呼び出し（gpt-4o-mini）による JSON 出力パース、API エラー発生時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。

- データ処理 / ETL / カレンダー
  - ETL 結果型（src/kabusys/data/pipeline.py）
    - ETL 実行結果を表す dataclass ETLResult を公開。取得/保存件数、品質問題、エラー一覧などを保持し to_dict で整形可能。
    - 差分取得、バックフィル、品質チェックに関する設計方針がコード上で明示（_MIN_DATA_DATE / _DEFAULT_BACKFILL_DAYS 等）。

  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを基に営業時間判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダーがない場合は曜日ベース（土日休み）でフォールバック。
    - calendar_update_job により J-Quants API からの差分取得 → 冪等保存（jq.fetch_market_calendar / jq.save_market_calendar を使用）を行う。バックフィルと健全性チェックを実装。

  - ETL ユーティリティの公開（src/kabusys/data/etl.py）
    - pipeline.ETLResult を再エクスポート。

  - DuckDB ユーティリティ
    - テーブル存在確認や最大日付取得などの内部ユーティリティを実装（pipeline と calendar_management 内）。

- リサーチ / ファクター計算
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン・200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）を計算する関数 calc_momentum, calc_volatility, calc_value を実装。
    - SQL を活用して DuckDB 上で高速に計算する設計。データ不足時は None を返す設計で安全性確保。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（任意のホライズン）、IC（Information Coefficient）計算 calc_ic、ランク変換 rank、カラム統計 factor_summary を実装。
    - 外部依存を持たず標準ライブラリのみで統計処理実装。

- モジュール公開整理
  - ai, research パッケージの __init__ に主要関数をエクスポート（例: kabusys.ai.score_news / kabusys.ai.score_regime, kabusys.research.*）。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- 新規リリースのため該当なし。

注意事項（利用者向け）
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings の各プロパティ参照）。
  - OpenAI API キーは score_news / score_regime の api_key 引数または環境変数 OPENAI_API_KEY で指定する必要あり。未設定時は ValueError を送出。
  - 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- DB スキーマ（想定しているテーブル）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など。各モジュールはこれらの存在と列を前提に SQL を実行します。

- ルックアヘッドバイアス対策:
  - ニュース/レジーム/ファクター計算はすべて target_date 未満または window の排他条件等で将来情報を参照しないよう配慮されています。

- フェイルセーフ挙動:
  - 外部 API（OpenAI, J-Quants）呼び出しにおいては、429 / ネットワーク断 / タイムアウト / 5xx に対するリトライや、最終的に失敗した場合の代替値（例: macro_sentiment=0.0）で処理継続する設計です。

既知の制約・今後の改善候補
- news_nlp と regime_detector でそれぞれ独立した _call_openai_api 実装を持つ（意図的）。将来的に共通化することで重複削減が可能。
- 一部処理（例: ETL の完全なワークフロー、jquants_client の具象実装）はこの差分からは参照のみで、外部モジュール実装に依存します。
- calendar_management や pipeline の一部は最大探索日数等の定数を調整することで柔軟性が向上します。

ライセンス・貢献
- 本リリースは初期公開版です。貢献方法や詳細な設計ドキュメントはリポジトリ内の README / docs を参照してください。