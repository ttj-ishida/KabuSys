# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」形式に従います。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォームのコア機能群を実装しました。主な追加点と設計上の要点を以下に示します。

### Added
- パッケージ基盤
  - パッケージ初期化とバージョン管理を追加（kabusys.__version__ = 0.1.0）。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - OS 環境変数を保護する protected バインディングを導入し、.env ファイルの上書き挙動を制御。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベルなどのプロパティを提供（必須項目は未設定時に ValueError を送出）。

- データ層（kabusys.data）
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未登録の際の曜日ベースのフォールバック、最大探索日数制限、DB優先ロジック。
    - calendar_update_job: J-Quants からの差分取得と冪等保存の夜間バッチジョブ。
  - pipeline / etl: ETL パイプライン基盤を実装。
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー情報などを含む）。
    - 差分更新・バックフィル・品質チェックの設計方針を反映。

- 研究（research）
  - factor_research: 定量ファクター計算を実装（Momentum / Value / Volatility / Liquidity）。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から組み合わせて算出。
  - feature_exploration: 将来リターン・IC・統計サマリー機能を実装。
    - calc_forward_returns: 任意ホライズンの将来リターン取得（既定: [1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）を実装、最小有効レコード数チェックあり。
    - rank: 平均ランク（同順位は平均）実装（丸めによる ties 対策あり）。
    - factor_summary: count/mean/std/min/max/median 集計。

- AI / ニュース解析（kabusys.ai）
  - news_nlp.score_news: raw_news と news_symbols から銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
    - 1 銘柄あたり最大記事数・最大文字数によるトリミング、20 銘柄単位バッチ処理。
    - JSON Mode を利用した出力バリデーション、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンス検証（results キー、型チェック、未知コード無視、数値変換、スコアの ±1 クリップ）。
    - DuckDB への書き込みは DELETE（対象コードのみ）→ INSERT の冪等操作（部分失敗時に既存スコア保護）。
  - regime_detector.score_regime: 市場レジーム判定（'bull' / 'neutral' / 'bear'）を実装。
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成。
    - calc_news_window を用いたマクロ記事抽出、OpenAI によるマクロセンチメント評価（gpt-4o-mini、JSON Mode）。
    - API 失敗時のフォールバック（macro_sentiment = 0.0）、リトライロジック、結果のクリップと閾値判定。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- DuckDB を用いた DB 操作全般
  - 各モジュールとも DuckDB 接続を受け取り SQL と組み合わせて処理。
  - 書き込みのトランザクション管理（BEGIN / COMMIT / ROLLBACK）とロギングを徹底。

- 設計上の注意点（ドキュメント化）
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照しない実装方針（target_date を明示的に受け取る）。
  - フェイルセーフ: 外部 API 失敗時は例外を投げずフォールバックまたはスキップして処理を継続する箇所が多い（ログ出力あり）。
  - テスト容易性: OpenAI 呼び出し関数に対して patch しやすい設計（モジュール内でラップした関数を使用）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能で、未指定時は環境変数 OPENAI_API_KEY を参照。API キー未設定時は明確な ValueError を発生させる。

---

注釈:
- 本リリースでは外部クライアント実装（例: jquants_client、kabu ステーションクライアント）が参照されるが、それらの実体はパッケージ外（別モジュール／別パッケージ）として想定されています。
- ロギングや固定定数（バッチサイズ・最大リトライ回数・モデル名等）はソース内定数で管理しており、運用上のチューニング余地を残しています。