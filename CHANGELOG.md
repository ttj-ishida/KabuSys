# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。  

現在のリリース: 0.1.0

[Unreleased]: https://example.com/kabusys/compare/release...HEAD
[0.1.0]: https://example.com/kabusys/releases/tag/v0.1.0

## [0.1.0] - 2026-03-27

Added
- パッケージ基盤
  - パッケージ初期化を追加（kabusys.__init__）し、公開サブパッケージを定義（data, strategy, execution, monitoring）。
  - バージョン情報を `__version__ = "0.1.0"` として固定。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env / .env.local の読み込み順序を実装（OS 環境変数優先、.env.local は上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - 複雑な .env 行パーサを実装（export プレフィックス、クォート内エスケープ、インラインコメント処理など）。
  - Settings クラスを追加し、アプリケーション設定をプロパティで提供（J-Quants / kabu ステーション / Slack / DB パス / env/log level 判定等）。
  - 必須環境変数未設定時に明確なエラーメッセージを投げる `_require` 実装。
  - env 値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の許容値検証）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティ（calc_news_window）。
    - 1 銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）によるトリム実装。
    - バッチ処理（最大 20 銘柄/API 呼び出し）・レスポンス検証・数値クリッピング（±1.0）を実装。
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
    - API 呼び出し部分はテスト時にモック差し替え可能（_call_openai_api を patch 可能）。
    - エラー時は例外を投げずにその銘柄チャンクをスキップするフェイルセーフ設計。
    - スコアの検証ロジック（JSON 抽出、results 配列形式、未知コード無視、数値検査）を実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする処理を実装。
    - マクロニュースの抽出（マクロキーワード群によるフィルタ）と LLM によるセンチメント評価を実装。
    - LLM 呼び出し時のリトライ / フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - lookahead バイアスを防ぐ設計（target_date 未満のデータのみを使用、datetime.today() を直接参照しない）。
    - OpenAI クライアント生成を外部キーから解決（api_key 引数または OPENAI_API_KEY 環境変数）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）の夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants API から差分フェッチ→冪等保存。
    - 営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーがない/未登録日の場合の曜日ベースのフォールバック（週末は取引なし）を一貫して適用。
    - 最大探索日数などの安全措置（_MAX_SEARCH_DAYS, 健全性チェック）を実装。
    - market_calendar の NULL 値検出時に警告を出す挙動を追加。

  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを導入し、ETL 実行結果（取得件数、保存件数、品質問題、エラー）を構造化して提供。
    - 差分更新、バックフィル、品質チェックの実行設計を反映したユーティリティ群（内部関数: テーブル存在チェック、最大日付取得、トレーディングデイ調整等）を実装。
    - J-Quants クライアントとの連携を前提にした設計（jq.fetch_* / save_* の呼び出し）とエラー安全化（例外捕捉とログ記録）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン, ma200_dev）、Volatility（20日 ATR, atr_pct, avg_turnover, volume_ratio）、Value（PER, ROE）などの定量ファクター計算関数を実装。
    - DuckDB を用いた SQL + Python のハイブリッド実装により大量データの効率的処理を実現。
    - データ不足時の None 扱い、結果は (date, code) キーをもつ dict のリストで返却。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン対応、入力検証、1 クエリでの取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマン順位相関を実装（ties は平均ランクで処理）。
    - ランク変換ユーティリティ（rank）およびファクター統計サマリー（factor_summary）を実装。
    - pandas に依存せず標準ライブラリ + DuckDB で完結する設計。

- ロギング / エラーハンドリング
  - 各モジュールで詳細なログ出力を追加（info/debug/warning/exception）。
  - API 呼び出しに対してはリトライ・バックオフ・フェイルセーフ（スコア 0.0 へのフォールバック等）を採用し、部分失敗時でも全体処理を継続可能に設計。

- テスト容易性
  - OpenAI API 呼び出し部（news_nlp._call_openai_api, regime_detector._call_openai_api）をモック差し替え可能に実装してユニットテストを容易化。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- .env 自動読み込み時に OS 環境変数を保護する仕組みを実装（読み込み時に既存の os.environ キーを protected として扱い、.env の上書きを制御）。
- 必須トークン・シークレット（OpenAI/J-Quants/Slack/Kabu API）の未設定時に明確なエラーを出すことで誤設定を防止。

Notes / 設計方針（重要）
- ルックアヘッドバイアス回避: 全ての AI / リサーチ処理は datetime.today()/date.today() を直接参照せず、外部から渡された target_date に基づいて処理する設計。
- DuckDB をデータ基盤として想定し、SQL を使って大量時系列データを効率的に処理する方針。
- OpenAI（gpt-4o-mini）の JSON Mode を利用し、厳格なレスポンス検証とフォールバックを組み合わせて安定稼働を目指す。

今後の予定（非網羅）
- strategy / execution / monitoring サブパッケージの実装（自動売買ロジック・発注エンジン・監視アラート統合）。
- ETL の詳細な品質チェックルール拡張とモニタリング機能の強化。
- CI / テストカバレッジの追加とドキュメント整備。

---

（この CHANGELOG はコードベースから推測して作成した初回リリース記録です。実際のリリースノート作成時は変更点・リリース日を適宜調整してください。）