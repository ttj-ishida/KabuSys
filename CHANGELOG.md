CHANGELOG
=========

すべての著しい変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

注: コードベースから推測して作成した初版リリースノートです（実装の意図・設計方針・既知の挙動を含みます）。

Unreleased
----------

（なし）

0.1.0 - 2026-04-04
------------------

Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。
  - パッケージの公開 API に data/strategy/execution/monitoring を想定（`__all__` 宣言）。

- 環境変数・設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出（CWD非依存）。
    - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサーの強化:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、行内コメント（空白直前の `#` をコメントと判定）などに対応。
    - ファイル読み込み失敗時は警告を発行して継続（例外を投げない）。
    - `.env.local` は既存 OS 環境変数を保護しつつ上書き可能（protected set の導入）。
  - Settings クラスを提供（`settings` インスタンスを公開）:
    - J-Quants / kabuステーション / LINE / データベースパス等の設定プロパティ。
    - デフォルト値の定義（例: KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PID/KILL フラグパス、閾値など）。
    - 環境値検証: KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL（DEBUG..CRITICAL）検証。
    - 必須変数取得時に未設定なら明示的な ValueError を送出する `_require` を実装。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄毎にニュースを結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - 時間ウィンドウ計算ユーティリティ `calc_news_window(target_date)` を提供（JST 基準を UTC naive datetime に変換）。
    - バッチサイズ、記事上限、文字数上限、リトライ（指数バックオフ）を含む堅牢な実装。
    - OpenAI の JSON Mode を想定し、レスポンスのバリデーション（JSON 抽出、results 配列、code/score の検証）を行う。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込む。部分失敗時に他コードの既存スコアを保護する設計。
    - テスト容易性: OpenAI 呼び出しを差し替えるための内部 `_call_openai_api` を分離（unittest.mock.patch が可能）。
    - API エラー時はスキップして継続（フェイルセーフ）、取得銘柄数を返す。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる raw_news フィルタ、最大記事数制限、OpenAI（gpt-4o-mini）呼び出し、リトライ、JSON パース、スコア合成、クリッピングを実装。
    - 結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を上位へ伝播。
    - API 失敗やパースエラー時は macro_sentiment を 0.0 として続行（フェイルセーフ）。
    - 「ルックアヘッドバイアス」を避ける設計（内部で datetime.today()/date.today() を参照しない、prices_daily クエリで date < target_date を明示）。

- Data / ETL / カレンダー / パイプライン（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを定義し、取得/保存件数・品質問題・エラー情報を集約。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）を想定した設計。
    - DuckDB に対する存在確認ユーティリティや最大日付取得ユーティリティを提供（互換性考慮）。
    - DuckDB の executemany の挙動（空リスト不可）を考慮した安全な書き込みロジック。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを扱うユーティリティ群を提供:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - market_calendar テーブルが存在しない場合は曜日ベースのフォールバック（週末非営業日）を採用。
    - DB 登録値優先、未登録日は曜日フォールバックで一貫性のある結果を返す設計。
    - 夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants API 経由で差分取得、バックフィル、健全性チェック、save を呼び出して保存）。
    - 最大探索日数・バックフィル・先読み（lookahead）等の安全パラメータを持つ。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム、ボラティリティ、バリュー関連のファクター計算関数を提供:
      - calc_momentum: mom_1m/3m/6m、ma200_dev（200日 MA 乖離）など。データ不足時は None を返す。
      - calc_volatility: 20 日 ATR（平均 true range）、相対 ATR、20 日平均売買代金、出来高比率など。
      - calc_value: PER（EPS が 0/欠損なら None）、ROE（raw_financials から最新値を参照）。
    - DuckDB SQL を活用した実装（外部 API 呼び出し無し）。結果は (date, code) キーの dict リストとして返す。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン引数の検証あり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。データが不足する場合は None を返す。
    - rank: 同順位は平均ランクを付与するランク付けユーティリティ（丸めを用いた ties 安全対策）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - 研究用ユーティリティの公開（`__all__` に主要関数を列挙）。

Other
- ロギング/エラーハンドリング
  - 各種モジュールで状況に応じて logger.warning/ info/ exception を出力。
  - OpenAI や外部 API の失敗に対しては適切な警告ログを出してフォールバックするポリシーを採用。
- DuckDB 互換性考慮
  - executemany に空リストを渡せない問題や、リスト型バインドの不安定性を回避する実装上の工夫がある。

Security
- 環境変数読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。.env.local などで OS 変数を意図せず上書きしない設計。
- 機密情報（例: KABU_API_PASSWORD, JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY）は Settings を通して必須チェックを行う（未設定時は ValueError）。

Breaking Changes
- 初回リリースのため互換性の変更履歴はなし。

Notes / 運用上の注意
- OpenAI API を利用する機能（news_nlp, regime_detector）は API キーが必須。関数呼び出し時に引数で渡すか環境変数 OPENAI_API_KEY を設定する必要がある。
- LLM 呼び出し失敗時はスコアにデフォルト値（0.0）を用いるため、外部 API の不調がシステム全体の例外を引き起こすことは基本的にないが、結果の欠損や中立化が発生する点に留意。
- DuckDB を利用した SQL 処理では日付型・ROW_NUMBER/ウィンドウ関数等を多用しているため、DuckDB のバージョン互換性に注意。
- テスト時には ai モジュールの内部 `_call_openai_api` をパッチすることで外部通信を行わずに動作確認が可能。

Acknowledgements / References
- 設計方針や処理フローの多くはコード内の docstring / コメントに明示されています。テスト・運用時にはそちらも参照してください。