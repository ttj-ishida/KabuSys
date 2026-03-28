CHANGELOG
=========

このプロジェクトは Keep a Changelog のフォーマットに準拠しています。
セマンティックバージョニングを使用しています。  

[Unreleased]
------------

（現時点のリポジトリ状態は初期リリース v0.1.0 に対応しています。今後の変更はここに記載します。）

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初版を追加（kabusys v0.1.0）。
  - パッケージエントリポイント: src/kabusys/__init__.py にてバージョンと公開APIを定義。
- 環境設定管理モジュール（kabusys.config）を追加。
  - .env / .env.local の自動読み込み機能（プロジェクトルート判定：.git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env のパース改善：
    - コメント行・空行の無視、export KEY=val 形式のサポート。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理対応。
    - インラインコメント（クォートなしの場合は直前が空白/タブの '#' をコメントと認識）への対応。
  - protected な OS 環境変数を保持するオプション（override の挙動制御）。
  - Settings クラスを公開し、各種必須／デフォルト設定をプロパティで取得可能（J-Quants、kabu API、Slack、DB パス、環境・ログレベル判定など）。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を実装。
- AI モジュールを追加（kabusys.ai）。
  - news_nlp（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_scores）を生成・書き込み。
    - タイムウィンドウ計算（JST基準の前日15:00〜当日08:30）と DuckDB を前提としたクエリ。
    - バッチサイズ・文字数・記事数の上限制御（過大入力対策）。
    - JSON Mode を使ったレスポンス検証と復元ロジック（前後余計なテキストが混入した場合に最外の {} を抽出）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフによるリトライ実装。
    - スコアの数値検証と ±1.0 クリッピング。
    - DuckDB の executemany 空リスト制約を考慮した安全な書き込み（DELETE → INSERT の差し替え戦略）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（内部 _call_openai_api が差し替え対象）。
  - regime_detector（kabusys.ai.regime_detector）
    - ETF コード 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、news_nlp によるマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - DuckDB の prices_daily / raw_news を参照し、ルックアヘッドバイアス防止のため target_date 未満のデータのみ使用。
    - OpenAI 呼び出しでのリトライ、障害時のフェイルセーフ（macro_sentiment=0.0）実装。
    - 計算結果を market_regime テーブルへ冪等に書き込む（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト用に _call_openai_api の差し替えを想定。
- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離（データ不足時は None）。
    - calc_volatility: 20日 ATR、ATR比率、平均売買代金、出来高比率など。
    - calc_value: raw_financials から財務指標（PER, ROE）を結合。
    - DuckDB ベースの SQL 実装（外部APIや発注処理に依存しない）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン算出。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。
    - factor_summary: カラムごとの count/mean/std/min/max/median の集計。
    - rank: 同順位は平均ランクを返す実装（丸めによる ties 対応）。
  - zscore_normalize を data.stats から再エクスポート。
- Data（kabusys.data）
  - calendar_management
    - market_calendar テーブルを用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - カレンダーデータがない場合の曜日ベースフォールバック（週末を非営業日扱い）。
    - next/prev_trading_day の最大探索日数制限（_MAX_SEARCH_DAYS）や健全性チェック。
    - calendar_update_job：J-Quants API から差分取得して market_calendar を冪等的に更新。バックフィル・サニティチェックを備える。
  - pipeline / ETLResult
    - ETL パイプライン向けの ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラーの収集・変換機能）。
    - _get_max_date, _table_exists などのユーティリティ実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。
- DuckDB 互換性・実装注意点
  - DuckDB 0.10 における executemany の空リスト不可を考慮してコード内でガードを追加。
  - DuckDB からの日付型を安全に date オブジェクトに変換する _to_date ユーティリティ。

Changed
- （初版リリースのため該当なし）

Fixed
- .env パーサーにおけるクォート内エスケープや export プレフィックスの扱いを実装（実用上のパース精度を向上）。

Security
- OpenAI/API キー取り扱い
  - news_nlp / regime_detector / その他の AI API 呼び出しは OPENAI_API_KEY を参照。キー未設定時は ValueError を投げて明示的に失敗させる。
- 環境変数の自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト時に無効化可能。

Notes / 注意事項
- ルックアヘッドバイアス対策として、AI モジュール・研究モジュールは内部で datetime.today()/date.today() を参照せず、必ず caller が渡す target_date を基準に処理します。
- OpenAI への実際の API 呼び出しは gpt-4o-mini と JSON Mode を使う設計だが、テスト容易性のため _call_openai_api をモックすることを想定しています。
- locale / タイムゾーン扱いはすべて naive な UTC/日付オブジェクトを前提にしており、JST↔UTC の変換は明示的に計算しています（news window など）。
- DuckDB の戻り値型がバージョンや環境で変わる可能性があるため、日付や status_code の取得は guard（getattr, isinstance）を使って安全に処理しています。
- 部分書き込み戦略（コードを指定して DELETE → INSERT）により、部分失敗時に既存データを不必要に消さないようにしています。

Known issues
- OpenAI API のレスポンス仕様変更やモデル変更があった場合、JSON Mode のパースロジックの修正が必要になる可能性があります。
- DuckDB のバージョン差異により executemany 等の挙動が変わる可能性があるため、使用する DuckDB バージョンでの動作確認を推奨します。

[0.1.0]: https://example.com/kabusys/releases/tag/v0.1.0  (リンクは適宜更新してください)