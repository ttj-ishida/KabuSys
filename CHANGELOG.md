# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティック バージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。
- 設定・環境変数管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env の行パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境モード（development/paper_trading/live）などを取得。値検証（env, log_level）のためのバリデーションを実装。
- AI ニュース分析（kabusys.ai.news_nlp）
  - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してセンチメント（-1.0〜1.0）を取得。
  - タイムウィンドウ定義（JST ベース、前日 15:00 ～ 当日 08:30 相当）と calc_news_window ユーティリティを提供。
  - バッチサイズ、最大記事数、文字数トリム、最大リトライ（Exponential backoff）等の実装により堅牢な API 呼び出しを実現。
  - レスポンスの厳密なバリデーション（JSON 抽出・results 配列・code/score チェック）とスコアのクリップ（±1.0）。
  - DuckDB への書き込みは部分書換え（該当 code の DELETE → INSERT）で冪等性を確保。DuckDB 0.10 互換のため executemany の空リスト対策あり。
  - テスト容易性のため _call_openai_api を patch 可能に設計。
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定。
  - ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）。データ不足時は中立値を採用。
  - マクロ記事の抽出、OpenAI 呼び出し（gpt-4o-mini）による JSON 出力の解析、API エラー時のフォールバック（macro_sentiment = 0.0）、リトライとバックオフを実装。
  - 合成後のスコアはクリップされ、閾値によりラベルを決定。結果は market_regime テーブルへトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等書き込み。
- 研究用ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）等を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）等を計算。
    - calc_value: raw_financials から直近財務を取得し PER / ROE を計算（EPS が 0/欠損の場合は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを一度に計算。
    - calc_ic: factor_records と forward_records を code で突合し、Spearman のランク相関（IC）を計算。有効データが 3 件未満なら None を返す。
    - rank: 同順位は平均ランクで処理（丸めによる ties を防止）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリユーティリティ。
  - zscore_normalize は kabusys.data.stats から利用可能（research パッケージで再エクスポート）。
  - すべての研究モジュールは DuckDB を直接参照し、外部発注 API や本番口座にはアクセスしない設計。
- データ基盤（kabusys.data）
  - calendar_management:
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーがない場合は曜日ベース（土日を非営業日）でフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants から差分取得して market_calendar を更新（バックフィル、健全性チェック、ON CONFLICT 相当の保存）。
  - pipeline / etl:
    - ETLResult データクラスを導入し、ETL の取得数・保存数・品質問題・エラーを集約して返却。
    - pipeline では差分更新・保存（jquants_client 経由）・品質チェックを行う方針を実装（設計に基づく）。
  - jquants_client（参照）経由でのデータ取得・保存を想定した設計（実装は別モジュール）。
- DuckDB をデータ層の主要 DB として活用。SQL と Python を組み合わせた計算を実行。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Deprecated
- 初版のため該当なし。

### Removed
- 初版のため該当なし。

### Security
- 環境変数による API キー管理を想定。OpenAI API キー（OPENAI_API_KEY）を直接参照する処理があるため、運用時は適切なシークレット管理を推奨。
- .env 自動読み込みでは既存 OS 環境変数を保護する設計（protected set）を採用。

---

注記:
- 多くの外部 API 呼び出し（OpenAI, J-Quants 等）や DB 書き込みはフェイルセーフを重視しており、API 失敗時はフォールバックやスキップで処理継続する設計です。  
- 時間ウィンドウや日付処理は「ルックアヘッドバイアス防止」の方針に従い、内部で datetime.today()/date.today() に依存しない実装が意識されています（ただし calendar_update_job 等一部は実行時の日付参照あり）。