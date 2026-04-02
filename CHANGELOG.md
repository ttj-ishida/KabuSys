# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

なお、このリポジトリの現行バージョンは `0.1.0` です（初期リリース）。

[Unreleased]: https://example.com/compare/HEAD...HEAD

## [0.1.0] - 2026-04-02

### Added
- パッケージ全体の初期実装を追加
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`, パブリックモジュール公開設定 (`__all__`) を定義。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み順序: OS 環境 > .env.local > .env
    - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
    - プロジェクトルートの検出: `.git` または `pyproject.toml` を親ディレクトリから探索
    - .env パーサーは export 形式・クォート・エスケープ・コメントを考慮
    - OS 環境変数を保護するための上書き制御（protected set）
  - 設定アクセス用クラス `Settings` を提供（`settings` インスタンスをエクスポート）
    - J-Quants / kabuステーション / Slack / DB パス / 監視しきい値 / システム環境などのプロパティを用意
    - 環境変数の必須チェック `_require()`（未設定時は ValueError を発生）
    - デフォルト値:
      - KABU API ベース: `http://localhost:18080/kabusapi`
      - DUCKDB_PATH: `data/kabusys.duckdb`
      - SQLITE_PATH: `data/monitoring.db`
      - PID_FILE_PATH: `data/execution.pid`
      - CPU/MEMORY/DISK しきい値デフォルトあり
    - `KABUSYS_ENV` の許容値: `development`, `paper_trading`, `live`
    - `LOG_LEVEL` の許容値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して `ai_scores` テーブルへ書き込む関数 `score_news(conn, target_date, api_key=None)` を実装。
  - 特徴:
    - JST ベースのニュース収集ウィンドウ計算（前日15:00～当日08:30 → 内部は UTC naive）
    - 1銘柄あたり最大記事数・文字数でトリム（トークン肥大対策）
    - 銘柄をチャンク（最大 20 銘柄）でバッチ送信
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ
    - レスポンス検証（JSON 抽出、"results" キー、コード/スコアの妥当性チェック）
    - スコアは ±1.0 にクリップ
    - DB 書き込みは冪等（対象コードのみ DELETE して INSERT）で部分失敗に配慮
    - API キーは引数または環境変数 `OPENAI_API_KEY` で解決。未設定時は ValueError を送出

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成して、市場レジーム（`bull` / `neutral` / `bear`）を日次で判定する `score_regime(conn, target_date, api_key=None)` を実装。
  - 特徴:
    - MA 計算は target_date 未満のデータのみを利用し、ルックアヘッドバイアスを排除
    - マクロニュースは `news_nlp.calc_news_window` で同ウィンドウを計算し、`_MACRO_KEYWORDS` でフィルタしたタイトル群を LLM へ送信
    - OpenAI 呼び出しは独自実装でモジュール結合を低減
    - API エラー時はマクロセンチメントを 0.0 にフォールバック（フェイルセーフ）
    - スコア合成後は `market_regime` テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - 必要な API キー未設定時は ValueError を送出

- 研究（kabusys.research）
  - ファクター計算（`calc_momentum`, `calc_value`, `calc_volatility`）
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離など
    - Value: PER / ROE（raw_financials を使用）
    - Volatility: 20 日 ATR、平均売買代金、出来高比率など
    - いずれも DuckDB の `prices_daily` / `raw_financials` を参照し外部 API にはアクセスしない
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン、引数検証あり）
    - IC（スピアマンのランク相関）計算 `calc_ic`
    - ランク変換ユーティリティ `rank`
    - ファクター統計サマリー `factor_summary`
    - すべて標準ライブラリと DuckDB の SQL を用いて実装（pandas 等依存なし）

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - 営業日判定 API: `is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`
    - JPX カレンダーを J-Quants から差分取得して `market_calendar` を更新する夜間バッチジョブ `calendar_update_job`
    - DB に値がない場合は曜日ベース（週末除外）でフォールバック
    - 最大探索日数の上限や健全性チェック、バックフィル挙動を実装
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL 実行結果を表す `ETLResult` データクラスを公開（`kabusys.data.ETLResult` 経由で再エクスポート）
    - 差分取得、保存（jquants_client 経由の idempotent 保存）、品質チェック（quality モジュール連携）を想定した設計
    - ETLResult は品質問題・エラーを集約し、to_dict() でシリアライズ可能
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など

- 例外処理・ロギング・運用性改善
  - API 呼び出しに対するリトライ戦略（指数バックオフ）を多数の箇所で導入
  - LLM レスポンスのパース失敗は例外を投げず警告ログを出してフェイルセーフにフォールバック
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照しない方針を各所で採用（関数引数で基準日を受け取る）

### Changed
- 初期リリースのため該当なし

### Fixed
- 初期リリースのため該当なし

### Security
- OpenAI API キーや各種トークンは環境変数で管理する設計
  - 必須環境変数（例）:
    - `OPENAI_API_KEY`（score_news, score_regime のデフォルト解決先）
    - `JQUANTS_REFRESH_TOKEN`
    - `KABU_API_PASSWORD`
    - `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
  - .env 自動読み込みを無効にしたいテスト等の用途には `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使用
- .env 読み込み時に OS 環境変数を保護する仕組みを用意（既存の env を上書きしない／保護 set）

### Notes / Migration
- DuckDB スキーマ（本実装が参照・書き込むテーブル）について:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar などを前提としているため、ETL や初回データロードでこれらのテーブルを用意してください。
- OpenAI の JSON mode を使用しているため、レスポンス形式は厳密な JSON を期待します。関数は余計な前後テキストを取り除く復元処理を行いますが、互換性に問題がある場合は調整してください。
- API キー未設定時の挙動:
  - `score_news` / `score_regime` は API キーが引数で渡されない場合、環境変数 `OPENAI_API_KEY` を参照し、未設定時は ValueError を送出します。
- DB 書き込みは基本的に冪等（DELETE→INSERT、トランザクション制御）を意識しているため、部分的な再実行や障害回復に耐性があります。

---

この CHANGELOG はコードベースから推測して作成した内容を記載しています。実際のリリースノートには、リリース日・変更者・影響範囲（breaking changes）などを適宜追記してください。