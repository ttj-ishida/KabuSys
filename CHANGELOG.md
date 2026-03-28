Keep a Changelog に準拠した CHANGELOG.md（日本語）を作成しました。コードから推測できる機能や設計上の注意点をまとめています。

以下をファイル内容としてお使いください。

---
# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に従い、セマンティックバージョニングを採用します。

## [Unreleased]
- 今後の変更をここに記載します。

## [0.1.0] - 2026-03-28
最初の公開リリース。プロジェクトのコア機能を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化とバージョン情報（__version__ = "0.1.0"）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で列挙。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルと OS 環境変数の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みの無効化対応（テスト向け）。
  - .env のパース機能を強化:
    - コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - _load_env_file による既存環境変数保護（protected set）と override フラグの実装。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得:
    - J-Quants / kabu-station / Slack / DB パスなどの設定プロパティ。
    - env（development/paper_trading/live）と log_level の値検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
  - 必須環境変数未設定時は ValueError を投げる _require ヘルパー。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news: ニュース記事を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores テーブルへ書き込む。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を実装。
    - 1銘柄あたりの記事数と文字数の上限を導入しトークン膨張を抑制（チャンク単位で最大20銘柄をAPIコール）。
    - JSON Mode を利用し厳密な JSON レスポンスを期待。レスポンスのバリデーションとクリッピング（±1.0）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - API 呼び出し部分はテスト用にモック差し替え可能（_call_openai_api を patch 可能）。
    - DB 書き込みは部分失敗に備え「対象コードのみを DELETE → INSERT」することで既存スコアを保護。
  - regime_detector.score_regime: ETF（1321）の200日MA乖離とニュースセンチメントを重み合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200 の算出（ルックアヘッドを排除するため target_date 未満のデータのみ使用）。
    - マクロキーワードで raw_news を抽出し LLM で macro_sentiment を算出（記事なし、API失敗時はフェイルセーフで 0.0）。
    - 重み合成（70%: MA, 30%: macro）、閾値設定に基づくラベル付与。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - API 呼び出しとエラーハンドリングは news_nlp と独立した実装（モジュール結合を避ける）。

- データプラットフォーム（kabusys.data）
  - calendar_management: JPX カレンダー管理と営業日ロジック
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得の際は曜日ベース（平日）でのフォールバック。
    - _MAX_SEARCH_DAYS 等の安全上限で無限ループ回避。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等に保存（バックフィル、健全性チェックを含む）。
  - pipeline / etl
    - ETLResult dataclass を公開（kabusys.data.etl から再エクスポート）。
    - pipeline モジュールにより差分取得・保存・品質チェックの基盤を提供（_get_max_date, _table_exists 等のユーティリティ実装）。
    - デフォルトのバックフィル動作、品質チェックの収集（重大度フラグ）をサポート。

- 研究用ユーティリティ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離の算出（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を算出（不足時は None）。
    - calc_value: raw_financials を参照して PER / ROE を算出（EPS が 0/欠損時は None）。
    - DuckDB の SQL ウィンドウ関数を多用し、データ整合性を考慮。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（horizons の妥当性チェックあり）。
    - calc_ic: スピアマンランク相関（IC）をコードマッチング後に算出（有効レコードが少ない場合は None）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクを採用するランク変換ユーティリティ（丸めによる ties 対応）。

- テスト・開発支援
  - OpenAI API 呼び出し箇所は各モジュール内で _call_openai_api をラップしており、unit test で簡単に差し替え可能。
  - 日時取得の直接参照（datetime.today()/date.today()）を避ける設計により、ルックアヘッドバイアスを排除しやすい実装。

### 修正 (Changed)
- N/A（初回リリース）

### 修正 (Fixed)
- N/A（初回リリース）

### 既知の注意事項 / 設計上の決定
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY が必須。未設定時は ValueError を発生させる。
- AI 部分はレスポンスパース失敗や API エラー時にはスキップまたはデフォルト値（0.0）にフォールバックする設計（安全重視）。
- DuckDB への書き込みは冪等性を重視し、部分失敗時に既存データを不必要に消さない実装になっている。
- .env の自動ロードはプロジェクトルートの検出に依存するため、配布後やインストール後の挙動に注意（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
- news_nlp と regime_detector は OpenAI 呼び出しロジックをモジュール内で独立実装しており、実装の重複はあるがモジュール結合を避け、テスト容易性を高めている。

---

（必要であれば、各モジュールごとの詳細な変更履歴や、将来のリリース向けの TODO / 改善点を追加します。）