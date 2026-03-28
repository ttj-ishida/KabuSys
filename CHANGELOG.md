# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

現在の日付: 2026-03-28

## [Unreleased]
（次回リリースまでの未確定の変更はここに記載します）

---

## [0.1.0] - 2026-03-28

初期リリース。以下の主要機能・モジュールを実装しています。設計上の方針やフェイルセーフの振る舞いも含めて記載しています。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開 API として data / strategy / execution / monitoring をエクスポート。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルと環境変数の読み込み機能を実装。
  - 自動ロードの探索はパッケージファイル位置から親ディレクトリを遡って .git または pyproject.toml を基準にプロジェクトルートを特定（CWD に依存しない）。
  - .env のパースは以下に対応：
    - 空行・コメント行（#）を無視
    - export KEY=VAL 形式のサポート
    - シングル/ダブルクォート内のエスケープ処理対応
    - クォートなしの値におけるインラインコメント処理（直前が空白/タブの場合のみ）
  - 読み込み順序: OS 環境変数 > .env.local (上書き) > .env（未設定のキーのみ設定）。
  - OS 環境変数を保護する protected 機構を実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト向け）。
  - Settings クラスを提供し、必須環境変数取得時に未設定なら ValueError を発生させるユーティリティを実装。
  - 主要設定項目（J-Quants / kabu API / Slack / DB パス / env, log level）をプロパティとして提供。KABUSYS_ENV と LOG_LEVEL の値チェック（許容値列挙）を実施。

- データ & ETL 基盤 (kabusys.data)
  - ETL の結果を表す ETLResult データクラスを実装（target_date, fetched/saved カウント, quality issues, errors 等）。
  - pipeline モジュールにて差分更新・バックフィル・品質チェックのフレームワークを実装。
    - デフォルトの backfill 日数・カレンダ先読みなどを定義。
    - テーブルの最大日付取得ユーティリティ、テーブル存在チェックを実装。
    - 品質チェックは重大度情報を含め、致命的なエラーがあっても処理を継続して呼び出し元に報告する設計（Fail-Fast ではない）。

- マーケットカレンダー管理 (kabusys.data.calendar_management)
  - market_calendar を用いた営業日判定ユーティリティを実装:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
  - DB にカレンダーデータがない場合は曜日ベース（土日除外）でフォールバックする一貫した挙動。
  - 最大探索日数 (_MAX_SEARCH_DAYS) による無限ループ防止。
  - calendar_update_job により J-Quants から差分取得して market_calendar を冪等的に保存するジョブを実装。バックフィル（直近 _BACKFILL_DAYS）・健全性チェック（未来日付の異常検知）を備える。
  - DuckDB からの date 値ハンドリングのユーティリティ実装。

- 研究（Research）ツール群 (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
      - データ不足時に None を返す扱い。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
      - true_range 計算は high/low/prev_close の NULL 伝播を厳密に扱う。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS=0 や欠損時は None）。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: target_date から複数ホライズンの将来リターンを一括で取得（LEAD を使用）。
      - horizons の検証（正の整数、<=252）を実装。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。レコード不足（<3）時は None。
    - rank: 同順位は平均ランクを返すランク化ユーティリティ（丸めで ties の検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - 研究モジュールは DuckDB 接続のみを参照し、外部 API/発注を行わない設計。

- AI / NLP モジュール (kabusys.ai)
  - ニュースセンチメント (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価して ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
    - 1 銘柄あたり最大記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - バッチサイズは最大 20 銘柄。リトライ（429/ネットワーク/タイムアウト/5xx）は指数バックオフで再試行。
    - レスポンスの厳密な検証（JSON パース、results リスト、各要素の code/score、既知コード照合、数値チェック）、スコアを ±1.0 にクリップ。
    - 部分失敗に備え、ai_scores の置換は対象 code を限定して DELETE → INSERT（部分失敗時に他銘柄データを保護）。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に実装。
    - API キー未設定時に ValueError を送出。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLMセンチメント（重み30%）を合成して、日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算は target_date 未満のデータのみ使用してルックアヘッドバイアスを排除。
    - マクロニュースは news_nlp の calc_news_window を利用してウィンドウを決定し、マクロキーワードでフィルタしたタイトルを LLM に渡す（上限 20 記事）。
    - OpenAI 呼び出しは専用実装（news_nlp とは別）で、リトライ・バックオフ・API エラー分類（5xx リトライ）を実装。API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフ。
    - レジームスコアは重み付け合成してクリップ。閾値に応じて regime_label を "bull"/"bear"/"neutral" に分類。
    - market_regime テーブルへの書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、エラー時に ROLLBACK を試みる。

- テスト性・設計上の注意点
  - 主要 AI 関数は _call_openai_api を個別に実装し、unittest.mock.patch による差し替えでテスト可能。
  - 全 AI / 研究モジュールは内部で datetime.today()/date.today() を直接参照しない（外部から target_date を注入）ことでルックアヘッドバイアスを防止。
  - DuckDB を主要な永続ストアとして利用（SQL + Python の組合せで計算）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー等の必須機密情報は環境変数経由で取得し、未設定時は明確なエラーを出す設計。

---

注記:
- 本リリースはコードベースからの推測に基づく CHANGELOG です。実際の運用で公開API名や設定名を変更した場合は本 CHANGELOG の内容を適宜更新してください。