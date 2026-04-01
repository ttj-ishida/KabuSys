CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。本プロジェクトでは「Keep a Changelog」形式に準拠しています。  
バージョン番号は Semantic Versioning に従います。

Unreleased
----------
（現在なし）

[0.1.0] - 2026-04-01
--------------------
Added
- 初回リリース: KabuSys パッケージ公開 (バージョン 0.1.0)。
  - パッケージエントリポイント: src/kabusys/__init__.py にて __version__ を定義し、主要サブパッケージを __all__ で公開。
- 環境設定管理 (kabusys.config)
  - .env / .env.local からの自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export KEY=val 形式、クォート／バックスラッシュエスケープ、インラインコメント扱い等に対応する堅牢な .env パーサ実装。
  - OS 環境変数を保護する protected オプション、override フラグ、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベース / 監視閾値 / システム設定（KABUSYS_ENV, LOG_LEVEL 等）の読み取りと検証を実装。
  - 必須環境変数未設定時は明示的な ValueError を発生させるユーティリティを提供。
- AI モジュール（kabusys.ai）
  - news_nlp: raw_news を銘柄ごとに集約し OpenAI (gpt-4o-mini) の JSON Mode を用いて銘柄別センチメント（ai_scores）を算出・書き込み。
    - タイムウィンドウ計算（JST基準の前日15:00～当日08:30 を DB の UTC として扱う calc_news_window）。
    - 銘柄ごとに最大記事数・文字数でトリムし、最大バッチサイズでの API 呼び出し。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ。
    - レスポンスの堅牢な検証 (_validate_and_extract): JSON 抽出、results 検証、コード正規化（整数→文字列対応）、スコアの数値化と ±1.0 クリップ。
    - DuckDB の executemany に対する空リスト回避（互換性対策）。
  - regime_detector: ETF 1321（日経225連動型ETF）の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等書き込み。
    - ma200_ratio 計算でルックアヘッド防止（target_date 未満のデータのみ使用）、データ不足時は中立（1.0）フォールバック。
    - マクロニュース抽出（マクロキーワードによるフィルタ、最大記事数制限）。
    - OpenAI 呼び出しの専用実装、API エラー時のリトライ、最終的なフェイルセーフとして macro_sentiment=0.0 を採用。
    - レジームスコア合成、ラベル付与、BEGIN/DELETE/INSERT/COMMIT による冪等書き込みと適切な ROLLBACK 処理（ROLLBACK 失敗時は警告ログ）。
- Data モジュール（kabusys.data）
  - calendar_management: JPX カレンダー管理と営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得の場合は曜日ベース（土日非営業）でのフォールバック。
    - calendar_update_job: J-Quants から差分取得→冪等保存（バックフィル、健全性チェックあり）。
  - pipeline / etl:
    - ETLResult データクラスを定義（ETL 実行結果・品質問題・エラーの集約）。
    - pipeline モジュールの ETLResult を data.etl 経由で再エクスポート。
    - 差分更新／バックフィル／品質チェックの設計方針を反映（詳細は pipeline.py の実装）。
- Research モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20日）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB の SQL／ウィンドウ関数で計算。
    - データ不足に対する None フォールバック、結果は (date, code) キーの辞書リストで返却。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic：Spearman ランク相関）、rank、factor_summary（count/mean/std/min/max/median）を提供。
  - data.stats の zscore_normalize を再エクスポート。
- 設計方針・運用的配慮
  - 全てのレポート・スコアリング関数は datetime.today()/date.today() を直接参照しない（明示的な target_date を必須とすることでルックアヘッドバイアスを防止）。
  - DB 書き込みは可能な限り冪等（DELETE→INSERT や ON CONFLICT を想定）で実装。
  - LLM レスポンスの不確実性に対しては失敗時スキップやデフォルト値で継続するフェイルセーフを採用。

Fixed / Improved
- .env パーサの強化: 引用符付き値のバックスラッシュエスケープ処理、インラインコメントの取り扱いを改善。
- 環境値上書きロジックに protected set を導入し、OS 環境変数の保護を実現。
- OpenAI からの JSON レスポンスが前後に余計なテキストを含むケースに対し、最外側の {} を抽出して復元する処理を追加（news_nlp）。
- DuckDB 操作の堅牢化:
  - executemany に空リストを渡さないようガード（DuckDB 互換性対策）。
  - トランザクションでの例外時に ROLLBACK を試み、ROLLBACK 自体が失敗した場合は警告ログ出力。
- API 呼び出しにおける細かなリトライ条件の調整（RateLimit / 接続断 / タイムアウト / 5xx をリトライ対象、その他はスキップ・ログ出力）。

Security
- 必須の外部キー（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を Settings 経由で明示的に要求。未設定時は ValueError を発生させ処理者に通知。

Notes / Migration
- 本ライブラリの主要関数は明示的な DuckDB 接続と target_date を受け取ります。呼び出し側は以下のテーブル（最低限）を用意してください:
  - prices_daily, raw_news, ai_scores, news_symbols, market_regime, market_calendar, raw_financials, 等。
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode を用います。API キーは OPENAI_API_KEY または各関数の api_key 引数で指定してください。
- 自動 .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- レスポンスやスコアは各モジュールでクリップ・検証されるため、外部から受け取る数値は ±1.0 の範囲に正規化されます。

Acknowledgements
- 初期実装では外部 API（J-Quants, OpenAI）や DuckDB に依存する箇所が多数あります。運用環境では各種シークレット／API エンドポイント設定と DB スキーマ準備を事前に行ってください。

---

（この CHANGELOG はコードベースの実装内容から推測して記述しています。実際のコミット履歴やリリースノートが存在する場合はそれに合わせて更新してください。）