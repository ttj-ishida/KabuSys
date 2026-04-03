CHANGELOG
=========

すべての重要な変更は Keep a Changelog の規約に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-03
-------------------

初回公開リリース。以下の主要機能を実装・公開します。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン 0.1.0）。パブリックサブパッケージとして data, strategy, execution, monitoring を __all__ で公開。
- 設定・環境変数管理（kabusys.config）
  - .env ファイル／環境変数からの設定読み込みを実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロード無効化可能）。
  - .env の堅牢なパーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理）。
  - override / protected 機能により OS 環境変数を保護して .env.local で上書き可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視 / システム関連の設定プロパティをラップ。
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL など）とユーティリティプロパティ（is_live / is_paper / is_dev）。
- AI モジュール（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - calc_news_window: スコアリング対象のタイムウィンドウ計算（JST基準 -> UTC naive datetime）。
    - score_news: raw_news, news_symbols を集約して OpenAI (gpt-4o-mini) にバッチ問い合わせし、銘柄毎のセンチメント ai_score を ai_scores テーブルへ冪等的に書き込み。
    - バッチング（最大 _BATCH_SIZE=20 銘柄）、1銘柄ごとの記事トリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）、JSON Mode を用いたレスポンス検証、±1.0 でクリップ。
    - リトライ・バックオフ処理（429/ネットワーク断/タイムアウト/5xx 対象）。API 失敗時はフェイルセーフとして当該チャンクをスキップし、他チャンクは継続。
    - レスポンスバリデーションにより未知コードや不正なスコアは無視。
    - DB 書込みは DELETE → INSERT の方式で部分失敗時に既存データを保護（DuckDB executemany の制約考慮）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime: ETF 1321 の 200 日移動平均乖離率（ma200_ratio）とマクロニュースの LLM センチメントを加重合成（MA: 70%、Macro: 30%）して日次レジーム（bull / neutral / bear）を算出。
    - ETF コード: 1321、MA ウィンドウ: 200、スケール・閾値を設定。
    - マクロニュース抽出はキーワードベース（日本・米国等の主要ワード群）で行い、最大記事数は制限。
    - OpenAI 呼び出しは独立実装。リトライ / エラーハンドリングを実装し、API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - market_regime テーブルへ冪等書き込み（トランザクション: BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar テーブルが存在しない場合の曜日ベースのフォールバック（週末を非営業日扱い）。
    - DB 登録値優先で、未登録日は曜日フォールバックすることで一貫性を維持。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得 → jquants_client 経由で保存、バックフィル・健全性チェック含む）。
  - ETL パイプライン基礎（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを実装（ETL 実行の集計結果・品質問題・エラーの保持、has_errors / has_quality_errors 等のユーティリティ）。
    - パイプライン用ユーティリティ（テーブル存在チェック、最大日付取得等）を実装。差分取得・バックフィル設計方針に対応する基盤コードを用意。
    - kabusys.data.etl で ETLResult を再エクスポート。
  - jquants_client 参照（カレンダー/ETL での外部クライアント使用を想定）。
- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、ma200 の乖離（ma200_dev）を DuckDB SQL で計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。NULL/不足時の扱いに注意。
    - calc_value: raw_financials から最新財務を取得し PER（EPS が有効な場合）・ROE を計算。
    - すべて DuckDB 接続を受け取り、外部 API には依存しない設計。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で計算。horizons のバリデーションあり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコード < 3 の場合は None。
    - rank: 同順位は平均ランクで処理（小数丸めで ties の検出を安定化）。
    - factor_summary: count/mean/std/min/max/median を算出（None を除外）。
  - research パッケージで主要関数を再エクスポート（zscore_normalize は data.stats から）。
- 実装上の設計方針・注意点（全体）
  - ルックアヘッドバイアス防止のため、date.today() / datetime.today() をスコア計算内部で直接参照しない実装方針を採用（target_date 引数ベース）。
  - OpenAI 呼び出しは明示的な API キーの注入を許可（api_key 引数、未指定時は OPENAI_API_KEY 環境変数を参照）。未設定時は ValueError を発生。
  - DuckDB を主要なストレージ/クエリ実行基盤として使用（SQL を多用）。DuckDB バージョン差の互換性を配慮した実装（executemany の空リスト回避等）。
  - ロギングと詳細な WARN/INFO 出力を充実させ、失敗時はできる限りフォールバックして処理継続するフェイルセーフ設計を採用。

Changed
- （初回リリースのため過去バージョンからの変更は無し）

Fixed
- （初回リリースのため無し）

Removed
- （初回リリースのため無し）

Security
- OpenAI API キー / 各種シークレットは環境変数経由で供給する設計。`.env.local` により開発環境での上書きが可能。OS 環境変数は protected として .env による上書きを防止。

Notes / Known limitations
- 実行にあたって:
  - AI 機能（score_news, score_regime）は OpenAI API（gpt-4o-mini）への接続が必須。API キーは api_key 引数または環境変数 OPENAI_API_KEY を設定してください。
  - DuckDB のテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）が事前に存在していることが前提です。
  - strategy / execution / monitoring パッケージは __all__ に含まれていますが、本リリースにおける該当実装は限定的（または別ファイルでの実装を想定）です。
- 将来的な改善案:
  - OpenAI SDK の API 変更やモデル差し替えに備えた抽象化の強化。
  - ETL のジョブ化・スケジューリング、品質チェックのより細かなレポーティング。

問い合わせ
- バグ報告・改善提案はリポジトリの issue をご利用ください。