# Changelog

すべての注目すべき変更を記録します。このプロジェクトは Keep a Changelog の方針に従って管理しています。

現在のバージョン: 0.1.0（初回リリース）

## [Unreleased]
- なし

## [0.1.0] - 2026-03-28
Initial release — KabuSys の初期実装を公開。

### Added
- パッケージ基盤
  - src/kabusys/__init__.py によるパッケージ公開（version=0.1.0）。公開サブパッケージ: data, strategy, execution, monitoring。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化のサポート（テスト向け）。
  - export 形式やクォート、エスケープ、インラインコメントなどに対応する堅牢な .env パーサ実装。
  - 環境変数上書きルール（OS 環境変数を保護する protected 機構）。
  - Settings クラス経由で各種設定を取得（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等）。
  - 必須環境変数未設定時に分かりやすいエラーメッセージを出す _require()。

- AI 関連（src/kabusys/ai/*）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news を銘柄毎に集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window() で提供。
    - 1 銘柄あたりの最大記事数・文字数制限によるトークン肥大化対策（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - バッチ処理（_BATCH_SIZE）、JSON mode を利用した厳密なレスポンスバリデーション、スコアクリップ（±1.0）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ。失敗時は該当チャンクはスキップし続行（フェイルセーフ）。
    - テスト容易化のため _call_openai_api の差し替え（mock/padch）が可能。
    - DuckDB の executemany に関する空リスト回避ロジックを追加（互換性対策）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照し、計算結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出しは retries/backoff を実装、API 失敗時は macro_sentiment=0.0 にフォールバック。
    - LLM に対するシステムプロンプトや JSON パースの堅牢化を実装。
    - テスト用に _call_openai_api を差し替え可能。

- Research（src/kabusys/research/*）
  - factor_research.py
    - モメンタム（約1/3/6ヶ月リターン）、200 日 MA 乖離、ATR ベースのボラティリティ、流動性指標、バリューファクター（PER/ROE）を DuckDB 上の SQL で算出する関数群を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時に None を返すなど堅牢な欠損処理。
  - feature_exploration.py
    - 将来リターン算出（calc_forward_returns）、スピアマンランク相関による IC 計算（calc_ic）、ランキング変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas など外部依存なしでの純粋 Python 実装。
  - research パッケージの __init__ で必要関数を再エクスポート。

- Data プラットフォーム（src/kabusys/data/*）
  - calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 値優先、未登録日は曜日ベース（週末除外）でフォールバックする一貫したロジック。
    - calendar_update_job による J-Quants からの差分取得/バックフィル/保存処理（健全性チェック・バックフィル日数・lookahead の実装）。
  - pipeline.py / etl.py
    - ETL パイプライン用の ETLResult dataclass（実行結果の集約、品質問題の格納、エラーフラグ）。
    - 差分取得、backfill、品質チェック（quality モジュール連携）を想定したユーティリティ。
    - DuckDB 用テーブル存在チェックや最大日付取得ユーティリティを含む。

- 一貫した設計方針
  - ルックアヘッドバイアス回避: 日付依存処理で datetime.today()/date.today() を直接使用しない設計（score_news / score_regime などでは target_date を明示）。
  - DB 書き込みは可能な限り冪等操作（DELETE→INSERT 等）で実装。例外時は COMMIT/ROLLBACK 処理。
  - ロギングを多用し、失敗時には例外を投げる／投げないを場合に応じて使い分け。LLM/API エラーは多くの場合フォールバックして継続する（可用性優先）。
  - テスト容易性の配慮（内部 API 呼び出しの差し替えポイント、環境ロードの無効化フラグなど）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- DuckDB の executemany に空リストを渡すと問題になる点に対してのガードを追加（news_nlp.score_news の書き込み処理など）。
- OpenAI レスポンスの JSON パースに関して、JSON mode でも余計な前後テキストが混ざるケースに対応する復元処理を追加（news_nlp, regime_detector）。

### Security
- 環境変数に依存する機密情報（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）は Settings._require により明示的に必須化。README/.env.example に従って安全に設定すること。
- .env 自動ロードはプロジェクトルートを基準に行い、OS 環境変数はデフォルトで保護（上書きされない）。

### Known issues / Limitations
- バリューファクターの PBR・配当利回りは未実装（calc_value に注記あり）。
- ai_score と sentiment_score は現フェーズでは同値で保存される（将来的な分離可能）。
- OpenAI SDK の将来的な API 仕様変更（例: 例外クラスや status_code の仕様）に対しては一部 try/except で互換性確保を図っているが、重大な変更があれば更新が必要。
- calendar_update_job / ETL の外部依存（jquants_client, quality モジュール）の実装に依存するため、運用環境ではそれらクライアントの設定が必要。

---

注: この CHANGELOG はソースコードの実装内容から推測して作成した初期リリースの変更履歴です。将来のリリースでは実際の差分に合わせて更新してください。