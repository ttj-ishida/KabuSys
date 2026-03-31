# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルはリリース履歴の要約であり、ユーザー向けの主要な機能追加・変更点を示します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システムの基盤ライブラリを提供します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージを導入（__version__="0.1.0"）。主要サブパッケージとして data, research, ai, その他（strategy, execution, monitoring）をエクスポート。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env の柔軟なパーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、コメント解析を考慮）。
  - Settings クラスを提供し、主要設定をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパスの既定値（DUCKDB_PATH, SQLITE_PATH）
    - KABUSYS_ENV の検証（development/paper_trading/live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）および is_live/is_paper/is_dev ヘルパー

- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - ニュース記事を銘柄ごとに集約し（ウィンドウ: 前日15:00 JST〜当日08:30 JST）、OpenAI (gpt-4o-mini) を用いて銘柄別センチメント（-1..1）を計算して ai_scores テーブルへ書き込み。
    - バッチ処理（最大20銘柄/チャンク）、トークン肥大化対策（記事数/文字数制限）、API エラーハンドリング（429, ネットワーク断, タイムアウト, 5xx をリトライ）を実装。
    - レスポンス検証、スコアのクリップ、部分成功時の DB 保護（対象コードのみ DELETE→INSERT）などの堅牢性設計を実装。
    - テスト用に内部の API 呼び出し関数を patch 可能。
  - regime_detector.score_regime:
    - ETF 1321（日経連動ETF）の200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等的に書き込み。
    - MA200 乖離 (重み 70%) と LLM マクロセンチメント (重み 30%) を合成。LLM 呼び出しはリトライ/フォールバック実装（失敗時 macro_sentiment=0.0）。
    - OpenAI クライアント生成／呼び出しの独立実装によりモジュール間結合を避ける。

- 研究・ファクター（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）等を計算。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER, ROE を計算（target_date 以前の最新財務レコードを使用）。
    - DuckDB SQL と Python を組み合わせて効率的に実装。データ不足時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括クエリで取得（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）計算。データ不足時は None を返す。
    - factor_summary: 各ファクター列の基本統計量 (count/mean/std/min/max/median) 計算。
    - rank: 同順位は平均ランクを与えるランク付けユーティリティ。
  - research パッケージは zscore_normalize（kabusys.data.stats から）を再エクスポート。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理ロジック（market_calendar を参照）。is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等のユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（土日を休日扱い）。
    - calendar_update_job により J-Quants からの差分取得と冪等保存（fetch + save）を実装。バックフィル・健全性チェックをサポート。
  - pipeline / etl:
    - ETLResult データクラス（target_date, fetched/saved カウント類, quality_issues, errors）を提供。
    - 差分更新・バックフィル・品質チェックの設計方針に基づく ETL 基盤（jquants_client, quality と連携する想定）。
    - _get_max_date 等のユーティリティを実装。
  - etl モジュールは ETLResult を再エクスポート。

- 共通設計・耐障害性
  - DuckDB を主要なデータソースとして利用（DuckDB 接続を受け取る API）。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() をスコープ外で直接参照しない設計（target_date を明示的に渡す）。
  - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等パターンを採用。例外時は ROLLBACK を試行し、失敗ログを出す。
  - OpenAI API 呼び出しでの再試行（指数バックオフ）、5xx とクライアントエラーの区別、レスポンス検証とフォールバック（0.0 やスキップ）を実装。
  - DuckDB の executemany に関する互換性（空リスト不可）を考慮した実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーはメソッド引数で注入可能。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定の場合は ValueError を発生させることで誤った無認証呼び出しを防止。

---

注記:
- テストしやすさを考慮し、内部の OpenAI 呼び出しは patch 可能な形で実装されています（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- 実際の API クレデンシャルや DB スキーマ（prices_daily, raw_news, ai_scores, market_calendar, raw_financials 等）はドキュメント/スキーマ定義を参照してください。