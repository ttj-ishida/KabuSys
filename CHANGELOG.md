# Changelog

すべての注目すべき変更点はここに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。

### 追加
- パッケージ基盤
  - pakage: kabusys
  - バージョン定義: `kabusys.__version__ = "0.1.0"`
  - 公開サブパッケージ: data, research, ai, execution, strategy, monitoring（__all__ にて宣言）

- 環境設定
  - kabusys.config
    - .env ファイルおよび環境変数からの自動読み込み機能（プロジェクトルート判定: .git / pyproject.toml）
    - .env / .env.local 読み込み優先度と保護キー（OS 環境変数の上書き防止）
    - .env パーサ実装（export 形式、クォート、エスケープ、インラインコメント対応）
    - Settings クラスによるプロパティ型取得:
      - J-Quants: `jquants_refresh_token`
      - kabuステーション API: `kabu_api_password`, `kabu_api_base_url`
      - Slack: `slack_bot_token`, `slack_channel_id`
      - DB パス: `duckdb_path`, `sqlite_path`
      - 実行環境判定: `env`, `is_live`, `is_paper`, `is_dev`
      - ログレベル検証: `log_level`
    - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- データプラットフォーム
  - kabusys.data.pipeline
    - ETL パイプラインの結果を表す `ETLResult` データクラスを実装・公開（kabusys.data.etl から再エクスポート）
    - 差分取得、バックフィル、品質チェックの概念を実装（jquants_client / quality を利用）
  - kabusys.data.calendar_management
    - 市場カレンダー管理と営業日判定ロジック実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - calendar_update_job: J-Quants からの差分取得、バックフィル、健全性チェック、冪等保存
    - DB がない/まばらな場合の曜日ベースフォールバック実装
    - 最大探索日数制限により無限ループ防止

- 研究（Research）
  - kabusys.research.factor_research
    - モメンタム / ボラティリティ / バリュー関連ファクター計算:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA のデータ不足時の扱い）
      - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio
      - calc_value: PER / ROE（raw_financials から最新レコードを取得）
    - DuckDB を用いた SQL + Python 実装。prices_daily / raw_financials のみ参照。
  - kabusys.research.feature_exploration
    - 特徴量探索・統計:
      - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
      - calc_ic: スピアマンランク相関（IC）計算（3 レコード未満は None）
      - rank: 同順位は平均ランクを返す実装（丸めにより ties を安定化）
      - factor_summary: count/mean/std/min/max/median の算出（None 値除外）
  - kabusys.research.__init__
    - 主要ユーティリティの再エクスポート（zscore_normalize を含む）

- AI（OpenAI 統合）
  - kabusys.ai.news_nlp
    - score_news(conn, target_date, api_key=None)
      - raw_news, news_symbols を集約して銘柄ごとにニューステキストを作成し、OpenAI（gpt-4o-mini）でバッチ評価。
      - バッチサイズ、記事数・文字数上限、JSON Mode レスポンス検証、リトライ（429/ネットワーク/5xx）、指数バックオフを実装。
      - レスポンスのバリデーション、スコアの ±1.0 クリップ、DuckDB への冪等的な書き込み（DELETE → INSERT、executemany 対策）。
      - テスト支援: _call_openai_api をパッチして置換可能。
  - kabusys.ai.regime_detector
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321（225 連動型）の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して日次市場レジーム判定（bull/neutral/bear）。
      - calc_news_window を利用してニュースウィンドウを取得、_calc_ma200_ratio による MA 乖離算出。
      - OpenAI 呼び出し（gpt-4o-mini）とリトライ・フォールバック（API 失敗時 macro_sentiment=0.0）。
      - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。
      - テスト支援: _call_openai_api をパッチして置換可能。
  - 共通設計方針:
    - datetime.today() / date.today() を用いない（ルックアヘッドバイアス防止）
    - API キー注入: 関数引数 api_key または環境変数 OPENAI_API_KEY を利用

### 変更
- 初版のため該当なし。

### 修正
- 初版のため該当なし。

### 削除
- 初版のため該当なし。

### セキュリティ
- 初版のためセキュリティ修正なし。

### 既知の制約・注意点
- DuckDB 互換性:
  - DuckDB のバージョンにより executemany の空リストが許容されないため、空チェックを明示的に行っている（score_news / ai_scores 書き込み）。
- OpenAI 使用時のフォールバック:
  - API エラーや JSON パース失敗時は例外を上げず中立スコア（0.0）やスキップを採る挙動（フェイルセーフ）になっている。
- DB スキーマ:
  - 本リポジトリ内にテーブル作成スクリプトは含まれていない。prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等のスキーマを事前に準備する必要がある。
- 外部クライアント:
  - jquants_client（データ取得）、quality（品質チェック）は外部モジュールとして参照しているため、提供またはモック化が必要。
- テスト向け設計:
  - OpenAI 呼び出し部分は内部で _call_openai_api を切り出しており、unittest.mock.patch で差し替え可能。
  - 環境変数の自動ロードはテストで KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。

### マイグレーション / 導入メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（score_news / score_regime 実行時）
- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動で読み込む。CI / テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨。
- DuckDB 接続:
  - 各関数は DuckDB の接続オブジェクト（DuckDBPyConnection）を引数として受け取るため、呼び出し側で接続を生成して渡すこと。
- OpenAI の呼び出し:
  - api_key を関数へ直接渡すか、環境変数 OPENAI_API_KEY を設定すること。レスポンスは JSON mode を期待する。

---

今後の予定（例）
- ETL のより詳細な品質チェック実装と自動アラート連携
- ai モジュールの追加評価指標や複数モデル対応
- DB スキーマ初期化スクリプトの追加

（この CHANGELOG はコード実装から推測して作成しています。実際のリリースノートとして公開する場合は、変更差分やリリース手順に合わせて加筆・修正してください。）