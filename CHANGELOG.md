# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog のフォーマットに従います。
セマンティックバージョニングを採用します。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-29
初回リリース — 基本的なデータプラットフォーム、リサーチ、AI評価、設定管理のコア実装を追加。

### 追加 (Added)
- パッケージ全体
  - パッケージメタ情報を追加 (kabusys.__version__ = "0.1.0")。
  - パッケージ公開モジュール群の基本構成を定義（data, strategy, execution, monitoring を __all__ に含める）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行うため、CWD に依存しない実装。
  - 高機能な .env パーサを実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ対応、インラインコメント処理）。
  - 環境変数保護（既存 OS 環境変数を protected として扱う上書き制御）をサポート。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能。
    - J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベル判定などのプロパティを含む。
    - KABUSYS_ENV, LOG_LEVEL のバリデーション（許容値チェック）を実装。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。
  - 必須環境変数未設定時には明示的な ValueError を送出。

- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols を集約して銘柄ごとのニュースセンチメントを生成する score_news を実装。
    - ニュース収集ウィンドウ計算 (calc_news_window)：前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して使用。
    - 銘柄毎に最新記事をトリムしてまとめ、最大バッチサイズで OpenAI に送信（_BATCH_SIZE=20）。
    - gpt-4o-mini を JSON Mode（厳密な JSON 出力）で呼び出す。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - API レスポンスのバリデーション（JSON 抽出、results 構造検査、コード整合性、数値チェック、スコアクリップ）を実装。
    - DuckDB 互換性対応：executemany に空リストを渡さないガードを実装。
    - フェイルセーフ: API エラー時はスキップして処理を継続（例外を上げない動作がデフォルト）。
    - score_news は書き込み件数（書込銘柄数）を返す。

- AI 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - ma200_ratio の計算（対象日は排他条件 date < target_date を用いてルックアヘッドを防止）。
    - マクロキーワードによる raw_news フィルタ (_MACRO_KEYWORDS) と記事抽出。
    - OpenAI 呼び出しは専用実装で行い、リトライ・バックオフ・エラー時のフォールバック（macro_sentiment=0.0）を実装。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。

- Research（因子計算・特徴量探索）(kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日 MA 乖離率）を計算。
      - データ不足時は None を返す設計。
    - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio 等のボラティリティ・流動性指標を実装（ATR の NULL 伝播管理等）。
    - calc_value: raw_financials から EPS/ROE を参照して PER/ROE を計算（最新レコード取得ロジックを含む）。
    - DuckDB を用いた SQL ベース実装で、外部 API にはアクセスしないことを保証。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションあり。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装（ties の平均ランク処理含む）。有効データが 3 件未満の場合は None を返す。
    - rank: 同順位は平均ランク化するユーティリティ（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリを返す。
  - research パッケージの __all__ を整備し、外部公開 API を整理。

- Data（データ基盤ユーティリティ）(kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - market_calendar が存在しない場合は曜日ベース（土日除外）でフォールバック。
    - DB 登録値を優先し、未登録日は曜日ベースで補完する一貫性のあるロジック。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）やバックフィル等の安全策を実装。
    - calendar_update_job: J-Quants クライアント経由で差分フェッチ → market_calendar へ冪等保存する夜間バッチ処理を実装。バックフィル日数と健全性チェックを導入。
  - ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー概要などを保持）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得ロジック、マーケットカレンダー補正など。
    - etl モジュールで ETLResult を再エクスポート。
    - 設計上の注意: 差分更新、バックフィル、品質チェックの設計思想を反映。

### 改善 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 非推奨 (Deprecated)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### セキュリティ (Security)
- OpenAI API キーは引数で注入可能かつ環境変数から取得する。キーの取り扱いは呼び出し側で注意すること。

---

補足（設計上の重要な決定・制約）
- ルックアヘッドバイアス対策として、いかなる場所でも datetime.today()/date.today() を直接参照する処理を避け、target_date を明示的に受け取る設計を採用。
- OpenAI 呼び出し部分は単体テスト容易性のため差し替え可能（モジュール内の _call_openai_api を patch 可能）。
- API 失敗時は例外を即投げずにフェイルセーフ（0.0 やスキップ）で継続する箇所が多く、運用上の堅牢性を重視。
- DuckDB のバージョン差分（executemany の空リスト不可等）への互換性対策を実装。
- DB 書き込みはできるだけ冪等に（DELETE→INSERT、ON CONFLICT 相当）行われるよう実装。

（注）
- この CHANGELOG は現状のコードベースの実装内容から推測して作成しています。機能仕様や将来の変更に応じて更新してください。