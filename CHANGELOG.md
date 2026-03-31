# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
この変更履歴は Keep a Changelog の慣習に従っています。

現在のリリース方針: 初期リリースとして v0.1.0 を公開。以降はセマンティックバージョニングを想定します。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買／データ基盤のコア機能群を実装。

### Added
- パッケージ基本情報
  - kabusys パッケージの初期バージョンを追加（__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に設定。

- 設定管理（kabusys.config）
  - .env ファイルと環境変数からの設定読み込みを自動化。プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を順番にロード。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサは export 形式、シングル/ダブルクォート、エスケープシーケンス、インラインコメント（スペース/タブ前置）に対応。
  - OS 環境変数を保護する protected ロジック（.env.local は既存 OS 環境をデフォルトで上書きしないが、override フラグで制御）。
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / データベースパス / 環境種別 / ログレベルなど）。必須環境変数未設定時は明確な ValueError を投げる。
  - KABUSYS_ENV と LOG_LEVEL の値検証ロジックを実装（許容値セットのチェック）。 is_live / is_paper / is_dev の便宜プロパティを提供。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント解析（news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに記事テキストをまとめて OpenAI（gpt-4o-mini）に JSON Mode で送信。
    - バッチ処理（最大 20 銘柄／API 呼び出し）と銘柄当たりの記事数・文字数トリム制御（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 429・ネットワーク・タイムアウト・5xx に対する指数バックオフによるリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列/要素検証、数値化、既知コードのみ採用）。
    - スコアは ±1.0 にクリップ。成功分のみを ai_scores テーブルへ（DELETE → INSERT の冪等処理）。
    - ルックアヘッドバイアス防止（target_date を受け外部時刻参照を行わない）やフェイルセーフ（API 失敗時はそのチャンクをスキップ）。

  - 市場レジーム判定（regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム ('bull'/'neutral'/'bear') を判定。
    - prices_daily から target_date 未満のみで MA を算出し、ルックアヘッドを防止。
    - raw_news からマクロ指標に紐づくタイトルを抽出し（キーワードリスト）、OpenAI へ送信して macro_sentiment を取得。
    - OpenAI 呼び出しは専用ラッパーを用意し、429・ネットワーク・タイムアウト・5xx に対してリトライとフォールバック（失敗時 macro_sentiment=0.0）。
    - 合成スコアをクリップし、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーを扱うロジックを実装。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が存在しない場合は曜日ベース（土日除外）でフォールバック。DB 登録がある場合は DB 値を優先し未登録日は一貫した曜日フォールバックを行う。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、保存）。外部 jquants_client と連携。
    - 検索上限や探索範囲（_MAX_SEARCH_DAYS, _CALENDAR_LOOKAHEAD_DAYS, _BACKFILL_DAYS など）を設定して安全性を確保。

  - ETL パイプライン（pipeline）
    - ETL の結果を表す ETLResult dataclass を実装（取得数・保存数・品質問題・エラー一覧など）。has_errors / has_quality_errors / to_dict を提供。
    - 差分更新、バックフィル、品質チェックを行う設計（jquants_client, quality モジュールと連携する想定）。
    - 内部ユーティリティ（テーブル存在チェック、最大日付取得、カレンダーヘルパー）を実装。

  - ETL 公開インターフェース（etl.py）で ETLResult を再エクスポート。

  - jquants_client など外部クライアントとの連携ポイントを用意（実装は別モジュール／外部）。

- リサーチ（kabusys.research）
  - factor_research: ファクター計算（モメンタム、ボラティリティ、バリュー）
    - calc_momentum: mom_1m/3m/6m、ma200_dev を計算（200 行未満なら None）。
    - calc_volatility: 20 日 ATR、atr_pct、20 日平均売買代金、出来高比などを計算（必要行数未満は None）。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0/欠損なら None）。
    - DuckDB と SQL ウィンドウ関数を組み合わせて効率的に実装。外部 API にはアクセスしない。

  - feature_exploration: 解析ユーティリティ
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。ホライズンバリデーションあり。
    - calc_ic: スピアマンのランク相関（IC）を計算。レコード不足・等分散で計算不能時は None を返す。
    - rank: same-rank を平均ランクで処理する安定したランク化実装（round による丸めで浮動小数境界の扱いを安定化）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。None を除外。

- 共通的な設計方針・堅牢性改善
  - ルックアヘッドバイアス防止のため、全てのスコアリング/判定関数は外部から target_date を受け取り内部で date.today()／datetime.today() を参照しない設計。
  - OpenAI 呼び出しには明示的な API キー解決（引数優先→環境変数）を導入し、未設定時は ValueError を投げて呼び出し側に明示。
  - DB 書き込みは冪等性を重視し、BEGIN/COMMIT/ROLLBACK を適切に使用。ROLLBACK 失敗時は警告ログを出力して上位へ例外を伝播。
  - API レスポンスのパース失敗や想定外の値は例外を投げずフォールバック（警告ログ）して処理を継続するフェイルセーフ設計。
  - DuckDB のバージョン差異（executemany の空リスト扱いなど）に配慮した実装。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- 環境変数読み込み時に OS 環境変数の上書きを保護する仕組みを追加（protected set）。
- OpenAI API キーの取り扱いは引数または環境変数から明示的に解決。未設定時は明示的にエラーとなり、意図しないデフォルト送信を防止。

### Deprecated
- なし

### Removed
- なし

---

注:
- 本 CHANGELOG はコードベースの内容から推測して記載しています。外部の未公開モジュール実装（例: jquants_client の内部、quality モジュールの詳細）は参照できないため、連携点と期待動作を記載しています。
- 今後のリリースでは API 仕様変更、DB スキーマ変更、AI モデル変更（モデル名・JSON Mode の廃止等）などがあれば Breaking Changes として明示していきます。