CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
本ファイルは「Keep a Changelog」規約に準拠しています。  
リリース日付は該当コミットから推測して記載しています。

[Unreleased]
-------------

v0.1.0 (2026-03-31)
-------------------

Added
- パッケージの初期公開。
- 基本モジュール構成を追加:
  - kabusys.config
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export prefix、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱いをサポート。
    - 環境変数必須チェック用 _require と Settings クラスを提供。主な設定項目:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development/paper_trading/live の検証）
      - LOG_LEVEL（DEBUG/INFO/... の検証）
    - Settings インスタンスをモジュールレベルで公開。

  - kabusys.ai
    - news_nlp モジュール
      - raw_news / news_symbols を基に、指定ウィンドウ（前日15:00 JST ～ 当日08:30 JST）内の記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む。
      - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの最大記事数・最大文字数トリム、レスポンス検証ロジックを実装。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
      - API エラーやパース失敗は警告ロギングの上で当該チャンクをスキップし、処理全体は継続する（フェイルセーフ）。
      - テスト容易性のため _call_openai_api を patch 可能にしている。
      - calc_news_window 関数を公開。

    - regime_detector モジュール
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込みする機能を実装。
      - マクロニュース抽出はキーワードベース（日本語／英語キーワード群）でフィルタし、OpenAI に JSON 応答を要求。レスポンスのリトライ・フォールバック（失敗時 macro_sentiment=0.0）を実装。
      - 呼び出し時に api_key を注入可能（なければ環境変数 OPENAI_API_KEY を参照）。
      - ルックアヘッドバイアス防止のため、内部で date.today()/datetime.today() を参照しない設計。

  - kabusys.research
    - factor_research モジュール
      - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）等を DuckDB の prices_daily / raw_financials を使って計算する関数を提供:
        - calc_momentum, calc_volatility, calc_value
      - 実装は SQL（DuckDB）と最小限の Python ロジックで完結し、本番口座や発注 API を参照しない。

    - feature_exploration モジュール
      - 将来リターン計算 calc_forward_returns（複数ホライズン対応、引数でホライズン指定、検証あり）。
      - IC（Spearman の ρ）計算 calc_ic（rank を内部で計算し ties に対応）。
      - rank ユーティリティ（同順位は平均ランク）。
      - factor_summary（count/mean/std/min/max/median）を提供。
      - 外部ライブラリ非依存（標準ライブラリのみ）で実装。

  - kabusys.data
    - calendar_management モジュール
      - JPX カレンダーの管理用ロジックを実装（market_calendar テーブルの使用を前提）。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。DB 登録値を優先し、未登録日は曜日ベース（土日を非営業日）でフォールバック。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
      - 探索範囲制限（最大探索日数）、日付型の一貫性保持などを実装。

    - pipeline / etl モジュール
      - ETLResult データクラスを公開（ターゲット日、取得/保存件数、品質問題リスト、エラーリスト等）。
      - 差分更新、backfill、品質チェックのためのユーティリティ関数を実装（jquants_client 経由の保存処理・品質チェック呼び出しを想定）。
      - _get_max_date / _table_exists 等の内部ユーティリティを実装。

  - 公開インターフェース・エクスポート
    - kabusys.__init__ にてバージョン __version__ = "0.1.0" を設定し、主要パッケージ（data, strategy, execution, monitoring）を __all__ でエクスポートの骨格を用意。
    - kabusys.data.etl で ETLResult を再エクスポート。
    - kabusys.ai.__init__ で score_news をエクスポート。
    - kabusys.research.__init__ で主要なリサーチ関数を再エクスポート。

Security
- OpenAI API キーや各種シークレットは環境変数で管理する想定。設定チェックは Settings で行い、未設定時は明確な例外を送出。

Notes / 設計上の注意点
- ルックアヘッドバイアス防止のため、スコアリング関連関数は内部で現在日時を参照しない。すべて呼び出し側から target_date を明示的に渡す設計。
- OpenAI 呼び出しは JSON Mode を使用し厳密な JSON 応答を期待するが、実装側でパース失敗ケース（前後の余計なテキスト等）にも耐性を持たせている。
- API 呼び出し部分はテスト容易性を考慮して patch 可能（_call_openai_api をモジュールごとに用意）。
- DB 書き込みは冪等性を意識（DELETE→INSERT のパターンや BEGIN/COMMIT/ROLLBACK の使用）しており、部分失敗時に既存の有効データを保護する実装を行っている（例: ai_scores の個別 DELETE）。
- エラー発生時は例外投げっぱなしにせずログに記録して処理を継続する箇所がある（フェイルセーフ設計）。ただし、DB 書き込み失敗時は例外を伝播させる箇所もある。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- 初版のため該当なし。環境変数管理と外部キー（API キー）取り扱いは注意。

その他
- テストを行う際は KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動 .env ロードを無効化するとテスト環境構築が容易です。
- DuckDB のバージョン依存（executemany の空リスト扱いなど）を考慮したガードを実装しています。

もしこの CHANGELOG に追記すべき差分（実際のコミットの意図や公開時のリリースノートに必要な情報）があれば、該当箇所（例: API 変更、破壊的変更、追加の環境変数等）を教えてください。必要に応じて日付やリリースノートの文言を調整します。