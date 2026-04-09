# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。  

※日付と内容は、提供されたコードベースの内容から推測して作成しています。

## [Unreleased]

（無し）

## [0.1.0] - 2026-04-09

初回リリース。以下の主要機能と設計方針を実装・提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化モジュールを追加（kabusys.__init__）。
  - 公開サブパッケージとして data, research, ai, その他（strategy, execution, monitoring を想定）をエクスポート。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、行末コメントの扱いに対応）。
  - Settings クラスを提供し、J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）などのプロパティを公開。
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL などの値検証と分かりやすいエラーメッセージを実装。
  - OS 環境変数を「protected」として .env 上書きから守る実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄単位のセンチメント（ai_score）を算出し ai_scores テーブルへ書き込む score_news を実装。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
  - API 呼び出しのバッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの記事数上限・文字数トリム、レスポンス検証ロジックを実装。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ実装。
  - JSON パースの堅牢化（周辺テキスト混入への対応）、スコアクリップ（±1.0）、部分失敗時に既存スコアを保護する DB 書き込みロジック（DELETE → INSERT）を採用。
  - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（関数単位で patch 可能）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の market_regime を計算・保存する score_regime を実装。
  - MA200 計算でルックアヘッドを防ぐため target_date 未満のデータのみを使用する実装。
  - マクロキーワードで raw_news をフィルタして LLM を呼び出すロジック、API エラー時のフォールバック macro_sentiment=0.0、リトライ・バックオフ処理を実装。
  - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を採用。

- データプラットフォーム（kabusys.data）
  - ETL 用データクラス ETLResult（pipeline モジュール）を公開（kabusys.data.etl による再エクスポート）。
  - ETL パイプライン（kabusys.data.pipeline）の基本骨子を実装（差分取得、保存、品質チェックの設計方針を定義）。
  - カレンダー管理モジュール（kabusys.data.calendar_management）を実装:
    - market_calendar テーブルの夜間更新ジョブ calendar_update_job（J-Quants から差分取得、バックフィル、健全性チェック）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティ。
    - DB にカレンダー情報がない場合の曜日ベースフォールバックを一貫して適用。
    - 検索範囲制限（無限ループ防止）や date 型のみを扱うことで timezone 混入を防止する設計。

- リサーチ（kabusys.research）
  - ファクター計算モジュール（kabusys.research.factor_research）を実装:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（ma200_dev）を計算。データ不足時の None ハンドリング。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が無効な場合は None）。
  - 特徴量探索モジュール（kabusys.research.feature_exploration）を実装:
    - calc_forward_returns: 指定ホライズンの将来リターン計算（複数ホライズン対応、入力検証あり）。
    - calc_ic: スピアマン（ランク）による IC 計算（ランクの tie 処理は平均ランク）。
    - rank / factor_summary: ランク変換と統計サマリの実装。
  - 研究用ユーティリティ群をリパッケージして公開。

### 変更 (Changed)
- （初リリースのため過去からの変更なし）

### 修正 (Fixed)
- （初リリースのため過去からの修正なし）

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- OpenAI API キー管理について:
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY のいずれかを必須とし、未設定時に ValueError を投げて明示。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化でき、運用上のリスクを軽減可能。
- OS 環境変数は .env から保護される（上書き不可）実装。

### 設計上の注意・方針
- ルックアヘッドバイアス防止: datetime.today() や date.today() に依存する処理を避け、関数引数の target_date を基準に処理を行うことを徹底。
- DuckDB を主要な分析 DB として使用（関数は DuckDB 接続を受け取る設計）。
- DB 書き込みは冪等性を考慮（部分失敗時に既存データを過度に消さない戦略）。
- OpenAI 呼び出し箇所はテストで差し替え可能（ユニットテスト容易性）。
- API 呼び出しの堅牢化（リトライ・バックオフ・5xx の扱い・タイムアウト）とレスポンス検証を重視。

---

今後のリリースでは、戦略（strategy）、実行（execution）、監視（monitoring）周りの具体的な発注ロジック／ランタイム監視機能の実装、運用向けの CLI / サービス化、より詳細な品質チェックやデータ補完ロジックの追加などが想定されます。