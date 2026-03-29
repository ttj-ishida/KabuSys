# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。  
安定版リリース後はメジャー・マイナー・パッチ毎にここを更新してください。

なお、この CHANGELOG は提供されたコードベースから推測して作成しています（実装・設計意図・挙動に基づく要約）。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。本リリースでは日本株自動売買システムのコアライブラリ群（データ取得・ETL、カレンダー管理、リサーチ／ファクター計算、AI によるニュース解析と市場レジーム判定、環境設定等）を実装・公開しました。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化とバージョン定義を追加（__version__ = "0.1.0"）。
  - パッケージの主要サブモジュールを __all__ に公開（data, strategy, execution, monitoring 等）。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env 解析で以下に対応:
    - export KEY=val 形式のサポート
    - シングル／ダブルクォート付き値とバックスラッシュエスケープ処理
    - クォートなし値の行内コメント（#）処理（直前がスペース/タブの場合にコメントと認識）
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト向け）。
  - Settings クラスを追加し、アプリケーションで使用する環境変数を安全に取得：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須キー検証
    - DUCKDB_PATH / SQLITE_PATH のデフォルト値提供（Path 型）
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/...）のバリデーション
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI（自然言語処理・レジーム判定）モジュール（kabusys.ai）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news / news_symbols を銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（JST 基準 → UTC 変換）を calc_news_window で明確化。
    - バッチサイズ、トークン膨張対策（記事数上限・文字数上限）を実装。
    - JSON Mode を利用した厳密なレスポンス検証とロバストなパース（前後ノイズが混ざるケースの復元処理含む）。
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ）。
    - DuckDB の executemany に対する互換性考慮（空リストを渡さないガード）。
    - score_news API: DuckDB 接続と target_date を受け取り、書き込んだ銘柄数を返却。APIキー注入可（api_key 引数 or OPENAI_API_KEY 環境変数）。
    - テスト容易性のため OpenAI 呼び出し箇所を置き換え可能（_call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して daily market_regime を算出・保存。
    - マクロニュース抽出（マクロキーワード）と gpt-4o-mini を用いた JSON 出力評価。
    - API エラー時のフォールバック（macro_sentiment = 0.0）やリトライ実装、冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - lookahead バイアス防止方針（target_date 未満のデータのみを参照、datetime.today()/date.today() を参照しない）。
    - _call_openai_api は news_nlp 側と独立して実装し、モジュール結合を避ける設計。

- データ ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
  - ETLResult データクラスを追加し、ETL 実行結果（取得件数・保存件数・品質問題・エラー等）を集約できるようにした。
  - 差分更新・バックフィル・品質チェックの設計方針を実装（jquants_client, quality モジュールとの連携前提）。
  - DuckDB の存在チェック・最大日付取得ユーティリティを追加。

- カレンダー管理（kabusys.data.calendar_management）
  - market_calendar を用いた営業日判定 API を実装:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - market_calendar 未取得時の曜日フォールバック（週末：土日非営業）を実装し、DB に登録がある場合は DB 値を優先。
  - カレンダー夜間バッチの calendar_update_job 実装（J-Quants から差分取得 → 保存 → バックフィルと健全性チェック）。
  - 最大探索日数やバックフィル日数・健全性チェック等の安全策を追加。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research: momentum / volatility / value ファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - calc_value: 最新財務データ（raw_financials）と株価を組み合わせた PER/ROE 計算。
    - DuckDB SQL を活用した集約クエリで高速に計算。
  - feature_exploration: 将来リターン計算・IC（Spearman）・ランク関数・ファクター統計サマリーを実装。
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons のバリデーションあり。
    - calc_ic: Spearman の rank 相関をゼロから実装（同順位は平均ランクで処理）。
    - rank / factor_summary: 同順位処理や基本統計量（count/mean/std/min/max/median）を提供。
  - 研究ユーティリティ群を研究パッケージ __all__ でエクスポート。

- パッケージ API 整備
  - ai.__init__ と research.__init__ 等で外部公開 API を整備（score_news, score_regime, 各種計算関数等の公開）。

### Changed
- 設計上の方針明文化・一貫した実装
  - ルックアヘッドバイアス防止のため、主要な分析関数は date.today()/datetime.today() を直接参照しない設計に統一。
  - OpenAI 呼び出しは JSON Mode を利用し厳密 JSON を期待するが、万一の前後ノイズにも耐える復元ロジックを追加。
  - DuckDB の互換性を踏まえ、executemany に空リストを渡さない安全策を導入。

### Fixed
- フォールバックとフェイルセーフの明確化
  - AI API 呼び出しで発生する各種エラー（429 / 接続エラー / タイムアウト / 5xx）に対して指数バックオフのリトライ実装と、最終的に 0.0 にフォールバックすることでパイプラインの継続性を確保。
  - レスポンスパース失敗や未知コード・非数値スコアは無視して部分的に処理を継続することで、1 件の不正が全体を停止させない。

### Security
- 環境変数による機密情報の取得を Settings 経由で行う設計により、明示的なキー要求とエラー報告を導入（未設定時は ValueError）。自動 .env ロード時に OS 環境変数を保護する protected キーセットを使用。

### Notes / Usage tips
- OpenAI API の呼び出しは api_key 引数で注入可能（テストや CI での注入に便利）。api_key 未指定時は環境変数 OPENAI_API_KEY を参照します。
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB との互換性のため、executemany に空リストを渡すと例外になるバージョンがある点に注意（empty-guard が組み込まれています）。
- AI モジュール内の OpenAI 呼び出し部分はテスト用に差し替え可能（unittest.mock.patch で _call_openai_api をモック化）。
- すべての日付は datetime.date 型で扱い、timezone を混入させない設計になっています（UTC naive の日時取扱いに注意）。

---

既知の制約・今後の改善候補（今後のリリースで検討）
- レスポンス検証やリトライ戦略の更なる細分化（モデルごとの最適化）。
- ai_score / sentiment_score の算出ロジックやフィルタリング条件のチューニング。
- ETL の品質チェック機能（quality モジュール）との統合強化と自動アラート機能。
- J-Quants / kabu API クライアント（kabusys.data.jquants_client 等）の詳細実装とモック化整備（テストカバレッジ向上）。

以上。必要に応じてリリースノートに追加の詳細（例: 重要な API の使用例、マイグレーション手順、既知のバグと回避策）を追記してください。