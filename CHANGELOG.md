# Changelog

すべての変更は Keep a Changelog のフォーマットに従います。  
このファイルでは主にコードベースの初期リリース（v0.1.0）の機能追加・設計方針・重要実装ポイントをまとめています。

全般的な注意
- 本リリースはパッケージメタ情報に基づく初期公開版です（バージョン: 0.1.0）。
- SQLite / DuckDB を用いたオンメモリ/ローカル分析基盤、OpenAI（gpt-4o-mini）を利用したニュースNLP・レジーム判定、ファクター計算・研究用ユーティリティ、JPXカレンダー管理、ETLパイプライン等を含みます。
- 多くの箇所で「ルックアヘッドバイアス防止」「フェイルセーフ」「冪等性」「DuckDB 互換性」を設計指針として採用しています。

## [0.1.0] - 2026-03-31

### Added
- 基本パッケージ初期構成
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - 公開サブモジュール: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定読み込み / Settings（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサの実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理など。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level）等のプロパティを定義。環境値のバリデーション（有効値セット）を実装。
  - 必須環境変数未設定時は ValueError を送出するヘルパー _require を実装。

- ニュースNLP（AI）機能（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードで一括センチメント評価を行う score_news(conn, target_date, api_key=None) を実装。
  - ニュース収集ウィンドウ計算 calc_news_window(target_date) を実装（JST基準: 前日15:00〜当日08:30、DB用にUTC naive datetimeで返却）。
  - バッチサイズ（1回のAPIで最大20銘柄）、1銘柄当たりの記事上限・文字数上限（トリム）などトークン肥大化対策を実装。
  - レスポンス検証ロジック（JSON パース、results リストの構造チェック、コード正規化、数値チェック、±1.0 でクリップ）を実装。
  - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。致命的でないエラー時はスキップして継続（フェイルセーフ）。
  - DuckDB への書き込みは冪等（DELETE → INSERT）で実行。部分失敗時に既存データを保護する実装（対象コードに限定して削除→挿入）。
  - テスト容易性のため、_call_openai_api を patch 可能にし、news_nlp モジュール内で独立した実装を持たせる設計。

- 市場レジーム判定（AI）機能（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュース由来のLLMセンチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定する score_regime(conn, target_date, api_key=None) を実装。
  - MA200 乖離計算、マクロ用キーワードによる raw_news フィルタリング、OpenAI 呼び出し、レジームスコア合成、market_regime テーブルへの冪等書き込みを実装。
  - マクロ記事がない場合やAPI失敗時は macro_sentiment=0.0 にフォールバック（APIエラーで例外を上げず継続）。
  - OpenAI 呼び出しは独立実装（news_nlp と共有しない）で、リトライ戦略・HTTPエラー区別・ログ出力を行う。
  - 設計上、内部ロジックは datetime.today()/date.today() を参照しない（ルックアヘッドバイアス防止）。

- 研究（Research）モジュール（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）:
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、ma200_dev（200日MA乖離）を計算。データ不足時は None を返す設計。
    - calc_volatility(conn, target_date): atr_20、atr_pct、avg_turnover、volume_ratio 等のボラティリティ/流動性指標を計算。true_range の NULL 伝播制御を行い欠損制御。
    - calc_value(conn, target_date): raw_financials から直近財務データを取得して PER / ROE を計算（EPS=0/欠損時は None）。
    - DuckDB クエリ中心で外部APIにはアクセスせず、(date, code) をキーとした辞書リストを返す。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）:
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（LEAD を使用）を一回のクエリで取得。horizons の入力チェックあり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を実装。データ不足や等分散のケースに対応。
    - rank(values): 同順位は平均ランクで扱うランク関数（丸めで ties 検出安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出する統計サマリー関数。
  - research パッケージの __all__ と再エクスポート（zscore_normalize など）を提供。

- データ関連（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）:
    - JPX カレンダー（market_calendar テーブル）を扱うユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック。探索上限 _MAX_SEARCH_DAYS の設定で無限ループを防止。
    - calendar_update_job(conn, lookahead_days): J-Quants API からカレンダー差分取得→冪等保存。バックフィル・健全性チェックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py と etl.py）:
    - ETLResult dataclass を定義（取得数・保存数・品質問題・エラー等を集約）。
    - 差分更新・バックフィル方針・品質チェック統合を想定した設計。jquants_client と quality モジュールを組み合わせる想定。
    - _get_max_date 等のユーティリティを実装してテーブル存在チェックや最大日付の取得を提供。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。
  - DuckDB を主要なローカル分析 DB として利用（prices_daily, raw_news, ai_scores, market_regime, market_calendar, news_symbols, raw_financials 等のテーブル名称を想定）。

### Changed
- （初期リリースのため過去変更はなし）設計上の注意点や実装方針をドキュメント内コメントとしてコードに反映：
  - 「ルックアヘッドバイアス防止」の徹底（date.today()/datetime.today() を直接参照しない）。
  - DuckDB のバージョン差分（executemany の空リスト問題等）への互換対策を実装。
  - OpenAI API の呼び出しに対するリトライ/フォールバック方針を明確化（マクロ評価 / ニュース評価ともに異常時はスコア 0 やスキップで継続）。

### Fixed
- （初期リリースのため既知のバグ修正履歴なし）
- 実装上のロバスト性向上:
  - DB 書き込み失敗時に ROLLBACK を試み、ROLLBACK 自体が失敗した場合に警告を出す処理を追加（冪等性保護）。
  - OpenAI レスポンスパース失敗やキー欠落時には例外を上位へ送出せず、ログ出力の上でフェールセーフ（0.0 もしくは処理スキップ）にフォールバック。

### Security
- 本バージョンでの外部APIキー取扱い:
  - OpenAI API キーは引数で注入可能（テスト容易化）であり、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示的に失敗する。
  - .env ファイルの読み込みに失敗した場合は warnings.warn を出すが、致命的エラーにはしない（安全上の配慮）。
  - 環境変数上書き時には OS 環境変数を protected として扱う仕組みを導入。

### Notable implementation / design notes
- OpenAI に関する共通事項:
  - 使用モデル: gpt-4o-mini（news_nlp と regime_detector の双方で使用）。
  - JSON mode を用いて厳密な JSON を期待するプロンプト設計（前後ノイズが混入した際の復元ロジックも実装）。
  - retry/backoff ロジックや 5xx の判別、RateLimit の扱いを明示。
- データ整合性:
  - DuckDB を前提とするクエリ設計（ウィンドウ関数、LEAD/LAG、ROW_NUMBER を多用）。
  - ETL と calendar_update_job は冪等保存（ON CONFLICT / DELETE→INSERT）を意図した実装。
- テストを想定した設計:
  - _call_openai_api をモジュールローカルで定義し、unittest.mock.patch により API 呼び出しを差し替え可能にしている。
  - 環境変数自動ロードの無効化フラグによりテスト環境での副作用を抑制可能。

今後の予定（想定）
- strategy / execution / monitoring の実装・テスト・ドキュメント拡充。
- ETL の詳細実装（jquants_client, quality 連携）の追加と運用・監査ロギング強化。
- CI / CD 用のテスト群（特に OpenAI 呼び出しのモック化）とパッケージリリースフローの確立。

---

（注）この CHANGELOG は提供されたコードベースの内容を基に推測して作成しています。実際のリリースノートに組み込む際は、リリース日や変更の粒度、追加の既知の問題点などをプロジェクトのポリシーに合わせて調整してください。