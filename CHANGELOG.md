CHANGELOG
=========

すべての重要な変更履歴はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

[Unreleased]
------------

なし

0.1.0 - 2026-03-29
------------------

初回公開リリース。

### 追加
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 に設定。パブリックサブパッケージとして data, strategy, execution, monitoring を公開。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定値を読み込む自動ローダを実装（OS 環境変数 > .env.local > .env の優先順位）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準に探索）。
  - .env のパース器を実装（export での定義、シングル／ダブルクォート、エスケープ、インラインコメント取り扱いに対応）。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 重要設定取得用ヘルパ（_require）と Settings クラスを提供。以下の設定プロパティを含む：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト値あり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスを持つ）
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/... のバリデーション）
    - is_live / is_paper / is_dev のブール判定プロパティ

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを算出。
    - バッチ処理（最大 20 銘柄/呼び出し）、1 銘柄あたりの記事数と文字数の上限設定を実装。
    - 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。API 失敗時は該当チャンクをスキップ（フェイルセーフ）。
    - レスポンスのバリデーションとスコアクリップ（±1.0）を実装。
    - ai_scores テーブルへ冪等的（DELETE→INSERT）に書き込み。部分失敗時の既存データ保護を考慮。
    - テスト容易化のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch 可能）。
    - 公開 API: score_news(conn, target_date, api_key=None)

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次のレジーム（bull/neutral/bear）を判定。
    - ma200_ratio の算出（ルックアヘッド防止のため target_date 未満のデータのみ使用、データ不足時は中立扱い）。
    - raw_news からマクロキーワードで記事を抽出し、OpenAI で macro_sentiment を算出。API 失敗時は macro_sentiment=0.0 としてフェイルセーフ。
    - レジームスコアの合成と label 決定（閾値適用）。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。例外時は ROLLBACK を試行。
    - 公開 API: score_regime(conn, target_date, api_key=None)

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar ベースの営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベースのフォールバックを提供（週末を非営業日扱い）。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、健全性チェック付き）。
    - 最大探索範囲制限（無限ループ防止）等の堅牢化。

  - ETL パイプライン（pipeline）
    - 差分取得→保存→品質チェックのフレームワークを実装。
    - ETL 実行結果を格納するデータクラス ETLResult を公開（to_dict により品質問題をシリアライズ可能）。
    - 最終取得日の取得、テーブル存在チェック、DuckDB 互換性を考慮したユーティリティ群を提供。
    - デフォルトのバックフィル日数やカレンダー先読みの設定を備える。

  - etl モジュールは ETLResult を再エクスポート。

- リサーチモジュール（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20日）、平均売買代金・出来高比率などを DuckDB の prices_daily 等から計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - raw_financials から PER/ROE を取得するロジック（calc_value）。
    - 全関数は DB のみに依存し、発注等の副作用はなし。
  - 特徴量探索（feature_exploration）
    - 将来リターン算出（calc_forward_returns、可変 horizon サポート）。
    - IC（Spearman の ρ）計算（calc_ic）、ランク算出ユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary）。
  - データ統計ユーティリティ（kabusys.data.stats から zscore_normalize を再利用）。
  - 公開 API: calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank

### 改善（設計上の配慮・実装上の注意）
- ルックアヘッドバイアスの防止
  - LLM 呼び出しや各種計算で date.today()/datetime.today() を直接参照しない設計。すべて target_date ベースで処理。
  - prices_daily クエリは target_date 未満／等の適切な排他条件で未来データ混入を防止。

- OpenAI 呼び出しの堅牢化
  - JSON Mode（response_format={"type":"json_object"}）を使用しつつ、JSON パースに失敗するケースへは前後の {} 抽出などの復元ロジックを実装。
  - レート制限・ネットワーク障害・タイムアウト・5xx に対してはリトライ（指数バックオフ）を実装し、最終的に失敗してもシステム全体を破綻させない（フェイルセーフで 0 やスキップ）。

- DuckDB 互換性考慮
  - executemany に空リストを渡せないバージョンへの対処（空チェックを明示）。
  - テーブル存在チェックや date 型変換ユーティリティを実装。

- トランザクション安全性
  - DB 書き込み時は BEGIN/COMMIT を明示し、例外時は ROLLBACK を試行してログ出力。

### セキュリティ / 必須設定
- 一部設定は必須。未設定時は ValueError を送出して早期検出する:
  - OPENAI_API_KEY（AI 関連関数で使用; 引数で上書き可能）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- .env 自動読み込み時、既存 OS 環境変数は保護（上書き防止）される仕組みを実装。

### テスト向けフック
- OpenAI 呼び出し部分（_call_openai_api）を unittest.mock.patch 等で差し替え可能にして単体テストを容易化。

### 既知の制約 / 注意事項
- OpenAI のレスポンス形式や SDK の将来的な変更（例: APIError のプロパティ名など）へは一部 getattr による耐性を持たせているが、SDK 大幅変更時は追加対応が必要になる可能性があります。
- DuckDB のバージョン差異により一部バインド方法や SQL 構文の互換性問題が生じ得るため、本番環境に導入する際は環境依存テストを推奨します。

今後の予定（例）
- strategy / execution / monitoring サブパッケージの実装拡充（本リリースでは data/research/ai を中心に提供）
- 更なる品質チェックルール追加やメトリクス計測の導入
- OpenAI モデルの切替やローカル代替モデル対応の検討

-----