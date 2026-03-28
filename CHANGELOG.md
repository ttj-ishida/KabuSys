# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: Unreleased / バージョン / 日付（YYYY-MM-DD）。

## [Unreleased]
（現在なし）

---

## [0.1.0] - 2026-03-28
初回リリース

### 追加 (Added)
- パッケージ初期構成
  - パッケージ名: kabusys、バージョン 0.1.0
  - エクスポート: data, strategy, execution, monitoring

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml 基準）
  - .env パーサーの実装（export 形式対応、クォート処理、インラインコメント対応）
  - 自動読み込み抑止フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 必須環境変数チェック用 _require ヘルパーと Settings クラス
  - 設定値:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須チェック
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH, SQLITE_PATH のデフォルトパスと Path 型返却
    - 環境モード検証（development / paper_trading / live）とログレベル検証

- ニュース系 AI モジュール (kabusys.ai)
  - news_nlp.score_news: raw_news を OpenAI（gpt-4o-mini）でバッチ評価し ai_scores テーブルへ保存
    - タイムウィンドウ計算（JST基準の前日15:00～当日08:30）
    - 銘柄ごとに記事集約（記事数・文字数上限でトリム）
    - 最大 20 銘柄単位のチャンク処理、JSON Mode を利用した堅牢なレスポンス検証
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ
    - レスポンスの厳格バリデーション（results 配列、code/score の検証、±1.0 にクリップ）
    - 部分失敗対策: 成功したコードのみ DELETE → INSERT による置換（冪等性と既存データ保護）
    - テスト容易性: _call_openai_api の差し替え（unittest.mock.patch で置換可能）
  - regime_detector.score_regime: マーケットレジーム判定
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成
    - レジームラベル: bull / neutral / bear（閾値設定あり）
    - OpenAI 呼び出しのリトライ/フェイルセーフ（失敗時 macro_sentiment=0.0）
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - 設計上ルックアヘッドバイアスを避ける（date < target_date 等の厳密な条件）

- データ処理 (kabusys.data)
  - ETL パイプラインインターフェース ETLResult（kabusys.data.pipeline）
    - ETL 実行結果を格納する dataclass（品質問題・エラー列挙・集計フィールド等）
  - pipeline モジュール: 差分更新、バックフィル、品質チェックの設計（J-Quants 統合想定）
  - calendar_management モジュール
    - JPX カレンダー更新バッチ（calendar_update_job）と J-Quants クライアント連携
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - カレンダー未取得時の曜日ベースのフォールバック（整合性確保）
    - 最大探索日数やバックフィル、健全性チェックの導入

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離
    - calc_volatility: 20日 ATR、ATR 比率、平均売買代金、出来高比率
    - calc_value: PER（EPS に基づく）、ROE（最新財務データ結合）
    - すべて DuckDB による SQL 処理で実装（外部 API にはアクセスしない設計）
  - feature_exploration モジュール
    - calc_forward_returns: 将来リターン（任意ホライズン、デフォルト [1,5,21]）
    - calc_ic: スピアマン順位相関（IC）計算
    - factor_summary: 基本統計量算出（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクの実装
  - zscore_normalize を data.stats から再エクスポート

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を参照する設計。API キーの未設定時は ValueError を送出して誤動作を防止。

### 設計上の注意・既知の挙動
- すべての日付計算はルックアヘッドバイアスを避けるために date / datetime の直接参照を避け、引数で渡された target_date に厳密に依存する。
- OpenAI 呼び出しは JSON Mode を想定しつつ、実運用でのレスポンス不整合に備えたパース耐性実装あり（外側の {} 抽出など）。
- DuckDB の executemany の制約（空リスト不可）を考慮して空チェックを行っている。
- market_calendar が不完全な場合でも一貫したフォールバックルールを提供する（DB 値優先、未登録日は曜日ベースで補完）。

---

開発・運用上の補足や将来の変更点は CHANGELOG の Unreleased セクションに追記してください。