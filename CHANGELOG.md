# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース

### Added
- パッケージの基本構成
  - kabusys パッケージを初版として公開。パブリック API として data / strategy / execution / monitoring をエクスポート。

- 環境設定 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする機能を実装。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルパーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - 既存の OS 環境変数を保護するための protected キー処理と、.env.local による上書きルールを実装。
  - Settings クラス提供。主要設定のプロパティを環境変数から取得（J-Quants / kabu API / LINE / DB パス / 監視閾値 / ログレベル / 環境種別など）。
  - 必須設定取得時の検証（_require が未設定時に ValueError を送出）、KABUSYS_ENV と LOG_LEVEL の許容値チェック、便利な is_live/is_paper/is_dev プロパティ。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols をもとに銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出する score_news を実装。
    - JST の業務ウィンドウ（前日15:00〜当日08:30）を UTC に変換する calc_news_window 実装。
    - バッチ単位（最大20銘柄）、1銘柄あたりの記事上限・文字上限を設定してトリムする仕組みを実装。
    - API 呼び出し時のリトライ（429、接続エラー、タイムアウト、5xx）や指数バックオフを実装。レスポンス JSON の妥当性検証、スコアの ±1.0 クリップ。
    - スコアを書き込む際は部分失敗時に既存スコアを保護するため、対象コードを限定して DELETE → INSERT の冪等保存を実施。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily から ma200_ratio を計算し、raw_news からマクロキーワードで記事を抽出して OpenAI に送信、復帰値を合成して market_regime テーブルへ冪等書き込みを行う。
    - API エラー時はフェイルセーフとして macro_sentiment=0.0 を採用して継続する設計。
    - OpenAI API 呼び出し回りはリトライ、エラー種別のハンドリング、JSON パースの堅牢化を実装。
    - ルックアヘッドバイアス防止のため内部で datetime.today()/date.today() を参照しない設計（呼び出しは target_date を明示）。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）などモメンタム系ファクターを DuckDB SQL で計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等を計算。true_range の NULL 伝播制御などを考慮。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS=0 または欠損時は None）。
    - すべて DuckDB 接続を受け取り SQL＋Python で実行。外部 API にアクセスしない設計。
  - feature_exploration モジュール
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを取得するための汎用関数（ホライズンのバリデーションあり）。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸めにより ties 検出漏れを軽減）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算するユーティリティ。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - JPX カレンダー管理機能（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar の有無に応じた DB 優先ルールと曜日ベースのフォールバック設計。
    - calendar_update_job: J-Quants API からの差分取得（バックフィル / 健全性チェックを含む）と market_calendar への冪等保存処理を実装（jquants_client 経由）。
  - pipeline / ETL
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題リスト・エラーの収集、has_errors / has_quality_errors / to_dict を提供）。
    - pipeline モジュールで差分取得・保存・品質チェックのフロー設計（backfill、品質チェックは致命的エラーを検出しても ETL 自体は継続して問題を集約する方針）。
    - data.etl で ETLResult を再エクスポート。

### Security
- 特になし

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Breaking Changes
- 初回リリースのため該当なし

---

注意事項 / 実装上の設計方針（簡潔）
- 多くの処理（AI 呼び出し、ETL、カレンダー更新）は外部 API エラーに対してフェイルセーフになっており、可能な限り例外を内部で吸収して継続する設計です。運用時はログや ETLResult の errors / quality_issues を監視してください。
- 日付に関する関数はルックアヘッドバイアス防止のため target_date を明示的に受け取り、内部で date.today() を参照しない設計です。
- OpenAI 呼び出し部分はテスト容易性のため差し替えやモックができる実装になっています（内部 _call_openai_api を patch 可能）。
- DuckDB の executemany 空リスト制約等の実運用上の留意点に対応する実装を行っています。

（以降のバージョンでは各機能の安定化、追加の戦略・実行モジュール・監視機能の拡張、ドキュメント整備などを予定しています。）