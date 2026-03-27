# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
安定版リリースや後方互換性の注意などは各項目を参照してください。

## [0.1.0] - 2026-03-27
初回リリース

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: kabusys のトップレベル __version__ を "0.1.0" として公開。モジュール公開一覧に data, strategy, execution, monitoring を追加。
- 設定/環境変数管理 (kabusys.config)
  - .env ファイルと環境変数の自動読み込み機能を実装。
    - プロジェクトルート判定は __file__ を起点に ".git" または "pyproject.toml" を探索して行うため、CWD に依存しない実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用）。
  - .env パーサ実装（export KEY=val 形式、シングル／ダブルクォート、バックスラッシュエスケープ、コメント処理をサポート）。
  - Settings クラスを公開（settings）。J-Quants / kabu ステーション / Slack / DB パスなどの設定プロパティを提供。
    - 必須項目は _require による ValueError を投げる（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - KABUSYS_ENV の値検証（development, paper_trading, live のみ有効）。
    - LOG_LEVEL の値検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - デフォルト DB パス: DuckDB は data/kabusys.duckdb、SQLite は data/monitoring.db。
- ニュース NLP / AI (kabusys.ai)
  - news_nlp モジュールを追加（score_news）
    - raw_news と news_symbols を集約して銘柄ごとに記事を連結・トリムし、OpenAI(Chat)（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを算出。
    - タイムウィンドウは JST 基準（前日 15:00 ～ 当日 08:30）を UTC に変換して利用。
    - バッチサイズや一銘柄あたりの文字数/記事数の上限 (_BATCH_SIZE, _MAX_CHARS_PER_STOCK, _MAX_ARTICLES_PER_STOCK) を設定。
    - レート制限（429）・ネットワーク断・タイムアウト・5xx に対して指数バックオフのリトライ実装。
    - レスポンスに対する堅牢なバリデーションを実装（JSON 抽出、results 配列・code/score の検証、スコアクリッピング ±1.0）。
    - DuckDB への書き込みは部分的置換戦略（対象コードのみ DELETE → INSERT）で冪等・部分失敗耐性を確保。DuckDB の executemany に空リストを与えないガードあり。
  - regime_detector モジュールを追加（score_regime）
    - ETF 1321（日経225）200日移動平均乖離とマクロニュースの LLM センチメントを重み付け合成して日次市場レジーム（bull/neutral/bear）を判定。
    - 合成重みは移動平均 70% / マクロセンチメント 30%、スコアを [-1, 1] にクリップし閾値でラベル付け。
    - ma200_ratio はルックアヘッドバイアスを防ぐため target_date 未満のデータのみ使用し、データ不足時は中立（1.0）を返すフェイルセーフ。
    - マクロニュースの LLM 呼び出しはリトライとフェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI クライアントは OpenAI(api_key=...) を利用。API キー未設定時は ValueError を送出。
- 研究・ファクター計算 (kabusys.research)
  - factor_research モジュールを追加
    - calc_momentum: 1M/3M/6M リターンと200日 MA 乖離（ma200_dev）の計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などの計算。
    - calc_value: raw_financials から EPS/ROE を取り出し PER/ROE を計算（未実装の指標を除く）。
    - 各関数は DuckDB 接続（prices_daily / raw_financials）を受け、(date, code) キーの辞書リストを返す設計。
  - feature_exploration モジュールを追加
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。
    - calc_ic: スピアマンのランク相関（IC）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクにするランク変換実装（浮動小数の丸めで ties 検出を安定化）。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算。
  - research パッケージは必要なユーティリティを __all__ で再エクスポート（zscore_normalize 等）。
- データプラットフォーム (kabusys.data)
  - calendar_management を追加
    - market_calendar テーブルに基づく営業日判定 helper（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーがない場合は土日ベースのフォールバック。DB がまばらな場合でも一貫性を保つ設計。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィル・健全性チェック（future days）を実装。
  - pipeline / ETL（kabusys.data.pipeline）を追加
    - ETLResult dataclass を実装し、ETL の取得数・保存数・品質問題・エラーを集約。
    - 差分更新・バックフィル・品質チェック（quality モジュール連携）を想定した設計。
  - etl モジュールで ETLResult を再エクスポート。
  - 内部で jquants_client との連携を想定した抽象化。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーは関数引数で注入可能。未指定の場合は環境変数 OPENAI_API_KEY を参照し、未設定時は明示的に例外を投げることで誤使用を防止。

### 互換性と注意事項 (Notes)
- ルックアヘッドバイアス防止
  - news_nlp, regime_detector, research モジュールはいずれも datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を明示的に与える設計です。運用時は必ず適切な target_date を渡してください。
- DuckDB 互換性
  - executemany に空リストを与えない等の回避処理を入れており、DuckDB のバージョン差異に配慮しています。
- .env 自動読み込み
  - パッケージ読み込み時にプロジェクトルートが検出されると .env/.env.local が自動で読み込まれます。テスト等で自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数
  - 実行に必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）は Settings 経由で要求されます。未設定時は ValueError が発生します。
- 設計方針
  - 本リリースの多くの処理は「読み取り／解析」側（データ取得・前処理・スコアリング・解析）に注力しており、発注・実際の取引用 API 呼び出し部分（execution 等）は別モジュールとして分離されています。

### マイグレーション (Migration)
- 既存プロジェクトへ導入する場合:
  - .env の場所はプロジェクトルート（.git または pyproject.toml の親ディレクトリ）を基準に探索されます。配置場所に注意してください。
  - OPENAI API を利用する機能（score_news, score_regime）は API キーが必須です。環境変数または関数引数でキーを渡してください。

---

今後のリリースでは、以下の点を予定しています（未実装/計画）
- 発注・実行ロジック（execution）およびモニタリング機能の詳細実装
- テストカバレッジ拡充と性能チューニング（特に大規模データ処理時のメモリ・レスポンス最適化）
- jquants_client / kabu API との結合テストおよびリトライ戦略の追加強化

（初回リリース: 開発チーム）