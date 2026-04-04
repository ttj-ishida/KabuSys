# CHANGELOG

すべての注目すべき変更はここに記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
- なし

## [0.1.0] - 2026-04-04
初回リリース。

### 追加 (Added)
- パッケージの基盤
  - kabusys パッケージ初版を追加（__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring をエクスポート。

- 環境設定 / 設定管理
  - 環境変数読み込みユーティリティを追加（kabusys.config）。
    - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索（CWD 非依存）。
    - .env / .env.local 自動読込（優先順位: OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - 自動読み込み時は OS 環境変数を保護（既存キーは上書きしない）。.env.local は override=True。
  - Settings クラスを提供（settings インスタンス）。
    - 各種設定プロパティ（J-Quants、kabu API、LINE、データベースパス、監視用ファイルパス、閾値、環境種別・ログレベル判定等）。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）。
    - 必須環境変数未設定時は ValueError を送出する _require ヘルパ。

  - 主要環境変数（代表）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - OPENAI_API_KEY（AI モジュールで使用）
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - KABUSYS_ENV（development / paper_trading / live）, LOG_LEVEL

- AI（自然言語処理）モジュール
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を読み、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でバッチ評価し ai_scores に書き込む機能を提供。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）: calc_news_window。
    - バッチ処理: 最大 20 銘柄/コール、記事数と文字数（1銘柄あたり最大記事数・最大文字数）でトリム。
    - OpenAI 呼び出しは JSON Mode（厳密 JSON 出力想定）を利用。レスポンスの検証・復元ロジックを実装。
    - 再試行ポリシー: レート制限・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
    - フェイルセーフ: API 失敗時は対象チャンクをスキップし処理継続。部分失敗時に既存スコアが不要に削除されないよう、削除→挿入は対象コードに限定。
    - スコアは ±1.0 にクリップ。テスト容易性のため _call_openai_api をパッチ可能に実装。
    - 公開 API: score_news(conn, target_date, api_key=None)

  - レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書込む機能を提供。
    - MA 算出は過去データ（target_date 未満のみ）で行い、データ不足時は中立（1.0）を採用。
    - マクロニュース: raw_news からマクロキーワードでタイトルを抽出（最大 20 件）、OpenAI へ投げて -1.0〜1.0 のスコアを取得。
    - OpenAI 呼び出し: 同様にリトライとバックオフ、サーバーエラーは再試行、最終的に失敗した場合 macro_sentiment=0.0 にフォールバック。
    - スコア合成は clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1) の方針。
    - DB 書き込みは冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）で実装。
    - 公開 API: score_regime(conn, target_date, api_key=None)

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを基に営業日判定・前後営業日の取得・期間内営業日リスト取得・SQ日判定などを提供。
    - DB にデータがある場合は DB 値を優先、未登録日は曜日ベース（土日除外）でフォールバック。
    - next_trading_day / prev_trading_day は最大探索日数（_MAX_SEARCH_DAYS）を設定して無限ループを防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィルと健全性チェックを実装。
    - 日付の扱いはすべて date オブジェクト（timezone 混入を避ける設計）。

  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETL 実行結果を表す ETLResult データクラスを提供（取得数・保存数・品質問題・エラー一覧等を含む）。
    - 差分更新のためのユーティリティ、バックフィル日数、品質チェック（kabusys.data.quality 統合ポイント）を想定したインターフェースと設計方針。
    - jquants_client 経由での保存は idempotent（ON CONFLICT / DO UPDATE 想定）。

- リサーチ（kabusys.research）
  - factor_research モジュールを追加
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（ma200_dev）を計算。データ不足は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）, 相対 ATR（atr_pct）, 20日平均売買代金, 出来高比率等を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS=0/欠損時は None）。
    - 全関数は DuckDB の prices_daily / raw_financials のみ参照し、外部 API にアクセスしない設計。
  - feature_exploration モジュールを追加
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンは 1〜252 営業日でバリデーション。
    - calc_ic: スピアマンランク相関（IC）を計算。有効レコードが 3 件未満なら None を返す。
    - rank: 同順位は平均ランクにするランク関数（丸め処理で ties 判定漏れを防止）。
    - factor_summary: count/mean/std/min/max/median の基本統計量を計算。
    - data 処理は標準ライブラリと DuckDB の SQL のみに依存（pandas 等に依存しない実装）。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- OpenAI 等外部 API キーの取り扱い
  - AI モジュール（news_nlp, regime_detector）は OPENAI_API_KEY が未設定の場合、呼び出し側に ValueError を送出して安全に失敗させる（キー不足で誤動作しないよう明示）。
  - .env の自動ロードでは OS 環境変数を上書きしない設計。秘密情報保護の観点から .env の読み込みは明示的に無効化可能。

### 注意事項 / 実装上の設計判断
- ルックアヘッドバイアス回避:
  - AI スコアリング・レジーム判定・ファクター計算など、すべてのバッチ関数は内部で datetime.today()/date.today() を参照せず、必ず target_date 引数を受け取りその日付より前のデータのみを参照する設計になっています。
- テスト容易性:
  - OpenAI 呼び出し部分はモジュール内の _call_openai_api をパッチ/モックできるよう実装しており、ユニットテストで安定した動作確認が可能です。
- DB 書き込みの冪等性:
  - market_regime / ai_scores 等への書き込みは、既存行の削除→挿入や executemany を用いることで部分失敗時のデータ保護と互換性を考慮して実装しています（DuckDB のバインド制約を考慮）。

もし特定ファイル・機能についての詳細な説明（使用例・引数のより詳しい挙動・API 使用方法等）が必要であれば教えてください。必要に応じてリリースノートの表現を調整します。