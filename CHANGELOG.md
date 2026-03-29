# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
安定版リリース・変更履歴はセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-29

初期リリース。本パッケージは日本株のデータ取得・ETL・特徴量計算・AI によるニュース解析・市場レジーム判定までをカバーする自動売買／リサーチ基盤の基本機能を提供します。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基本設定
  - kabusys パッケージ初期化（__version__ = 0.1.0）。主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定・ロード機能（kabusys.config）
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索し判定（CWD に依存しない）。
  - .env 行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ等に対応）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを実装し、J-Quants／kabuステーション／Slack／DB パス／動作環境（development/paper_trading/live）等のプロパティを提供（必須項目は未設定時に ValueError を送出）。
  - DUCKDB/SQLite のデフォルトパス設定をサポート。

- AI: ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約し、銘柄ごとのニュース全文（タイトル＋本文）を LLM（gpt-4o-mini）へ送信してセンチメントスコアを取得する score_news を実装。
  - ニュース収集ウィンドウは target_date の「前日 15:00 JST ～ 当日 08:30 JST」に基づき UTC に変換する calc_news_window を提供。
  - バッチ処理: 最大 _BATCH_SIZE（デフォルト 20）銘柄ずつ API に送信、1 銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - JSON Mode を利用し厳密な JSON レスポンスを期待。レスポンスのバリデーション (_validate_and_extract) を行い、スコアを ±1.0 にクリップして ai_scores テーブルへ安全に書き込む（DELETE→INSERT）。
  - API エラー（429、ネットワーク、タイムアウト、5xx）に対する指数バックオフリトライを実装。致命的でない失敗はスキップして処理継続するフェイルセーフ設計。
  - テスト容易化のため、OpenAI 呼び出しは _call_openai_api を通じて行う（unittest.mock.patch で差し替え可能）。

- AI: 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
  - ma200 の計算（直近 200 行の終値、lookahead バイアス回避のため target_date 未満のデータのみ使用）と、raw_news からマクロキーワードに一致するタイトルを抽出する処理を含む。
  - マクロキーワードは日本・米国・グローバルの主要用語を列挙（デフォルトリストを内包）。
  - OpenAI 呼び出しは独立実装、retry/backoff と JSON パースによる堅牢な処理。API 失敗時は macro_sentiment を 0.0 にフォールバック（例外を投げず継続）。
  - 結果は market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して上位へ例外を伝播。

- Research（kabusys.research）
  - ファクター計算群（factor_research）を実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）・相対 ATR（atr_pct）・平均売買代金・出来高比率を計算。
    - calc_value: raw_financials の直近財務を取得して PER / ROE を計算（EPS 欠損や 0 の場合は None）。
  - feature_exploration を実装:
    - calc_forward_returns: 将来リターン（任意ホライズン）を LEAD により一括算出（デフォルト [1,5,21]）。
    - calc_ic: factor と将来リターンの Spearman ランク相関（IC）を算出。サンプル不足時は None。
    - rank: 同順位は平均ランク扱い（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - 研究ユーティリティは DuckDB 接続を受け取り、外部 API やトレード実行を行わない設計。

- Data / ETL（kabusys.data）
  - calendar_management:
    - market_calendar を元にした営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - market_calendar 未取得時は曜日ベース（土日除外）でフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants API から差分取得し market_calendar を冪等保存。バックフィルと健全性チェック（未来日チェック）を実装。
  - pipeline / ETL:
    - ETLResult データクラスを導入し、ETL 実行結果（取得数、保存数、品質問題リスト、エラーリスト等）を構造化して返却・ログ可能に。
    - _get_max_date、_table_exists 等のヘルパーを実装。差分更新・バックフィルの設計方針に沿うインフラを提供。
  - etl モジュールで ETLResult を再エクスポート。

- テスト性・安全設計
  - datetime.today()/date.today() を解析ロジック内部で直接参照しない設計（すべて target_date ベース）によりルックアヘッドバイアスを防止。
  - OpenAI 呼び出し・DB 書き込みは冪等性・部分失敗時の保護（コード絞込み、個別 DELETE → INSERT）を考慮。
  - 各所でログ・警告を充実させ、異常時はスキップ＋警告や明示的な例外により上位制御が可能。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 注意点 / 既知の制約 (Notes / Known issues)
- OpenAI API キー（OPENAI_API_KEY）が必須の処理（score_news, score_regime）。未設定時は ValueError を送出。
- DuckDB のバージョン差異に依存しないよう executemany の空リストチェック等を実装しているが、環境差異による動作確認は必要。
- news_nlp / regime_detector は外部 API（OpenAI、J-Quants）に依存するため、API 利用制限やレスポンス仕様変更に影響を受ける可能性がある。
- 現時点で Strategy / execution / monitoring などのサブパッケージはエクスポート名が準備されているが、実行側統合や実口座接続については本リリースで直接発注する機能は含まれていない（安全設計）。

---
今後の予定（例）
- モデルやプロンプトの改善、ニューストリミングの最適化
- ai_scores / market_regime のダッシュボード監視連携（Slack 通知等）
- ETL のジョブスケジューリングとモニタリング拡張

ご要望があれば、この CHANGELOG を英語版に翻訳したり、各変更に対応する Issue / PR 番号を追加する形で拡張します。