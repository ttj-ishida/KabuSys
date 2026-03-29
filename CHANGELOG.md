# Changelog

すべての注目すべき変更点はここに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  

[Unreleased]: https://example.com/kabusys/compare/...  

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買システムのコアライブラリを提供します。主にデータ取得／ETL、カレンダー管理、ファクター計算・研究ユーティリティ、ニュースNLP・市場レジーム判定などの機能を含みます。

### Added
- パッケージ基盤
  - src/kabusys/__init__.py
    - パッケージのエントリポイント。バージョン __version__ = "0.1.0" と主要サブパッケージの公開定義を追加（data, research, ai などのサブモジュールを想定）。
- 設定・環境変数管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
    - プロジェクトルート検出機能を実装（.git または pyproject.toml を探索）。
    - .env の自動読み込みロジック（優先順位: OS環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - .env パーサーは次の特徴を持つ:
      - export KEY=val 形式対応
      - シングル/ダブルクォート内のエスケープを考慮
      - クォートなし時のインラインコメント処理（'#' の扱いは直前が空白/タブのみコメントとする）
      - 無効行・空行・コメント行をスキップ
    - _load_env_file にて OS 環境変数を保護する protected キーセットを導入し、.env.local による上書き制御をサポート。
    - Settings にて各種必須設定アクセス（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）・既定値・検証 (KABUSYS_ENV, LOG_LEVEL) を実装。
    - データベースパス設定（DUCKDB_PATH, SQLITE_PATH）を Path 型で提供。
- AI（ニュースNLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news, news_symbols を元にニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算 calc_news_window（JST ベースで前日15:00〜当日08:30）を提供。
    - API バッチ処理（1リクエスト当たり最大 _BATCH_SIZE=20 銘柄）、1銘柄あたり最大記事数 _MAX_ARTICLES_PER_STOCK=10、文字数トリム _MAX_CHARS_PER_STOCK=3000 を採用。
    - JSON Mode（response_format={"type":"json_object"}）を用い、レスポンスの厳密なバリデーションとスコアの ±1.0 クリップを実装。
    - リトライ／バックオフ: 429、ネットワーク断、タイムアウト、5xx を対象に指数バックオフでリトライ（最大 _MAX_RETRIES）。
    - レスポンスパース失敗や API 異常時はフェイルセーフで該当チャンクをスキップし、部分成功時には既存スコアを保護するためコード絞り込み（DELETE → INSERT）で書き換え。
    - テスト容易性のため OpenAI 呼び出し部分（_call_openai_api）をパッチ差し替え可能に設計。
  - src/kabusys/ai/regime_detector.py
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、市場レジーム（bull / neutral / bear）を daily 単位で判定して market_regime テーブルに冪等書き込みする機能を実装。
    - MA200 比率計算（ルックアヘッドを防ぐため target_date 未満のデータのみ使用）、マクロニュース抽出、OpenAI（gpt-4o-mini）呼び出し _score_macro、スコア合成、しきい値判定を実装。
    - API 失敗や JSON パースエラー時は macro_sentiment=0.0 にフォールバックし継続。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理、例外時には ROLLBACK を試みエラーを伝播。
- データ関連
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理ロジックを提供（market_calendar テーブル利用）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。DB にカレンダーがない場合は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job: J-Quants クライアント経由で差分取得し market_calendar を冪等保存。バックフィル、健全性チェック（未来日が過剰な場合スキップ）を実装。
    - 最大探索日数制限で無限ループを防止（_MAX_SEARCH_DAYS）。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインの結果を表す ETLResult データクラスを実装（取得・保存件数、品質問題、エラー一覧などを格納）。
    - 差分取得のための最終日取得、テーブル存在チェック、_get_max_date 等のユーティリティを実装。
    - jquants_client を使った差分取得・保存・品質チェックを行う想定（jquants_client, quality モジュールに依存）。
    - ETL 設計: backfill_days による再取得、品質チェックは検出しても ETL 自体は継続（呼び出し元がアクション決定）。
- 研究（Research）ユーティリティ
  - src/kabusys/research/factor_research.py
    - ファクター計算関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）を prices_daily から計算。データ不足時には None。
      - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
      - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS=0/欠損時は None）。
    - DuckDB を活用した SQL ベースの計算を採用し、外部 API には依存しない設計。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）で将来リターンを計算。horizons の検証（正の整数かつ <=252）を実装。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）時は None。
    - rank: 同順位は平均ランク扱いするランク関数（丸めにより ties の扱いを安定化）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出。
  - src/kabusys/research/__init__.py
    - 主要関数のエクスポート（calc_momentum 等、zscore_normalize を data.stats から再エクスポート）。
- その他
  - テスト容易性・保守性を意識した実装:
    - OpenAI 呼び出し箇所をパッチ差し替え可能に設計（ユニットテストでモック可能）。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() をスコア算出ロジックで直接参照しない設計方針を明記。
    - DuckDB のバージョン差異（executemany の空リスト制約、ANY リストバインド不安定など）に対応した実装。

### Changed
- N/A（初回リリースのため該当なし）

### Fixed
- N/A（初回リリースのため該当なし）

### Security
- 環境変数の読み込みにあたり OS 環境変数を保護する設計（.env の上書き制御）を導入し、誤った上書きによる機密情報漏洩リスクを低減。

### Notes / Migration
- OpenAI API キーは関数引数（api_key）で注入可能。指定しない場合は環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError を送出する仕様です。
- .env の自動読み込みはデフォルトで有効です。テスト等で無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を利用するため、DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）の事前準備が必要です（ETL/保存ロジックは jquants_client に依存）。
- ニューススコアやレジーム判定の結果は ±1.0 にクリップされます。LLM 呼び出し失敗時はデフォルト値（news: スコア取得失敗はスキップ / regime: macro_sentiment=0.0）にフォールバックします。
- レスポンスは JSON モードを要求しますが、まれに前後テキストが混ざるケースに備え最外側の {} を抽出してパースを試みます。

---

今後のリリースでは以下のような改善を予定しています（例）:
- jquants_client / quality モジュールの実装・統合テストの整備
- さらなるエラーハンドリング強化と監視（Slack 通知等）
- パフォーマンス最適化（大型データセットの処理、並列化）
- API モデルの抽象化と複数モデル対応

[0.1.0]: https://example.com/kabusys/releases/0.1.0