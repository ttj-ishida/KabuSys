# Changelog

すべての注記は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このファイルはコードベースの内容から推測して作成しています。各項目はソース内の実装・ドキュメント文字列・設計方針等に基づく要約です。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-31

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期リリース。
  - パッケージ公開用の __version__ = "0.1.0"、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定・設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルートの検出ロジック: .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応）。
  - 環境変数を厳密に取得する Settings クラスを追加。
    - 必須キー取得時は未設定で ValueError を送出（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）。
    - duckdb/sqlite 等のデフォルトパス取得、CPU/メモリ/ディスクの閾値、ログレベル・環境（development/paper_trading/live）検証などのプロパティを提供。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI（自然言語処理）機能 (kabusys.ai)
  - ニュースセンチメント解析: score_news を実装（kabusys.ai.news_nlp）。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST、内部は UTC naive datetime を使用）。
    - raw_news と news_symbols を銘柄ごとに集約し、1 銘柄あたりの最大記事数/文字数でトリム。
    - OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信（最大 20 銘柄/チャンク）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ付きリトライ実装。
    - レスポンスバリデーション（JSON 抽出、results 配列、code と score の検証、スコアの有限性チェック、±1 にクリップ）。
    - 書き込みは部分置換（DELETE → INSERT）で冪等性を確保。DuckDB の executemany の制約に注意して実装。
    - API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出。
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）。

  - 市場レジーム判定: score_regime を実装（kabusys.ai.regime_detector）。
    - ETF 1321（日経225 連動）について 200 日移動平均乖離を計算し（_calc_ma200_ratio）、マクロニュースの LLM センチメントと合成して市場レジーム（bull / neutral / bear）を判定。
    - 合成重み: MA200 重み 70%、マクロセンチメント重み 30%（スコアの合成とクリッピング実装）。
    - マクロニュースの抽出（キーワードベース）と LLM 呼び出し、API エラー時は macro_sentiment=0.0 でフォールバック。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とトランザクションのロールバック保護。
    - OpenAI 呼び出しは独立実装でモジュール結合を避ける設計。

- データ基盤ユーティリティ (kabusys.data)
  - カレンダー管理モジュール（kabusys.data.calendar_management）
    - JPX カレンダー管理ロジック（market_calendar テーブル）: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫した判定ロジック。
    - 夜間バッチ job (calendar_update_job) を実装し、J-Quants API から差分取得→保存（バックフィルと健全性チェックを含む）。
    - 最大探索範囲やバックフィル日数などの安全ガードを導入。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（取得・保存件数、品質問題、エラーの集約）。
    - 差分更新、バックフィル、品質チェックを想定した設計方針とユーティリティ関数を実装（テーブル存在チェック、最大日付取得など）。
    - jquants_client（外部クライアント）との連携を想定（fetch/save の呼び出しポイントあり）。
    - エラー時のロギングと例外ハンドリング方針を文書化。

- リサーチ機能 (kabusys.research)
  - ファクター計算群（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時の None 処理。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を参照して PER と ROE を算出（EPS が 0/欠損時は None）。
    - DuckDB のウィンドウ関数・集計を活用し、営業日ベースのウィンドウ設計、ルックアヘッドバイアス回避の設計方針を採用。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンの入力検証あり。
    - calc_ic: スピアマンのランク相関による IC 計算を実装（結合・欠損除外・最小サンプルチェック）。
    - rank: 同順位は平均ランクにするランク変換を実装（丸めで ties の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー関数を実装。
  - research パッケージは主要関数を __all__ で公開（calc_momentum 等）。

### 変更 (Changed)
- なし（初版のため実装・追加が中心）

### 修正 (Fixed)
- なし（初版のため実装・追加が中心）

### 削除 (Removed)
- なし

### 非推奨 (Deprecated)
- なし

### セキュリティ (Security)
- なし

---

注記（実装上の重要な設計判断・利用上の注意）
- OpenAI API を利用する機能（news_nlp / regime_detector）は API キーを引数または環境変数 OPENAI_API_KEY で解決します。キー未設定時は ValueError が発生します。
- ニュース・レジーム処理はルックアヘッドバイアス防止のため内部で date.today() / datetime.today() を直接参照しない設計になっています。処理対象日は明示的に引数で渡してください。
- DuckDB への書き込みは冪等性と部分失敗保護を重視（DELETE→INSERT、トランザクション）しています。DuckDB の executemany に関する注意点に対応済み。
- .env 自動ロードはプロジェクトルート検出に依存します。パッケージ配布後に異なる動作が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- テスト容易性のため、OpenAI 呼び出しポイント（_call_openai_api）を差し替え可能に実装しています。

もし実際の変更履歴（コミットログやリリースノート）が別に存在する場合は、本ファイルをそれらの情報で更新してください。