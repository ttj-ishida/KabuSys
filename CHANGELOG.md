# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

※本ファイルはコードベースから推測して作成しています。実装の詳細や運用手順はソースコードやドキュメントを併せて確認してください。

## [Unreleased]

## [0.1.0] - 2026-03-29

### Added
- 初回リリース。パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0", エクスポート: data, strategy, execution, monitoring）。
- 環境設定モジュール（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装（読み込み優先順位: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。
  - .env パーサの実装: export 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ処理、インラインコメント処理。
  - OS 環境変数を保護するための protected 上書き制御。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DBパス / システム設定（env, log_level）等のプロパティを公開。入力値検証（有効な env / log_level のチェック）を実装。
  - 必須変数未設定時には ValueError を送出するヘルパー関数 _require を提供。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチで投げて銘柄単位のセンチメント（ai_score）を計算する score_news を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当）を calc_news_window で提供。
    - API 呼び出しは JSON Mode を利用し、429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。失敗時はフォールバック（スキップ）し処理継続するフェイルセーフ設計。
    - レスポンスの堅牢なバリデーションを実装（JSON パースの復元処理、results フィールドの検証、未知コード無視、数値検査、スコアの ±1.0 クリップ）。
    - 戻り値を ai_scores テーブルへ冪等に書き込む（DELETE → INSERT、DuckDB executemany の互換性考慮で空リストチェック）。
    - 単体テスト容易化のため _call_openai_api の差し替えポイントを用意。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - calc_news_window に基づくニュースウィンドウ取得、マクロキーワードフィルタ、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を算出。
    - API 呼び出しはリトライ/バックオフを行い、失敗時は macro_sentiment=0.0 とするフェイルセーフ動作。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

- データモジュール（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理と夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得 → 保存）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。market_calendar が存在しない場合は曜日ベース（土日除外）でのフォールバックを行う設計。
    - 更新時のバックフィル、健全性チェック（将来日付の異常検出）、最大探索日数制限を実装して無限ループや誤操作を防止。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを実装し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を集約。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）、冪等保存を行う設計方針を反映したユーティリティ関数群を提供。
    - _get_max_date 等の内部ユーティリティを実装。
  - etl モジュール（src/kabusys/data/etl.py）
    - pipeline.ETLResult を上位モジュールへ再エクスポート。

- Research モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算。
    - calc_volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、volume_ratio を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（財務データは target_date 以前の最新を使用）。
    - DuckDB SQL とウィンドウ関数を中心に実装し、外部 API には依存しない。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 与えられた複数ホライズンの将来リターンを一括で取得（LEAD を利用、horizons のバリデーションあり）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。データ不足時は None を返す。
    - rank: 同順位の平均ランク付け（丸めで ties の検出強化）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
  - zscore_normalize を data.stats から再エクスポート（src/kabusys/research/__init__.py）。

- 共通実装 / 設計上の配慮
  - DuckDB を主要なローカル分析 DB として使用。クエリは DuckDB の互換性やバージョン差分（例: executemany の空リスト制約）を考慮して実装。
  - すべての「日付基準」処理で datetime.today() / date.today() を直接参照しない方針を採用（ルックアヘッドバイアス防止）。target_date を明示的に受け取る API を提供。
  - OpenAI や外部 API 呼び出しはリトライ / バックオフ / フォールバック（安全なデフォルトスコア）を採用し、外部障害で処理全体が失敗しない設計。
  - API 呼び出し部分は単体テスト容易性を考慮して差し替え可能（例: モジュール内の _call_openai_api を patch）。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。ROLLBACK の失敗は警告ログ出力で捕捉。
  - 各モジュールに詳細なログ出力（info/warning/exception）を追加し、運用時の可観測性を確保。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数読み込みの保護機構を導入（OS 環境変数を protected として .env による上書きを防止）。
- 一部機能は API キー（OPENAI_API_KEY 等）を必須とし、未設定時は明示的に ValueError を送出して安全性を高める。

---

備考:
- 実運用では .env.example に従い必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）を設定してください。
- OpenAI 呼び出しで使用するモデルはコード上で gpt-4o-mini が指定されています。運用時のモデル変更やコスト管理は別途検討してください。