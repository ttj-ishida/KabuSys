# Changelog

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の形式に従います。  

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期バージョンを実装。パッケージバージョンは 0.1.0。
  - パッケージの公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パーサー実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理。
    - 無効行・コメント行のスキップ。
  - 環境変数読み込みの上書き制御（override, protected）を実装。OS 環境変数の保護を考慮。
  - Settings クラスを提供（プロパティ経由で各種必須/任意設定を取得）:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite）等の設定プロパティ。
    - KABUSYS_ENV の値検証（development / paper_trading / live）。
    - LOG_LEVEL の値検証（DEBUG/INFO/...）。
    - 必須設定未定義時は ValueError を送出する _require() を実装。

- AI (kabusys.ai)
  - news_nlp モジュール:
    - raw_news と news_symbols を用い、指定ニュースウィンドウ（前日15:00 JST ～ 当日08:30 JST）を集計して銘柄単位に結合。
    - OpenAI (gpt-4o-mini) の JSON Mode を用いたバッチ処理（最大 20 銘柄/チャンク、1銘柄あたり記事トリム制限あり）。
    - 再試行（429/ネットワーク/タイムアウト/5xx）には指数バックオフを実装、致命的でない失敗時はスキップして継続（フェイルセーフ）。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、コード照合、数値検査）、スコアを ±1.0 にクリップ。
    - 成果を ai_scores テーブルへ冪等的に保存（対象コードのみ DELETE → INSERT）。
    - calc_news_window ユーティリティを公開。
  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出（マクロキーワードリストでフィルタ）、OpenAI 呼び出しは JSON モードで実施。
    - OpenAI API のリトライ・エラーハンドリングを実装（フェイルセーフ時は macro_sentiment=0.0）。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易化のため OpenAI 呼び出しラッパーはモジュール内で独立実装（news_nlp と共有しない）。
  - ai.__init__ で score_news をエクスポート。

- データ基盤 (kabusys.data)
  - calendar_management モジュール:
    - market_calendar に基づく営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar 未取得時には曜日ベース（土日除外）でフォールバック。
    - calendar_update_job を実装: J-Quants API から差分取得し market_calendar を冪等更新、バックフィルと健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを定義（取得数、保存数、品質問題、エラー等を格納）。
    - ETL 処理の補助関数（テーブル存在チェック、最大日付取得、トレーディング日調整など）を実装。
    - data.etl で ETLResult を再エクスポート。
  - jquants_client / quality 等外部モジュール連携を想定した設計（フェイルセーフ/部分成功維持を重視）。

- リサーチ (kabusys.research)
  - factor_research モジュール:
    - モメンタム (1M/3M/6M)、200 日移動平均乖離、ATR（20 日）、平均売買代金・出来高比率などのファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 内で SQL により効率的に集計・ウィンドウ関数を利用して実装。
    - データ不足の銘柄に対しては None を返す等の堅牢な取り扱い。
  - feature_exploration モジュール:
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、入力検証あり）。
    - IC（Spearman の ρ）計算 calc_ic（rank を利用、最小有効サンプルチェックあり）。
    - rank ユーティリティ（同順位は平均ランク、丸めで ties 検出安定化）。
    - factor_summary：基本統計量（count/mean/std/min/max/median）計算。
  - research.__init__ で主要 API を再エクスポート（zscore_normalize は data.stats からの再エクスポートを想定）。

### 変更 (Changed)
- 設計上の方針・注意点を README・モジュール docstring レベルで明示:
  - ルックアヘッドバイアス防止のため、score_news / score_regime 等は内部で datetime.today() / date.today() を参照しない（呼び出し側が target_date を指定）。
  - DuckDB の executemany 空リスト制約（0.10 系）を考慮した実装（空リスト時は実行しない）。
  - API 呼び出しのテスト容易化のため _call_openai_api 等を patch 可能に実装。

### 修正 (Fixed)
- 該当なし（初回リリースのためバグ修正履歴は無し）。

### セキュリティ (Security)
- 該当なし。

### 破壊的変更 (Breaking Changes)
- 該当なし（初回リリース）。

---

メモ:
- 実装の多くは DuckDB を前提とした SQL / Python ハイブリッドで記述されており、本番データベースへの冪等保存・フェイルセーフ設計・ロギングが組み込まれています。
- OpenAI（gpt-4o-mini）連携部分は JSON mode を利用し、レスポンスの堅牢な検証と再試行戦略を備えています。テスト時は該当関数をモック差し替え可能です。