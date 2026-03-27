# CHANGELOG

すべての重要な変更をここに記録します。  
このファイルは "Keep a Changelog" の書式に準拠します。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な内容は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - パッケージ名: kabusys、バージョン v0.1.0 を設定（src/kabusys/__init__.py）。
  - 公開サブパッケージ予定値として __all__ に data, strategy, execution, monitoring を定義。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env のパース機能を独自実装（コメント処理、export プレフィックス、シングル/ダブルクォート対応、エスケープ対応など）。
  - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - 必須環境変数取得用の _require ヘルパーと、Slack / J-Quants / kabu API / DB パス等のプロパティを提供。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を実装。
  - デフォルトの DB パス (DUCKDB_PATH / SQLITE_PATH) の既定値を設定。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP（score_news）を実装（src/kabusys/ai/news_nlp.py）。
    - raw_news / news_symbols テーブルから銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）にバッチで投げてセンチメントを取得。
    - JSON mode を利用した厳密な出力バリデーションを実装。
    - バッチサイズ、記事数上限、文字数上限を設定してトークン肥大化を防止。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ処理を実装。
    - スコアを ±1.0 にクリップ。部分失敗時にも既存スコアを保護するためにコード単位で DELETE → INSERT の冪等更新を行う。
    - テスト用に内部の _call_openai_api を patch で差し替え可能に設計。
    - calc_news_window ヘルパーで JST の時間ウィンドウ（前日 15:00 ～ 当日 08:30）を UTC に変換して扱う。

  - レジーム検出（score_regime）を実装（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を算出・保存。
    - マクロキーワードによる raw_news フィルタリング、最大記事数制限を実装。
    - OpenAI 呼び出しのリトライ/フォールバック（API失敗時は macro_sentiment=0.0）を実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - datetime.today() 等を参照せず、外部から与えられる target_date に依存する設計でルックアヘッドバイアスを回避。

- リサーチモジュール (src/kabusys/research)
  - factor_research モジュールを実装（calc_momentum / calc_value / calc_volatility）。
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離の計算。
    - Volatility: 20日 ATR、相対ATR、平均売買代金、出来高比率の計算。
    - Value: raw_financials から最新の EPS / ROE を取得して PER / ROE を算出。
    - DuckDB のウィンドウ関数と集計で効率的に計算。
  - feature_exploration モジュールを実装（calc_forward_returns / calc_ic / factor_summary / rank）。
    - 将来リターンの計算（任意ホライズン、horizons の検証）。
    - スピアマンランク相関（IC）計算（重複ランクは平均ランクで処理）。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
    - 小さなユーティリティ（rank）を含む。
  - re-export: zscore_normalize を kabusys.data.stats から再エクスポート。

- データプラットフォーム (src/kabusys/data)
  - market_calendar 管理モジュールを実装（calendar_management.py）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 登録値優先、未登録日の曜日ベースフォールバック、最大探索日数制限による安全性。
    - calendar_update_job を実装（J-Quants API からの差分取得、バックフィル、健全性チェック、保存処理呼び出し）。
  - ETL パイプライン用のインターフェースと ETLResult データクラスを実装（pipeline.py / etl.py）。
    - ETLResult により取得件数・保存件数・品質問題・エラーの集約を提供。
    - _get_max_date 等のヘルパーを実装。差分取得・バックフィル・品質チェックの設計を反映。
    - jquants_client（外部クライアント）との連携レイヤを想定。

### 変更 (Changed)
- なし（初回リリースのため「追加」が中心）。

### 修正 (Fixed)
- なし（初回リリース）。

### セキュリティ (Security)
- 環境変数管理:
  - 自動 .env ロード時に既存 OS 環境変数を保護する仕組み（protected set）を導入。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。

### 設計上の注意 / 既知の制約 (Notes / Known limitations)
- OpenAI への依存:
  - news_nlp/regime_detector は OpenAI API（gpt-4o-mini）を利用するため、API キー（OPENAI_API_KEY）の提供が必須。関数は api_key を引数で注入可能。
  - API 呼び出しは冪等性を保証しないため、部分失敗対策として DB 書き込みはコード単位で削除→挿入を行う実装とした。
- DuckDB の互換性:
  - DuckDB 0.10 の executemany の空リスト制約を考慮した実装上の配慮がある（空 params の場合は実行しない）。
- 時刻/タイムゾーン:
  - すべての内部処理は明示的に日付（date）や UTC-naive datetime を扱うようにし、ローカル日時参照（date.today() の直接使用）は避け、ルックアヘッドバイアスを防止している。
- テスト容易性:
  - OpenAI 呼び出し部分は内部関数（_kall_openai_api 等）を patch して置き換え可能にしており、ユニットテストがしやすい設計。

---

もし特定の変更点（例: より詳細なログ出力、関数のシグネチャ変更、追加した環境変数の一覧等）を CHANGELOG に含めたい場合は、該当箇所を指定してください。必要に応じてリリースノートを追記・整形します。