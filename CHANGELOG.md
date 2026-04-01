# Changelog

すべての重要な変更点はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに準拠しています。  
安定版の互換性方針はセマンティックバージョニングに従います。

---

## [Unreleased]

- なし

---

## [0.1.0] - 2026-04-01

初回リリース。日本株自動売買プラットフォームのコア機能を実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ基盤
  - パッケージ名: `kabusys`、バージョン 0.1.0（src/kabusys/__init__.py）。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ で定義。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイル自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml を検索）。CWD に依存しない探索を実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - Settings クラスを提供: J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム環境（KABUSYS_ENV）などのプロパティを環境変数から取得し、必須パラメータ未設定時に ValueError を送出するユーティリティを実装。
  - 有効値チェック: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証。

- データ関連 (`kabusys.data`)
  - ETL 結果データクラス `ETLResult` の公開（kabusys.data.etl が pipeline.ETLResult を再エクスポート）。
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分取得、バックフィル、品質チェック（quality モジュールと連携）を想定した ETL 設計。
    - ETLResult: 実行結果の集約、品質問題のシリアライズ、エラー判定ユーティリティを実装。
    - DuckDB を利用したテーブル存在確認や最大日付取得などのユーティリティ関数。

  - 市場カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job`（J-Quants から差分取得して market_calendar テーブルへ冪等保存）。
    - 営業日判定 API: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を提供。
    - DB にカレンダー情報がない・一部欠損時のフォールバックロジック（曜日ベース、土日を非営業日扱い）を実装。
    - 最大探索日数（_MAX_SEARCH_DAYS）やバックフィル・健全性チェックを実装して無限ループや極端な将来日付を防止。

- 研究（Research）モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算する `calc_momentum`。
    - Volatility/Liquidity: 20日 ATR, ATR 比率, 20日平均売買代金, 出来高比率を計算する `calc_volatility`。
    - Value: EPS/ROE に基づく PER/ROE を計算する `calc_value`（raw_financials の最新レコードを target_date 以前から取得）。
    - SQL + DuckDB による実装。結果は (date, code) を含む dict のリストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 `calc_forward_returns`（デフォルト horizons=[1,5,21]、ホライズン検証あり）。
    - IC（Spearman ランク相関）計算 `calc_ic`（None 値や小サンプル時のハンドリング）。
    - ランク変換ユーティリティ `rank`（同順位は平均ランク、丸めで ties を安定化）。
    - 統計サマリー `factor_summary`（count/mean/std/min/max/median の算出）。
  - 研究用モジュールは外部発注 API に依存せず、DuckDB 上の価格・財務データのみを利用する設計。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを取得。
    - バッチサイズ、トリム（_MAX_CHARS_PER_STOCK）、最大記事数、JSON Mode を利用した応答パースを実装。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）は指数バックオフで実行。部分失敗を考慮して ai_scores テーブルへは取得済みコードのみ置換（DELETE → INSERT）して部分障害時の被害を限定。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results キー、コード整合性、スコア数値化、±1.0 にクリップ）。
    - テスト容易化のため _call_openai_api をモジュール内で独立実装し patch による差し替えを想定。
    - 時間ウィンドウ計算 `calc_news_window`（JST ベース、UTC へ変換して DB の datetime と比較）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime を判定・保存する `score_regime`。
    - マクロキーワードフィルタで raw_news からタイトルを抽出し、OpenAI（gpt-4o-mini）で macro_sentiment を取得。
    - LLM 呼び出しは独立実装（news_nlp と共有しない）で、リトライ/フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - レジームスコアはクリップ後に閾値で "bull"/"neutral"/"bear" に分類し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計。

- 監視・その他
  - Settings に監視用閾値（CPU/MEM/DISK）や PID ファイルパス、DB パス等をプロパティとして用意。
  - Slack 用環境変数（SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を必須として定義（通知連携想定）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数から API キー等を取得する設計のため、必須キー（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）が未設定の場合は ValueError を送出して早期に検出します。
- .env の自動読み込みはオプトアウト可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

### Notes / Known limitations / Migration
- OpenAI の呼び出しは gpt-4o-mini（JSON Mode）を前提としています。将来モデルを変更する際は各モジュール内の _MODEL 定数とレスポンス検証ロジックを更新してください。
- DuckDB バージョン依存の挙動（executemany の空パラメータ等）を考慮した実装になっています。DuckDB バージョン差異に起因する問題が起きた場合は pipeline/calendar/ai モジュールの該当箇所を確認してください。
- 研究モジュールは外部 API に影響を与えない設計です（安全にローカルで解析可能）。
- news_nlp と regime_detector は相互にプライベート関数を共有せず、それぞれ独立した _call_openai_api 実装を持ち、テストの差し替えを想定しています。

---

開発に関する問い合わせやバグ報告、改善提案は issue にてお願いします。