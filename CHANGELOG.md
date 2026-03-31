# CHANGELOG

このプロジェクトは Keep a Changelog の形式に従います。  
バージョニングは SemVer を使用します。

全般的な設計方針（本リリースで一貫していること）
- ルックアヘッドバイアス防止: datetime.today()/date.today() を直接参照せず、明示的な target_date 引数を用いる。
- DuckDB を主要なローカルデータストアとして利用し、SQL + Python の組合せで処理を実装。
- 外部 API 呼び出しは堅牢化（バッチ化・リトライ・フェイルセーフ）し、部分失敗でも他の処理を保護する（冪等書き込み等）。
- テスト容易性を考慮し、OpenAI 呼び出し等はモック可能に設計。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
Added
- パッケージ基盤
  - kabusys パッケージの初期公開。パッケージバージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を定義（将来のサブパッケージ公開を想定）。

- 設定／環境変数管理（kabusys.config）
  - .env / .env.local 自動ロード機能を実装（読み込み優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env パーサの強化:
    - コメント行、export プレフィックス対応。
    - シングル／ダブルクォート内のエスケープ処理対応。
    - 行中コメントの扱い（クォート有無に応じた適切なトリミング）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供。
  - Settings で J-Quants / kabuステーション / Slack / DB パス / 環境判定（development/paper_trading/live）/ログレベルの検証付き取得を実装。
  - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。

- AI 関連（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI (gpt-4o-mini) を用いて銘柄別センチメント（ai_score）を算出して ai_scores テーブルへ保存する。
    - 特徴:
      - JST 時刻ウィンドウ（前日 15:00 〜 当日 08:30）を正確に計算（UTC naive）。
      - 1 銘柄当たり最大記事数および文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - バッチ処理（最大 20 銘柄/回）と JSON Mode による厳密なレスポンス検証。
      - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）。
      - レスポンスの堅牢なバリデーションとスコアクリップ（±1.0）。
      - DuckDB executemany の空リスト問題回避（空の params を送らないチェック）。
      - テスト利便のため _call_openai_api を差し替え可能に実装。
  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定し market_regime テーブルへ冪等書き込みする。
    - 特徴:
      - prices_daily へのクエリは date < target_date でルックアヘッドを防止。
      - マクロニュースはニュースタイトルをフィルタして最大 20 件まで LLM に送り、OpenAI の結果を JSON パースしてスコア化。
      - API 障害時は macro_sentiment を 0.0 として継続（フェイルセーフ）。リトライ／バックオフ処理を組み込み。
      - OpenAI 呼び出しは news_nlp と別実装にしてモジュール結合を回避。
      - 計算結果は BEGIN/DELETE/INSERT/COMMIT の冪等処理で保存、失敗時は ROLLBACK を試行。

- 研究用ツール群（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を参照して計算する関数群を実装。
    - データ不足時は None を返す等の安全設計。
  - feature_exploration モジュール
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）を一括クエリで取得する calc_forward_returns。
    - ランク相関（Spearman 相当）の IC 計算 calc_ic（ties の平均ランク処理を実装）。
    - 基本統計量を返す factor_summary（count/mean/std/min/max/median）。
    - 独自の rank 実装（浮動小数の丸めで ties を安定検出）。

- データプラットフォーム（kabusys.data）
  - calendar_management モジュール
    - JPX カレンダー管理ロジック（market_calendar テーブルベース）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定 API を提供。
    - DB 未取得時は曜日（土日）ベースのフォールバックを使用する一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得し、バックフィル（直近数日）と健全性チェックを行い冪等保存するバッチ処理を実装（fetch/save を jquants_client に委譲）。
  - pipeline モジュール（kabusys.data.pipeline）
    - ETLResult データクラスを提供し、ETL の取得数／保存数／品質検査結果／エラーを集約して返却。
    - 市場カレンダー・株価・財務データの差分取得・保存・品質検査を想定したユーティリティを構造化。
  - etl で ETLResult を再エクスポート。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし（ただし上記の設計で既知の落とし穴に対応済み。例: DuckDB executemany の空リスト回避、OpenAI API の 5xx / タイムアウト処理、.env ファイルのエスケープ処理など）。

Security
- OpenAI API キー等の機密情報は Settings を介して環境変数で管理。OpenAI キーが未セットの場合、score_news / score_regime は ValueError を送出し明示的に失敗する（誤発注などを避けるため）。

Notes / Migration / 使用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須チェックを行う。
  - OpenAI API を利用する関数（score_news / score_regime）は api_key 引数または環境変数 OPENAI_API_KEY を必要とする。未設定時は ValueError。
- 自動 .env ロードが不要なテストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能。
- DuckDB / テーブル前提:
  - 多くの処理は prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等のテーブル存在を前提としている。初期化スクリプト／スキーマ整備は別途必要。
- OpenAI へのリクエスト:
  - デフォルトモデルは gpt-4o-mini。API 呼び出しは JSON mode（response_format={"type": "json_object"}）を利用しており、レスポンス整形を期待している。
  - LLM レスポンスがパースできない場合はフェイルセーフとして該当スコアをスキップまたは 0.0 にフォールバックするため、部分的な失敗がシステム全体を停止させることはない。
- テスト補助:
  - news_nlp._call_openai_api、regime_detector._call_openai_api 等は unittest.mock.patch で差し替えて単体テスト可能。

既知の制限 / 今後の課題
- 資産ごとの追加ファクター（PBR、配当利回り等）は未実装（calc_value には注記あり）。
- strategy / execution / monitoring パッケージは __all__ に含まれているが、本リリースでは実装が限定的（将来実装予定）。
- DuckDB へのリストバインド（ANY 等）はバージョン依存の挙動があるため、互換性のために executemany を多用している。将来的にバインド互換性が改善されればリファクタ検討。

署名
- 初回リリース: kabusys 0.1.0 — 日本株自動売買システムのデータ処理・研究・AI評価基盤のプロトタイプ的実装を公開。

（この CHANGELOG はコードベースの実装に基づいて作成しています。実際のリリースノートはコミット履歴やリリース時の差分に応じて更新してください。）