Keep a Changelog に準拠した CHANGELOG.md を日本語で作成しました。プロジェクトの現状（バージョン 0.1.0）をコードベースから推測してまとめています。

CHANGELOG.md
=============

すべての注目すべき変更をここに記載します。  
フォーマットは Keep a Changelog に従っています。  

Unreleased
----------

（開発中の変更はここに記載）

0.1.0 - 2026-03-29
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"
    - パブリックサブパッケージ候補: data, strategy, execution, monitoring（__all__）

- 環境変数/設定読み込み機能（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いに対応。
  - Settings クラスを提供し、以下の設定をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパープロパティ: is_live, is_paper, is_dev
  - 必須項目が未設定の場合は ValueError を発生させる `_require` 実装。

- AI 関連
  - kabusys.ai.news_nlp: ニュースのセンチメント解析および ai_scores への書き込み
    - 関数: score_news(conn, target_date, api_key=None)
    - ニュース収集ウィンドウ計算: calc_news_window(target_date)
    - OpenAI（gpt-4o-mini）を JSON mode で利用、バッチ処理（最大 20 銘柄／チャンク）、スコア ±1.0 にクリップ。
    - エラーハンドリング: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ再試行、その他はスキップして継続（フェイルセーフ）。
    - レスポンス検証ロジック（JSON パース補正、結果構造 validation）。
    - テスト容易性: _call_openai_api をモック差替え可能。
  - kabusys.ai.regime_detector: 市場レジーム判定（bull/neutral/bear）
    - 関数: score_regime(conn, target_date, api_key=None)
    - 指標: ETF(1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成。
    - OpenAI 呼び出しは gpt-4o-mini、リトライ・フェイルセーフの実装。
    - market_regime テーブルに対する冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - API キーは引数で注入可能（テスト容易性）。

- Data / ETL / Calendar
  - kabusys.data.pipeline:
    - ETLResult データクラスを公開（etl の集計結果・品質チェック・エラー等を保持）。
    - ETL の設計方針（差分更新、バックフィル、品質チェックの扱い）をコード化。
  - kabusys.data.calendar_management:
    - market_calendar 管理（祝日・半日取引・SQ 日の処理）および営業日判定機能を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - calendar_update_job(conn, lookahead_days=90): J-Quants からの差分取得と market_calendar 更新（バックフィル・健全性チェック付き）。
    - DB にデータがない場合は曜日ベース（土日判定）でフォールバックする堅牢な実装。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) で無限ループを防止。

- Research（因子・特徴量解析）
  - kabusys.research.factor_research:
    - calc_momentum(conn, target_date): モメンタム関連（1M/3M/6M、ma200_dev）。
    - calc_volatility(conn, target_date): ATR(20)、相対ATR、20日平均売買代金、出来高比等。
    - calc_value(conn, target_date): PER, ROE（raw_financials を参照）。
    - 設計: DuckDB の SQL ウィンドウ関数を活用して高速に計算、データ不足時は None を返す。
  - kabusys.research.feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン計算（デフォルト [1,5,21]）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関 (IC) 計算。
    - rank(values): 平均順位（同順位は平均ランク）を返すユーティリティ。
    - factor_summary(records, columns): 各ファクターの count/mean/std/min/max/median を計算。
    - 実装は標準ライブラリのみ（pandas 等に依存しない）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Known limitations / Notes
- OpenAI API まわり
  - API 呼び出しは外部ネットワーク依存のため、失敗時はスコアを 0.0 にフォールバックまたは該当コードをスキップする設計になっている（フェイルセーフ）。呼び出し回数や料金に注意。
  - API キーは関数引数で注入できるため、ユニットテストで差替え可能。
  - news_nlp と regime_detector でそれぞれ別個に _call_openai_api を実装している（モジュール間のプライベート関数共有を避ける設計）。
- データベース書き込み
  - ai_scores / market_regime などへの書き込みは冪等化（DELETE → INSERT）しトランザクションを使用。失敗時は ROLLBACK を試み例外を上位へ伝播。
  - DuckDB の executemany に関する互換性制約（空リスト渡せない）に配慮した実装になっている。
- ルックアヘッドバイアス対策
  - ほとんどの処理（news window, ma200 の計算, ETL 等）は target_date を明示的に受け取り、内部で date.today()/datetime.today() を直接参照しない設計。
- 一部のファクターはデータ不足時に None を返す（利用側でのハンドリングが必要）。
- calendar_management は market_calendar が未取得の場合に曜日ベースでフォールバックするため、完全な祝日情報がない環境での結果に注意。

Migration / Upgrade notes
- 初回リリースのため、既存バージョンからの破壊的変更はなし。
- 環境変数名・必須キー（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）を .env.example に合わせて設定する必要あり。

開発者向けメモ
- テスト容易性: OpenAI 呼び出しの差替え (_call_openai_api のモック)、および再試行待ちの _sleep_fn 注入による時間操作が可能。
- DuckDB 接続を引数に取る実装なので、インメモリ DB を用いた単体テストが容易。

今後の予定（例）
- strategy / execution / monitoring パッケージの具現化（現時点でモジュール名のみ公開）。
- AI モデルやプロンプトのチューニング機能、バッチ処理の監視・メトリクス収集、より詳細な品質チェックルールの追加。

----- 

この CHANGELOG.md はコードベースからの推測に基づいて作成しています。実際のリリースノートに含めたい追加情報（リリース日、貢献者、関連 Issue 番号、リリース手順など）があればお知らせください。