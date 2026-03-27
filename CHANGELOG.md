# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しています。主な追加点・設計方針は以下の通りです。

### Added
- パッケージの基本設定
  - kabusys パッケージ初期化 (src/kabusys/__init__.py)。
  - バージョン: 0.1.0。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数からの設定読み込みを自動で行う仕組みを追加。
  - プロジェクトルート探索は __file__ を基点に .git または pyproject.toml を探索（CWD 非依存）。
  - .env の自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしでのインラインコメント扱い（直前が空白・タブの場合）
  - _load_env_file にて既存 OS 環境変数を保護する protected 引数を採用（上書き防止）。
  - Settings クラスを提供し、必須環境変数取得時に未設定で ValueError を送出:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等
  - 設定の検証:
    - KABUSYS_ENV は {development, paper_trading, live} のみ許容
    - LOG_LEVEL は標準ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL) のみ許容
  - データベースパスのデフォルト（DuckDB / SQLite）を提供

- AI（NLP）モジュール (src/kabusys/ai)
  - ニュースセンチメント解析 (src/kabusys/ai/news_nlp.py)
    - 指定タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）に基づく記事集約機能 calc_news_window, _fetch_articles。
    - 銘柄ごとに記事を結合し、トークン肥大化防止のため記事数／文字数でトリム。
    - OpenAI（gpt-4o-mini）へのバッチ送信（最大 20 銘柄 / チャンク）を実装。
    - レスポンスは JSON Mode を想定し厳密なバリデーションを行う (_validate_and_extract)。
    - リトライ戦略（429, ネットワーク断, タイムアウト, 5xx）を実装（指数バックオフ）。
    - スコアは ±1.0 にクリップし、結果を ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT）。
    - テスト用に _call_openai_api を patch 可能（unittest.mock.patch で差し替え推奨）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - MA200 計算（target_date 未満のみ使用）とマクロ記事の抽出ロジックを実装。
    - OpenAI 呼び出しは独立実装で、API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出しでの再試行ロジック（RateLimit/Connection/Timeout/5xx で再試行）を実装。
    - テスト用に _call_openai_api を patch 可能。

- リサーチ（ファクター計算・特徴量探索） (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算する calc_momentum。
    - Volatility / Liquidity: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算する calc_volatility。
    - Value: EPS/ROE から PER/ROE を算出する calc_value（raw_financials + prices_daily を利用）。
    - DuckDB を用いたウィンドウ関数・移動窓計算による実装で、データ不足時は None を返す設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（任意ホライズン、SQL LEAD を使用）。
    - IC（Information Coefficient）計算 calc_ic（スピアマン系のランク相関、必要データ不足時は None）。
    - ランク変換ユーティリティ rank（同順位を平均ランクで処理）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。

- データプラットフォーム（Data） (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティ。
    - market_calendar が未取得時は曜日ベースのフォールバック（週末を非営業日扱い）。
    - calendar_update_job により J-Quants API から差分取得し market_calendar を冪等更新。
    - バックフィル、健全性チェック、探索上限（日数）を実装して異常値に対処。
    - jquants_client インタフェースへの依存性（fetch_market_calendar / save_market_calendar）を想定。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（target_date, fetched/saved counts, quality_issues, errors 等）。
    - 差分取得・保存・品質チェックの方針をコード中に反映（_get_max_date 等のユーティリティを実装）。
    - DuckDB 互換性を考慮した実装（executemany の空リストチェック等）。

- 内部設計/運用面の追加
  - 多くのモジュールで「datetime.today()/date.today() を参照しない」方針を採用（ルックアヘッドバイアス防止）。
  - OpenAI 呼び出しや外部 API 失敗時のフォールバック（0.0スコアやスキップ）によりフェイルセーフを重視。
  - ログ出力（logging）を各処理に導入し、失敗時は警告/例外ログを残す。
  - DuckDB（ローカル分析 DB）前提の SQL 実装と互換性処理（型変換・日付処理）を整備。
  - テスト容易性の配慮: 外部呼び出しを差し替え可能にしてユニットテスト作成を容易化。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数必須項目に未設定時 ValueError を発生させることで、機密設定の見落としを防止。

### Notes / Known limitations
- jquants_client（J-Quants API 用クライアント）や一部外部依存の実装は別モジュール想定（コード内で参照あり）が、今回差分提供コード中に含まれていないため、実運用には該当クライアント実装が必要。
- 実際の発注API（kabuステーション等）への接続部分はこの差分に含まれていない（__all__ に execution/strategy/monitoring を公開しているが、該当実装は別途）。
- OpenAI の SDK バージョン差異に備え、APIError から status_code を安全に取得する処理を実装しているものの、将来の SDK 変更に応じた追加対応が必要になる可能性あり。
- DuckDB のバージョン互換性（executemany の空リスト扱い等）を考慮した実装が入っているが、実行環境の DuckDB バージョンでの動作確認が必要。

---

今後の予定（例）
- execution / strategy / monitoring 等の取引実行パス実装と統合テスト
- jquants_client の実装および ETL の本番運用化
- モニタリング・アラート（Slack 連携）の実装拡充

（以上）