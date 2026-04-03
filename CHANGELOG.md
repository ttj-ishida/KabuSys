# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-03

Added
- 初期リリースとして kabusys パッケージを追加。
  - パッケージメタ情報: version = 0.1.0、公開 API: data, strategy, execution, monitoring。
- 環境設定管理（kabusys.config）
  - .env/.env.local 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサを実装（export プレフィクス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い）。
  - 環境変数取得用 Settings クラスを追加（J-Quants / kabu API / LINE / DB / 監視 / システム設定をカバー）。
  - 設定値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）を提供。
  - ファイルパス設定は Path.expanduser を利用。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む処理を実装。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime）を採用。calc_news_window ユーティリティを提供。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄につき最大記事数・文字数制限によるトリミングを実装（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しは JSON Mode を期待し、レスポンスのバリデーションとスコアクリッピング（±1.0）を行う。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ。致命的な失敗はスキップ（フェイルセーフ）。
    - DuckDB への書き込みは部分置換（DELETE → INSERT、対象コードのみ）で冪等性と部分失敗耐性を確保。DuckDB の executemany 空リスト制約に配慮。
    - テストしやすさのため _call_openai_api を差し替え可能に実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む。
    - ma200_ratio の算出は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）。
    - マクロニュースはニュースタイトルをキーワードフィルタ（マクロ指標ワード群）で抽出。記事がない場合は LLM 呼び出しを行わず macro_sentiment = 0 とする。
    - OpenAI 呼び出しでのリトライ・エラー処理を実装（news_nlp と同様にフェイルセーフな挙動）。
    - DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に実施。ロールバック失敗時は警告。

- Data / ETL / Calendar（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー取得・保存・営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得のときは土日フォールバックを使い、一貫した挙動（DB 優先、未登録日は曜日ベース）を維持。
    - next/prev_trading_day は探索上限を設け _MAX_SEARCH_DAYS を超えるとエラーを返す。
    - calendar_update_job: J-Quants API から差分取得 → save_market_calendar 呼び出し → 保存（バックフィル・健全性チェックあり）。API/保存失敗はログ出力して 0 を返す。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー一覧を保持）。
    - 差分取得・保存・品質チェックの基本設計を反映したインターフェースを提供。
    - jquants_client と quality モジュールを想定した設計（idempotent 保存、バックフィル、品質チェックの収集）。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA 乖離率）を計算。データ不足時は None を返す設計。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。必要行数未満は None。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。未実装の指標（PBR 等）は明記。
    - DuckDB ベースの SQL＋Python 実装で外部 API を呼ばないポリシー。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 将来リターン（指定営業日ホライズン）を一括 SQL で取得。horizons の妥当性チェックあり。
    - calc_ic: ファクター値と将来リターンから Spearman（ランク）相関（IC）を計算。有効レコードが 3 未満なら None。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を実装。数値の有限性チェックと None 除外を行う。
    - pandas 等非依存で標準ライブラリのみでの実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは関数引数で注入可能（テスト容易化）かつ環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を発生させることで誤使用を防止。

Notes / Implementation details
- ルックアヘッドバイアス対策として各種処理は date / target_date を明確に受け取り、datetime.today()/date.today() を直接参照しない設計を採用。
- OpenAI 呼び出し周りは JSON mode を期待しつつ、レスポンスに前後テキストが混入するケースを考慮してパーシングのフォールバックを実装。
- DuckDB への書き込みでは部分更新（コードを限定）と executemany の空リスト回避を行い、DuckDB のバージョン依存問題に配慮。
- テスト容易性のため、内部で使用している API 呼び出し関数（例: _call_openai_api）を patch して差し替え可能。

Breaking Changes
- （初回リリースのため該当なし）

----

今後の予定（参考）
- ai_scores / market_regime の追加指標やバリデーション強化
- pipeline の具体的な ETL 実装（差分算出・保存フロー）の提供
- strategy / execution / monitoring モジュールの実装拡充

もし CHANGELOG の記載粒度や項目の追加・修正希望があれば教えてください。コードの差分（コミット履歴）があればより正確に作成できます。