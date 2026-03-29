# CHANGELOG

全ての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-29

### 追加
- 初回公開リリース。
- パッケージの基本情報を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パブリックモジュール: data, strategy, execution, monitoring（簡易エクスポートを __all__ に設定）
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能
  - export KEY=val 形式、シングル／ダブルクォート内のエスケープ、インラインコメント処理などに対応した .env パーサを実装
  - 環境変数必須チェック用の _require、Settings クラスを提供
  - J-Quants / kabu API / Slack / DB パスなどの設定プロパティを公開（デフォルト値を含む）
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーション実装
  - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news と news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価して ai_scores テーブルへ書き込み
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC で前日 06:00 ～ 23:30）を厳密に計算して対象記事を選択
    - バッチ処理: 最大 20 銘柄/コール、1銘柄あたり最大 10 記事・3000 文字にトリム
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフで再試行
    - レスポンスのバリデーション（JSON 抽出、results 配列、code/score 検証、スコアの ±1.0 クリップ）
    - DuckDB の互換性考慮（executemany に空リストを渡さない保護）
    - API 呼び出し箇所はテスト用に patch 可能（kabusys.ai.news_nlp._call_openai_api）
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出
    - マクロキーワード群に基づく記事抽出、LLM による -1.0〜1.0 のマクロセンチメント評価（gpt-4o-mini）
    - 設計上の注意: ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照せず、prices_daily クエリは target_date 未満のデータのみを使用
    - API エラー時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ実装
    - OpenAI 呼び出し箇所は news_nlp とは独立した実装（モジュール結合を避ける）
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装
    - 再試行・エラーハンドリング、ログ出力を整備
- データモジュール (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを用いた営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB 未登録の日は土日ベースのフォールバックを採用して一貫性を確保
    - calendar_update_job: J-Quants API から差分取得し市場カレンダーを更新（バックフィル・先読み・健全性チェックあり）
    - 最大探索範囲、バックフィル日数、先読み日数、健全性チェック等のパラメータを定義
  - ETL / パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（取得数・保存数・品質チェック結果・エラー一覧を含む）
    - 差分更新・バックフィル・品質チェックを行う設計を想定
    - jquants_client と quality モジュールとの連携を前提にした構造
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など
  - jquants_client のラッパー（fetch/save を期待する実装を想定）
- Research モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR・ATR 比率）、Value（PER、ROE）等を DuckDB のクエリで計算
    - 欠損やデータ不足時の None 処理、スキャン用バッファ採用
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（calc_forward_returns、ホライズンはデフォルト [1,5,21]、最大 252 日チェック）
    - IC（Information Coefficient）計算（スピアマンのランク相関）
    - ランク関数（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）
  - data.stats の zscore_normalize を再エクスポート
- テスト容易性のための設計上の配慮
  - OpenAI 呼び出し箇所を patch しやすくしてユニットテストで差し替え可能に設計
  - API キー引数注入に対応（api_key 引数が None の場合は環境変数 OPENAI_API_KEY を参照）
- ロギングとエラーハンドリング
  - 各所で適切な logger を利用し、警告・情報・例外時のログを追加
  - DB 書き込み失敗時は ROLLBACK を試行し、失敗ログは警告として記録

### 変更
- （初版のため過去の変更なし）

### 修正
- （初版のため過去の修正なし）

### 既知の制約 / 注意点
- OpenAI は gpt-4o-mini を前提にプロンプトで JSON 出力を要求しているが、稀に余計なテキストが含まれる場合があるため、JSON 抽出ロジックで耐性を持たせている。
- DuckDB のバージョン差異（例: executemany に空リストを渡すと失敗する挙動）に配慮した実装を行っている。
- .env パーサは一般的なケースに対応しているが、非常に特殊な .env 構文には未対応の可能性がある。
- 現段階では PBR・配当利回り等の一部バリューファクターは未実装。

### セキュリティ
- API キー等の秘密は Settings で環境変数から取得することを想定。サンプル .env（.env.example）を参照して設定すること。

今後のロードマップ（例）
- strategy / execution / monitoring モジュールの具体的な実装（発注・監視機能）
- ai モデルの改善（プロンプトチューニング、追加評価指標）
- ETL の品質チェック強化（quality モジュールとの統合テスト）
- CI / テストカバレッジの整備

---