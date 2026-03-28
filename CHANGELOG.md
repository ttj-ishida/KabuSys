CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録されます。フォーマットは "Keep a Changelog" に準拠しています。

フォーマット
-----------
各リリースは以下のセクションを持ちます: Added, Changed, Fixed, Deprecated, Removed, Security。  
日付は YYYY-MM-DD 形式です。

Unreleased
----------
（現在のところなし）

0.1.0 - 2026-03-28
-----------------

Added
- 基本情報
  - 初回公開リリース (version 0.1.0)。パッケージ名: kabusys。
  - パッケージトップでのエクスポート: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定 / config (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - 自動ロードの探索は __file__ を基準にプロジェクトルート（.git または pyproject.toml）を探索するため、CWD に依存しない動作。
  - .env のパースは以下機能を備える:
    - 空行・コメント行（先頭 #）のスキップ。
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなしの場合、'#' の前に空白/タブがあればインラインコメント扱い。
  - 自動ロードの無効化環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 自動ロード順序: OS 環境変数 > .env.local（上書き） > .env（未設定キーにセット）。
  - 必須環境変数取得用 _require と Settings クラスを提供。Settings には J-Quants, kabu API, Slack, DB パス、環境判定（development/paper_trading/live）、ログレベル検証などを実装。
  - 不正な KABUSYS_ENV / LOG_LEVEL の検査ロジックを追加。

- AI モジュール (src/kabusys/ai)
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）にバッチ送信してセンチメント（-1.0〜1.0）を取得。
    - JSON Mode を使用し、API レスポンスの堅牢なバリデーションを実装（JSONパースリカバリ、results 配列チェック、コード照合、数値変換、クリッピング）。
    - バッチサイズ、記事数および文字数制限（_BATCH_SIZE=20, _MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフ（最大リトライ回数など設定）。
    - 成功した銘柄のみ ai_scores テーブルに対して DELETE → INSERT で冪等的に書き込み（部分失敗時に未取得銘柄の既存スコアを保持）。
    - ルックアヘッドバイアス回避のため datetime.today() を直接参照せず、target_date ベースでウィンドウ計算（calc_news_window）。
    - API キーは引数で注入可能（テスト容易性）。未指定時は環境変数 OPENAI_API_KEY を参照し未設定なら ValueError を送出。
  - regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定。
    - MA 計算は target_date 未満のデータのみを利用してルックアヘッドを防止。データ不足時は中立（ma200_ratio=1.0）にフォールバックして WARNING を出力。
    - マクロニュースは news_nlp.calc_news_window に基づくウィンドウからキーワードフィルタでタイトル抽出（最大 _MAX_MACRO_ARTICLES）。
    - OpenAI 呼び出しは専用の実装（news_nlp と内部関数を共有しない）で、APIエラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコア合成後に market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試み上位へ例外伝播。
    - リトライ戦略、モデル指定（gpt-4o-mini）などを定義。

- Data モジュール (src/kabusys/data)
  - calendar_management
    - JPX カレンダー管理（market_calendar 管理、営業日判定、next/prev/get_trading_days、is_sq_day）。
    - DB にデータがない場合は曜日ベースのフォールバック（平日を営業日と扱う）。
    - データが不完全（NULL 等）な場合のログ出力と一貫したフォールバックロジック。
    - 次/前営業日の探索は探索上限（_MAX_SEARCH_DAYS=60）を設けて無限ループを防止。
    - calendar_update_job: J-Quants API からの差分取得、バックフィル（直近 _BACKFILL_DAYS 再取得）、健全性チェック（未来日付が過度に大きい場合はスキップ）、fetch/save 呼び出しとエラーハンドリングを実装。
  - pipeline / etl
    - ETLResult dataclass による ETL 実行結果の構造化（取得数、保存数、品質問題リスト、エラーリスト、has_errors, has_quality_errors プロパティ、辞書化メソッド to_dict）。
    - ETL ユーティリティ: 差分更新、バックフィル、品質チェック（quality モジュールを利用）などの方針文書とユーティリティ実装（テーブル存在チェック、最大日付取得等）。
    - ETL の設計方針として id_token 注入可能、差分単位は営業日、backfill_days による後出し修正の吸収を明記。
  - etl.py は pipeline.ETLResult を再エクスポート。

- Research モジュール (src/kabusys/research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金/出来高変化率）、バリュー（PER、ROE）を計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で SQL を用いて高速に計算。欠損・データ不足時の None ハンドリング。
    - 設計上、prices_daily / raw_financials のみ参照し外部 API にはアクセスしない（リサーチ専用・安全）。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）: target_date から指定 horizon 後のリターンを一括 SQL で取得。horizons の検証（正の整数かつ <= 252）。
    - IC 計算（calc_ic）: factor_records と forward_records を code で結合し、スピアマンランク相関を計算。十分なサンプル（>=3）がない場合は None を返す。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク、丸めで ties 検出の安定化を行う。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。None 値除外。
  - research パッケージは主要関数を __all__ で公開。

- その他
  - DuckDB を中心とした内部データ操作を前提に設計（各関数は DuckDB 接続を引数に取る）。
  - OpenAI クライアントは外部注入（api_key 引数 or 環境）によってテスト容易性を確保。API 呼び出し部はユニットテストで差し替え可能な内部関数を使用するよう実装。
  - ルックアヘッドバイアス防止の設計方針が各 AI / 研究関数に徹底されている（datetime.today()/date.today() の不使用、target_date に依存）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 環境変数と .env の取り扱いで OS 環境変数を保護するため protected set を導入（自動ロード時に既存の環境変数を上書きしない等）。

Notes / 実装上の注記
- 多数の機能で「DB 書き込み時の冪等性（DELETE → INSERT、ON CONFLICT、executemany の空リスト回避等）」が考慮されているため、本番データ保全に配慮した実装になっています。
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode を利用する想定。API 変更に備え、APIError の status_code などを安全に扱う実装（getattr で保護）を行っています。
- DuckDB バージョン依存の挙動（executemany に空リストを渡せない等）に対する互換性処理を含みます。

今後の予定（例）
- strategy / execution / monitoring の実装拡充（本リリースではコアライブラリとデータ処理・研究・AI 部分に注力）。
- テストカバレッジの追加、自動化 CI、ドキュメント（使用例・API リファレンス）の充実。

--- 
以上。