CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。

[Unreleased]
-------------

なし

[0.1.0] - 2026-03-28
--------------------

初期リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点、設計上の注意点、フェイルセーフやテストのためのフックなどを以下にまとめます。

Added
- パッケージ構成
  - kabusys パッケージの基本構造を追加。公開サブパッケージとして data, research, ai, 等を __all__ に定義。
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする機能を追加。
  - 読み込み順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメント処理）。
  - 環境変数上書きロジック（override / protected）をサポートし、OS 環境変数の保護を実装。
  - Settings クラスを追加し、アプリケーション設定をプロパティ経由で取得可能に：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト付き）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（'development' / 'paper_trading' / 'live' のバリデーション）および LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev のヘルパー

- AI モジュール（kabusys.ai）
  - news_nlp:
    - score_news(conn, target_date, api_key=None) を追加。raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントをスコア化し ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で実装。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1 銘柄あたりの記事数と文字数上限（記事数: 10、文字数: 3000）でトリム。
    - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライを実装。
    - OpenAI の JSON Mode 応答を検証して、未知コードの無視、スコアの ±1.0 クリップなどの堅牢処理を実装。
    - API 呼び出し部分は _call_openai_api として抽象化し、テスト時に patch で差し替え可能。

  - regime_detector:
    - score_regime(conn, target_date, api_key=None) を追加。ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - マクロ記事の抽出（マクロキーワードリスト）、OpenAI（gpt-4o-mini）呼び出し、JSON パース、リトライ戦略を実装。
    - API 失敗時は macro_sentiment = 0.0 のフェイルセーフを採用。
    - Look-ahead バイアス対策として target_date 未満のデータのみを参照する設計。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理と営業日判定ユーティリティを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未登録の場合は曜日ベース（平日）でフォールバックする一貫したロジックを実装。
    - calendar_update_job による夜間バッチ更新を実装（J-Quants から差分取得して保存、バックフィル、健全性チェックを含む）。
  - pipeline / etl:
    - ETLResult データクラスを追加（ETL 実行結果の構造化、品質問題やエラー一覧の保持、辞書化メソッド to_dict）。
    - 差分取得や最大日付取得のためのユーティリティを実装（_get_max_date, _table_exists 等）。
    - jquants_client と quality モジュールとの統合を想定した設計。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を追加。prices_daily / raw_financials に基づくファクター計算を SQL（DuckDB）で実装。
    - 実装は lookback バッファ、欠損ハンドリング（データ不足時に None を返す）を考慮。
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターンを一括取得）、calc_ic（スピアマンランク相関による IC 計算）、factor_summary（統計サマリー）、rank（同順位は平均ランク）を実装。
  - 各種ユーティリティを __init__ で再エクスポート。

Changed
- 設計上の方針明確化:
  - すべての「日付」操作で datetime.today() / date.today() の直接参照を避け、target_date 引数ベースでの処理を徹底（ルックアヘッドバイアス防止）。
  - DB 書き込みは可能な限り「冪等」に行う（DELETE→INSERT、ON CONFLICT DO UPDATE 等を意識）。

Fixed / Robustness
- OpenAI 応答パースの堅牢化:
  - JSON モードでも前後に余計なテキストが混入するケースに対応して、文字列内の最外側の {} を抽出して JSON パースを試行するロジックを追加。
  - 不正レスポンスやパースエラー時は例外を投げずに警告ログを出してフェイルセーフ（スコア 0.0 やスキップ）を行う挙動を統一。

- DuckDB 互換性対応:
  - executemany に空リストを渡すと失敗する環境（DuckDB 0.10 系）に対応するため、空の場合は executemany を呼ばないガードを追加。

- エラー処理 / ロギング:
  - 各種 API 呼び出しでのリトライや 5xx 判定、最終的に失敗した場合のログ出力（warning / exception）を充実。
  - DB 書き込み時の例外発生に対して ROLLBACK を試み、ROLLBACK 自体が失敗した場合は警告ログを出すように実装。

Security
- OpenAI API キーの必須化:
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY が設定されていない場合に ValueError を送出する（意図しない API 呼び出しを防止）。
- 環境変数保護:
  - 自動 .env ロード時に OS 環境変数を上書きしない挙動（protected set）を実装。

Testing / Extensibility
- テスト容易性を考慮して、OpenAI への API 呼び出しを行う内部関数（_call_openai_api）をモジュール内で定義し、unittest.mock.patch 等で差し替えられるように実装。
- KABUSYS_DISABLE_AUTO_ENV_LOAD による自動環境読み込み無効化でユニットテスト時の環境汚染を回避可能。

Notes / Known limitations
- 現時点では PBR・配当利回りなど一部バリューファクターは未実装（calc_value は PER と ROE のみ）。
- AI モジュールは OpenAI (gpt-4o-mini) の JSON Mode を前提としているため、将来の API 仕様変更に注意が必要。
- calendar_update_job / ETL パイプラインは jquants_client の具体実装（fetch/save 関数）依存のため、外部 API の仕様変更があると影響を受ける可能性あり。

Acknowledgements
- 本リリースは、DuckDB を主要な分析 DB、OpenAI（gpt-4o-mini）を NLP バックエンドとして想定した実装を提供します。アプリケーションの運用・監視・さらなる拡張（例: 発注実装、より多様なファクター）は今後の開発で追加予定です。