# Keep a Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。以下の主要機能・モジュールを実装・公開しました。

### 追加
- パッケージ構成
  - kabusys パッケージの公開（__version__ = 0.1.0）。主要サブパッケージ想定: data, research, ai, (strategy, execution, monitoring を __all__ に含む)。

- 設定管理（kabusys.config）
  - プロジェクトルート自動検出ロジック（.git または pyproject.toml を基準）を実装し、カレントワーキングディレクトリに依存しない .env 自動読み込みを提供。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理など）。
  - .env と .env.local の読み込み優先度を実装（OS 環境変数を保護する protected 機能、override の挙動）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - Settings クラスを提供し、必要な環境変数取得メソッド（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）や、パス（duckdb/sqlite）、環境（development/paper_trading/live）・ログレベルのバリデーション、環境判定ユーティリティ（is_live/is_paper/is_dev）を実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとのニュース集約ロジックを実装（収集ウィンドウ計算、記事トリム、記事数/文字数上限）。
    - OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価を実装（最大バッチサイズ、JSON mode 利用）。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実行、失敗はフェイルセーフでスキップ。
    - レスポンスバリデーション機能を実装（JSON 抽出、results 検証、コード照合、数値チェック、±1.0 でクリップ）。
    - ai_scores テーブルへの置換的書き込み（DELETE → INSERT、部分失敗時に既存データ保護）。
    - score_news API を公開（DuckDB 接続を受け取り、書き込み件数を返す）。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily / raw_news を用いたデータ取得、ma200 比の計算、マクロキーワードによる記事抽出、OpenAI 呼び出し、スコア合成と market_regime への冪等書き込みを実装。
    - API 呼び出しのリトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0 にフォールバック）を備える。
    - モジュール結合を避けるため、OpenAI 呼び出しの内部実装は news_nlp と分離。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー取り扱いロジックを実装（market_calendar テーブル参照、DB 優先、未登録日は曜日ベースのフォールバック）。
    - 営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - calendar_update_job を実装（J-Quants API を経由した差分取得、バックフィル、健全性チェック、jquants_client による保存）。
    - 検索範囲リミット、サニティチェック、不整合時のログ出力など堅牢性を考慮。
  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを実装（取得・保存件数、品質問題、エラー集約、辞書化メソッド）。
    - テーブル存在確認、最大日付取得など ETL ヘルパーを実装。
    - 差分更新、バックフィルの方針、品質チェック（quality モジュール）との連携方針を反映。
    - kabusys.data.etl は pipeline.ETLResult を再エクスポート。
  - jquants_client 使用のインターフェースを想定（fetch/save 処理は jquants_client 側で実装）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、ATR 相対値、20 日平均売買代金、出来高比を計算。
    - calc_value: raw_financials を用いた PER / ROE の計算（最新財務レコードを結合）。
    - 全関数は DuckDB 接続を受け取り、prices_daily / raw_financials のみ参照（外部 API 非依存）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装（有効レコード 3 未満は None）。
    - rank, factor_summary: ランク化（同順位は平均ランク）と統計サマリー（count/mean/std/min/max/median）を実装。
  - kabusys.research パッケージから主要関数を公開（再エクスポート）。

### 変更
- （初回リリースのため過去バージョンからの変更は無し）

### 修正
- （初回リリースのため修正履歴なし）

### 既知事項 / 設計上の注意
- ルックアヘッドバイアス防止: 多くの関数で datetime.today() / date.today() を直接参照せず、必ず外部から target_date を受け取る設計。
- OpenAI 呼び出しは JSON mode を利用する前提だが、レスポンスの前後に余計なテキストが混入するケースに備えたリカバリロジックを実装。
- DuckDB の executemany 空リスト制約（特に 0.10 系）に配慮した実装（空チェックしてから executemany を呼ぶ）。
- テスト容易性: OpenAI 呼び出しを差し替え可能にしてユニットテストでのモック化を想定。
- jquants_client, quality モジュール等は外部依存（別モジュール実装）を想定しているため、実運用にはそれらの実装が必要。

### セキュリティ
- 機密情報は Settings 経由で環境変数から取得（必須チェックあり）。.env 自動読み込みは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### 将来の作業候補（省略的）
- ファクターモデルの追加（PBR、配当利回り等）。
- news_nlp / regime_detector の評価とキャッシュ・メタデータ保存強化。
- ETL 実行のスケジューリング・監視統合（現段階では機能単位の実装）。

---

このファイルはコードベースから推測して作成した CHANGELOG です。必要に応じて日付・バージョンや細部を調整してください。