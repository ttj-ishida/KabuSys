# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

なお本 CHANGELOG は、リポジトリ内のソースコード（src/kabusys 以下）を解析して推測した変更点・機能一覧です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-03

### 追加 (Added)
- パッケージ初版リリース: kabusys v0.1.0
  - パッケージ識別子: src/kabusys/__init__.py にて __version__ = "0.1.0"
  - 公開モジュール: data, strategy, execution, monitoring（__all__）
- 環境設定・ロード機能（kabusys.config）
  - プロジェクトルートの自動検出（.git または pyproject.toml）に基づく .env / .env.local の読み込み機能を追加。
  - .env の行パーサを実装（コメント・export プレフィックス・クォート・エスケープ対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
  - OS 環境変数を保護する protected 上書き制御、override フラグ対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / システム環境等のプロパティを環境変数から取得（必要変数未設定時は ValueError を送出）。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（有効値チェック）。
- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini）を利用して銘柄ごとのセンチメント（-1.0〜1.0）を算出する score_news を実装。
  - ニュース収集ウィンドウ（JST 前日 15:00 ～ 当日 08:30）を計算する calc_news_window を提供（UTC 換算で DB 比較に使用）。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1銘柄あたりの記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - OpenAI 呼び出しに対する指数バックオフによるリトライ（429/ネットワーク/タイムアウト/5xx 対応）。
  - レスポンスの厳密な JSON バリデーション、結果のクリップ（±1.0）、ai_scores テーブルへの冪等的書き込み（DELETE → INSERT）。
  - テスト容易性のため _call_openai_api を patch して差し替え可能に設計。
- マーケットレジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - ma200_ratio 計算（ルックアヘッド回避: target_date 未満のデータのみ使用）とマクロキーワードフィルタ、OpenAI 呼び出し、スコア合成、market_regime への冪等書き込みを実装。
  - API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装。
  - OpenAI 呼び出しのリトライ制御（429/ネットワーク/タイムアウト/5xx）と JSON パース安全化。
- リサーチ（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離率（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率など。
    - calc_value: raw_financials を用いた PER・ROE の算出（最新の報告日以前の財務データを使用）。
    - DuckDB を用いた SQL 実装で prices_daily / raw_financials のみ参照し、本番取引 API へはアクセスしない方針。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21]）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。
    - rank, factor_summary: 同順位の平均ランク処理や基本統計量の算出（pandas 非依存）。
- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar ベースの営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 未登録日は曜日ベース（週末除外）でフォールバックする一貫したロジック。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェック（lookahead/backfill/sanity）と jquants_client 経由の保存処理。
  - pipeline / etl:
    - ETLResult データクラス（ETL 実行結果、品質問題・エラー一覧保持）を提供。
    - 差分取得・品質チェックの設計（バックフィル、部分失敗を許容して他データを保護する書き込み戦略）。
  - data/etl.py で ETLResult を再エクスポート。
- 一般
  - DuckDB を主要なローカルデータストアとして使用。
  - ロギングを各処理に導入し、警告・情報ログで異常や処理状況を記録。
  - ルックアヘッドバイアス防止設計: datetime.today() / date.today() を直接参照しない（score_* 系は target_date を明示的に受け取る）。
  - DB 書き込みは冪等性を意識（DELETE → INSERT、ON CONFLICT 方針など）して実装。

### 変更 (Changed)
- 初版のため該当なし（新規追加のみ）。

### 修正 (Fixed)
- 初版のため該当なし。

### 削除 (Removed)
- 初版のため該当なし。

### セキュリティ (Security)
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定。必須未設定時は ValueError を送出し明示的に失敗させる実装により、鍵未設定による誤動作を防止。

---

## 注意・移行メモ（利用者向け）
- 必要な外部サービス・DB テーブル:
  - DuckDB 上のテーブル: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などが想定されます。ETL/pipeline での事前作成・マイグレーションを推奨します。
  - J-Quants API、OpenAI API（gpt-4o-mini）を利用する処理があります。OPENAI_API_KEY および J-Quants の認証情報を環境変数で設定してください。
- 環境変数自動ロード:
  - プロジェクトルート（.git または pyproject.toml）検出に成功すると .env を自動で読み込みます（.env → .env.local の順で読み込み、.env.local は上書き）。
  - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- テスト可能性:
  - OpenAI 呼び出し箇所は内部関数 _call_openai_api を patch して差し替え可能です。ユニットテストでのモック注入に対応しています。
- フェイルセーフ:
  - LLM 呼び出し失敗時は基本的にスコアを 0.0 にフォールバックし、処理を継続する設計です（部分失敗時に他データを消さない書き込み戦略を採用）。

---

（この CHANGELOG はソースコードからの推測に基づいて作成しています。実際のリリースノートや運用ルールが別にある場合はそちらを優先してください。）