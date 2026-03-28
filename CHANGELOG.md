# Changelog

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
バージョニングは Semantic Versioning に従います。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システム "KabuSys" の基礎機能を実装しました。以下はコードベースから推測してまとめた主な追加・設計方針・注意点です。

### Added
- パッケージ化
  - パッケージ名: kabusys
  - __version__ を 0.1.0 に設定。
  - 公開モジュール: data, strategy, execution, monitoring をトップレベルで公開。

- 設定管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパースはシェル形式（export プレフィックス、クォート、インラインコメント等）に対応。
  - Settings クラスを提供し、アプリで必要な環境変数をプロパティ経由で取得:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時に ValueError を送出）
    - 任意・デフォルトあり: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV (development/paper_trading/live の検証), LOG_LEVEL（DEBUG/INFO/... の検証）
  - 環境変数の保護（OS 環境変数は .env で上書きされない）を考慮した実装。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントスコアを生成して ai_scores テーブルへ書き込み。
    - タイムウィンドウ: JST 前日 15:00 〜 当日 08:30（内部は UTC naive datetime に変換して扱う）。
    - バッチ処理: 最大 20 銘柄/チャンク、記事数上限・文字数上限（10 件、3000 文字）でプロンプト肥大化を抑制。
    - 再試行/バックオフ: 429/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ（最大試行回数制御）。
    - レスポンス検証: JSON パース、"results" 構造、コードの照合、数値検証を実施。無効レスポンスはスキップ（例外を上げず継続）。
    - スコアは ±1.0 にクリップ。部分成功時は取得できたコードのみ DELETE → INSERT により置換（冪等性・既存保護）。
    - テスト容易性のため OpenAI 呼び出し箇所にパッチ可能な _call_openai_api を用意。

  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と news_nlp のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio は prices_daily（date < target_date）から算出し、データ不足時は中立（1.0）にフォールバックして WARNING を出力。
    - マクロニュース抽出はマクロキーワード一覧でフィルタ（最大 20 記事）。
    - OpenAI 呼び出しは独立した内部実装（news_nlp とプライベート関数を共有しない設計）。
    - API エラー時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - 判定結果は market_regime テーブルへトランザクションで冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。失敗時は ROLLBACK。

- データ基盤 (kabusys.data)
  - calendar_management
    - JPX カレンダー管理と営業日判定ヘルパーを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar が存在しない/未登録日の場合は曜日ベース（土日を非営業日）でフォールバック。
    - next/prev/get の探索は一貫したフォールバックロジックを採用。探索上限 (_MAX_SEARCH_DAYS) を設け無限ループを回避。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル日数・健全性チェックを実装。

  - ETL / pipeline
    - ETLResult データクラスを導入（ETL 実行結果の収集と to_dict によるサマリ出力）。
    - 差分取得／backfill／保存（jquants_client の save_* を利用）／品質チェックを行う設計方針を実装（pipeline モジュールの基盤）。
    - 内部ユーティリティ (_table_exists, _get_max_date, _adjust_to_trading_day 等) を提供。

  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。データ不足は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。欠損処理あり。
    - calc_value: raw_financials から最新の財務データを取得し PER、ROE を計算（EPS=0 / 欠損時は None）。
    - 実装は DuckDB の SQL ウィンドウ関数を多用して効率的に計算。

  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons の検証あり。
    - calc_ic: ファクターと将来リターンのスピアマン（ランク相関）を計算。十分なサンプルがない場合は None。
    - rank: 同順位は平均ランク、浮動小数点丸めで ties の扱いを安定化。
    - factor_summary: count/mean/std/min/max/median を計算（None 値は除外）。

- テスト補助
  - OpenAI 呼び出し箇所に対して unittest.mock.patch による差し替えを想定した設計（_call_openai_api を外部からパッチ可能）。

- ロギング / 耐障害性
  - 各所で詳細なログ（info/debug/warning/exception）を出力。
  - 外部 API エラー時のフォールバック（中立スコアやスキップ）により、ETL/スコア生成が単一障害で停止しない設計。
  - DB 書き込みはトランザクションで行い、失敗時は適切な ROLLBACK 処理とログを行う。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security / Environment notes
- 必須環境変数が未設定の場合、Settings のプロパティが ValueError を投げます。CI/本番環境では必ず設定してください:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- OpenAI 利用に必要な OPENAI_API_KEY は score_news / score_regime の引数で注入可能。引数未指定時は環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError を投げます。
- .env 自動ロードはデフォルトで有効。テストや特殊環境で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

### Migration notes / Usage highlights
- DuckDB 接続オブジェクトを各関数に直接渡す設計です（関数内でグローバル DB を開かない）。呼び出し側で接続管理を行ってください。
- news_nlp や regime_detector は外部の OpenAI API に依存します。テスト時は _call_openai_api をモックしてレスポンスを制御してください。
- ai_scores / market_regime / calendar 更新はいずれも冪等性を考慮しており、部分失敗時に既存データを不必要に消さない実装になっています。

---

今後の予定（想定）
- strategy / execution / monitoring の実装拡充（現状はパッケージ公開のみ）。
- 追加の品質チェック（quality モジュールの実装拡張）やエンドツーエンドの CI テスト。
- ドキュメント整備（API リファレンス、運用手順、環境構築手順）。

--- 

作成にあたり、コード中の docstring と実装から機能・設計方針を推測してまとめました。必要であればリリースノートの文言をより簡潔/詳細に調整します。