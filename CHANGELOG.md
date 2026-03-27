# Keep a Changelog

全ての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

なお、本リリース情報は与えられたコードベースから推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-27
初回公開リリース。

### Added
- パッケージ基礎
  - kabusys パッケージを追加。公開 API として data / research / ai / execution / monitoring 等を想定（src/kabusys/__init__.py）。
  - パッケージバージョンを 0.1.0 に設定（__version__）。

- 設定管理
  - 環境変数 / .env ファイル読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して自動で .env / .env.local を読み込む（CWD 非依存）。
    - .env パーサは `export KEY=val` 形式、クォート値（"'/エスケープ）やインラインコメント処理に対応。
    - OS 環境変数を保護する protected 集合を用いた上書き制御（.env.local は override=True）。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、必要な設定値をプロパティ経由で取得（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）。
  - 設定値のバリデーション: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証。

- AI（自然言語処理）
  - ニュースセンチメント集計・保存機能（src/kabusys/ai/news_nlp.py）。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST → UTC に変換）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（記事数・文字数上限でトリム）。
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチ評価（1回最大 20 銘柄）。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - レスポンスの厳密なバリデーション（results 配列、code/score の型・既知コード検査、数値チェック）、スコアを ±1.0 にクリップ。
    - 成功スコアのみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
    - テスト向けに _call_openai_api の差し替えを想定（unittest.mock.patch でモック可能）。
  - 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - マクロニュースはキーワードフィルタで抽出し、OpenAI により JSON 形式で macro_sentiment を取得。
    - API エラーやパース失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - lookahead バイアス防止のため date ベースのクエリ・日付参照設計（datetime.today() を使わない）。

- Research（ファクター・特徴量解析）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER/ROE）などの定量指標を DuckDB を用いて計算。
    - データ不足時は None を返す挙動で安全に処理。
    - 出力フォーマットは (date, code) をキーとする dict リスト。
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）。
    - 将来リターンの計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）、ランク関数、ファクター統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB で実装。
  - zscore_normalize を data.stats から再エクスポート（src/kabusys/research/__init__.py）。

- Data（ETL / カレンダー）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日ロジックを提供。
    - market_calendar が存在しない場合は曜日ベースでフォールバック（土日非営業）。
    - calendar_update_job により J-Quants から差分取得 → market_calendar に冪等保存。バックフィルと健全性チェックあり。
  - ETL パイプライン（src/kabusys/data/pipeline.py, etl.py）。
    - 差分取得、保存（jquants_client の save_* を想定）および品質チェックフローを定義。
    - ETLResult データクラスを追加（処理概要、品質問題、エラー集約、ユーティリティ to_dict）。
    - バックフィル期間、最小データ日の定義、品質チェックは問題を収集して継続する設計（Fail-Fast ではない）。
  - pipeline の ETLResult を外部公開（src/kabusys/data/etl.py）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数に秘密情報（OpenAI API key, Slack token, kabu パスワード 等）を想定し、Settings で必須チェックを行う。未設定時は ValueError を発生させて明示的に通知。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

---

注記 / 実装上の設計意図・制約（重要）
- すべてのモジュールでルックアヘッドバイアス防止のため、直接 datetime.today() / date.today() を参照しない設計（target_date を明示的に受け取る）。  
- OpenAI への呼び出しは JSON mode（厳密な JSON 出力）を期待。API 応答のパースに失敗した場合はフェイルセーフによりスコア等をスキップまたは 0 にフォールバックする実装。  
- データベース書き込みは可能な限り冪等（DELETE → INSERT や ON CONFLICT を想定）にし、部分失敗時でも既存データの不必要な消失を防ぐ。  
- DuckDB バインディングの互換性（executemany に空リスト不可等）に配慮した実装。  
- 依存: openai SDK / duckdb。テストのため API 呼び出し部分は差し替え可能（内部関数をパッチ可能にしている）。  
- 未実装 / 制限: 現時点で PBR や配当利回り等の一部バリューファクターは未実装。AI スコアは現フェーズで sentiment_score と ai_score を同一視。

もし CHANGELOG に追記したい点（リリース日変更、追加の重要な修正や既知のバグ、リリースノートの体裁変更など）があれば指示してください。