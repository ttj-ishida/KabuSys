# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
安定版への影響がある重要な設計判断・依存・運用上の注意点についてもコードから推測して追記しています。

## [Unreleased]

### 追加
- なし（初回公開リリースは v0.1.0）

### 注意事項
- なし

---

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買プラットフォームのコアライブラリを実装。

### 追加
- 基本パッケージ
  - pakage 初期化: kabusys.__init__ により主要サブパッケージ（data, strategy, execution, monitoring）を公開。
  - バージョン情報: __version__ = "0.1.0" を設定。

- 設定／環境変数管理（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env, .env.local の優先順位を実装（OS 環境変数を保護する protected 機構、.env.local は上書き）。
  - export KEY=val 形式や引用符付き値、インラインコメント等に対応したパーサを実装。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 任意/デフォルト付き: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）、KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）
  - 設定値のバリデーション（env 値の許容値チェック、未設定時は ValueError を送出）。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp（kabusys.ai.news_nlp）
    - raw_news と news_symbols を結合して銘柄ごとにニュース文を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 BATCH_SIZE=20 銘柄）・トークン肥大対策（記事数上限・文字数トリム）を実装。
    - リトライ/バックオフ（429・ネットワーク断・タイムアウト・5xx）を実装、致命的でない失敗はスキップして継続（フェイルセーフ）。
    - レスポンスの堅牢なバリデーション実装（JSON 部分抽出、results 配列検査、型チェック、スコアクリップ ±1.0）。
    - 書き込みは idempotent（対象コードのみ DELETE → INSERT）で、部分失敗時に既存スコアを保護。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
    - calc_news_window: JST ベースのニュース集計ウィンドウ計算ユーティリティを提供（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。

  - regime_detector（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を統合して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照し、計算結果を market_regime テーブルへ冪等的に保存（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しは独立実装（news_nlp の内部関数と共有しない）でモジュール結合を避ける。
    - API エラーやパース失敗時は macro_sentiment=0.0 のフォールバックで継続。
    - 再試行ポリシー、クリッピング、スレッショルド（BULL_THRESHOLD, BEAR_THRESHOLD）などを実装。

- データプラットフォーム（kabusys.data）
  - ETL 基盤
    - pipeline モジュール: 差分取得、保存（idempotent）、品質チェックのワークフローに対応する ETLResult を実装（dataclass）。
    - ETLResult に品質問題・エラー収集・サマリ変換（to_dict）を実装。
    - 差分取得のための内部ユーティリティ（テーブル存在チェック、最大日付取得など）。
  - カレンダー管理（calendar_management）
    - market_calendar に基づく営業日判定ユーティリティ群を実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB データが不十分な場合は曜日ベースでフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants からの差分取得と market_calendar への冪等保存（バックフィル・健全性チェックを含む）。
    - 最大探索日数やバックフィル・先読み等の運用パラメータを定義（可読な定数として管理）。

- 研究用モジュール（kabusys.research）
  - factor_research
    - Momentum, Volatility, Value 等の定量ファクター計算関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA の乖離）
      - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、avg_turnover、volume_ratio
      - calc_value: PER（price / EPS）、ROE（raw_financials から最新レコードを取得）
    - DuckDB SQL を活用した効率的な実装とデータ不足時の None 帰還。
  - feature_exploration
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を使用）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（同順位は平均ランク）。
    - rank: 同順位処理を含むランク変換ユーティリティ。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算する統計サマリ。

- テスト・運用に配慮した設計
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - DuckDB を主要データストアとして利用（テーブル名の期待: prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）。
  - OpenAI クライアント呼び出しの差替（patch）ポイントを提供してユニットテストを容易化。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 破壊的変更
- なし（初回リリース）

### セキュリティ
- なし（初回リリース）

### 運用上の注意（重要）
- 必要環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI API を使う機能（news_nlp / regime_detector / score_news / score_regime）を利用する場合は OPENAI_API_KEY が必要。
- .env 自動読み込みはプロジェクトルート検出に .git または pyproject.toml を使用するため、配布後の実行環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定するか、明示的に環境変数を渡すことを推奨。
- DuckDB スキーマはモジュール実装で前提となるテーブル構造・カラムを要求する（ETL 実行前にスキーマの準備が必要）。
- OpenAI 呼び出しは外部 API であるためレート制限・費用に注意。失敗時はフェイルセーフで継続するが、想定外の挙動を避けるためログ監視を推奨。
- calendar_update_job 等は J-Quants クライアント（kabusys.data.jquants_client）に依存するため、該当クライアントの実装と認証情報の用意が必要。

---

脚注:
- 本 CHANGELOG は提供されたソースコードの内容・コメントから推測して作成しています。実際のリリースノートは機能要件や API 仕様（外部クライアント実装等）に基づき適宜補足してください。