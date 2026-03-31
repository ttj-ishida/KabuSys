# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

最新の変更やリリースに関する情報はここを参照してください。

## [Unreleased]
- （今後の変更をここに記載）

---

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買プラットフォームの基礎機能を実装しています。主要なモジュールは DuckDB をデータ基盤として利用し、J-Quants および OpenAI を外部データ／NLP ソースとして統合する設計になっています。

### Added
- パッケージ基盤
  - kabusys パッケージを追加（__version__ = 0.1.0）。公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 設定管理
  - 環境変数／.env 読み込みモジュール（kabusys.config）
    - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export KEY=val 形式やクォート内のバックスラッシュエスケープ、インラインコメント検知などに対応した堅牢なパーサを実装。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DBパス / 監視閾値 / 環境種別などのプロパティ取得と検証（必須変数未設定時は ValueError を送出）。
    - 環境値の検証: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL（DEBUG/INFO/...）のバリデーション。

- データ基盤（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPXカレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants から差分取得 → idempotent 保存。
    - 営業日判定ユーティリティを提供：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 未登録日のフォールバックは曜日ベース（土日非営業）。最大探索日数制限付き（_MAX_SEARCH_DAYS）。
    - 健全性チェック・バックフィル・lookahead の実装。
  - ETL パイプライン（pipeline / etl）
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - 差分更新・バックフィル・品質チェックの設計方針を実装（jquants_client 経由での取得、品質問題は収集して呼び出し元で対処）。
    - DuckDB 上のテーブル存在確認や最大日付取得などのユーティリティを実装。

- 研究用分析（kabusys.research）
  - factor_research モジュールを追加
    - モメンタム（calc_momentum）：1M/3M/6M リターン、200日移動平均乖離を計算。
    - ボラティリティ（calc_volatility）：20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - バリュー（calc_value）：raw_financials から EPS/ROE を取得し PER/ROE を計算。
    - 全て DuckDB の prices_daily / raw_financials のみを参照し、本番の発注 API 等にはアクセスしない設計。
  - feature_exploration モジュールを追加
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを取得。
    - IC（calc_ic）: スピアマンのランク相関に基づく Information Coefficient を計算。
    - ランク（rank）: 同順位は平均ランクを返す実装（丸め処理で ties の漏れを防止）。
    - 統計サマリ（factor_summary）: count/mean/std/min/max/median を算出。
  - zscore_normalize は kabusys.data.stats から利用可能にして再エクスポート。

- AI / NLP（kabusys.ai）
  - ニュースセンチメント（news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大20銘柄/チャンク）、記事トリム（記事数・文字数上限）、指数バックオフによるリトライを実装。
    - レスポンス検証（JSON 抽出・キー検査・型チェック・スコアの有限性）を行い、ai_scores テーブルへ idempotent に書き込み（DELETE → INSERT）。
    - API キーは引数で注入可能（テスト容易化）。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を送出。
    - 失敗時は該当チャンクをスキップしプロセス継続するフェイルセーフ設計。
  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225 連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - news_nlp の calc_news_window を利用してニュースウィンドウを決定、OpenAI を呼ぶ際は独立実装の内部呼び出し関数を使用してモジュール結合を最小化。
    - API エラーやパースエラー時は macro_sentiment = 0.0 にフォールバックして継続。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- 安全性・テスト性
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() の直接参照を避ける設計（各関数は target_date を引数に取り時間窓を計算）。
  - OpenAI 呼び出し部分はテストで差し替え可能（_call_openai_api を patch する等）。
  - DuckDB の executemany 周りの互換性（空リストバインド回避）を考慮した実装。

### Changed
- 初版リリースのため該当なし。

### Fixed
- 初版リリースのため該当なし。

### Security
- 機密情報の取り扱い
  - OpenAI APIキー、J-Quants トークン、Kabu API パスワード、Slack トークン等は環境変数経由で管理。必要変数が未設定の場合は明示的に例外を投げる（早期検出）。
  - .env 自動読み込みの際、既存 OS 環境変数を保護する仕組み（protected set）を導入。

---

注記:
- 本リリースは「データ取得・前処理・研究（因子計算）・ニュース/レジーム判定」の基盤を提供します。実際の発注ロジック（execution）、ストラテジー実行の orchestration、モニタリング周り（Slack 通知やプロセス監視）はパッケージ構成に含まれる名前空間として想定されていますが、本バージョンでは主にデータ処理・分析・NLP のコア部分が実装されています。今後のリリースで実行系・運用系の機能拡張（例: 発注ラッパー、監視ダッシュボード、より詳細な品質チェック等）を予定しています。