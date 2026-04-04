# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

## [Unreleased]

## [0.1.0] - 2026-04-04

### Added
- パッケージ初回リリース: kabusys 0.1.0
  - パッケージ宣言と公開 API を追加（kabusys.__init__）。
- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルート探索は __file__ を基点に .git / pyproject.toml を探索（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - OS側の既存環境変数は protected として上書きを防止。
  - .env パーサー
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理をサポート。
  - 設定クラス Settings を提供
    - 各種必須環境変数取得メソッド（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH（data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）等。
    - 監視系ファイルパス（PID ファイル, kill flag）・閾値（CPU/MEMORY/DISK）を設定可能。
    - KABUSYS_ENV と LOG_LEVEL の値検証（有効値チェック）。
    - is_live / is_paper / is_dev のショートハンドを提供。
- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news + news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）でセンチメント評価。
    - ニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 換算）を calc_news_window で実装。
    - バッチ送信（最大 20 銘柄 / バッチ）、1 銘柄につき最大 10 記事・3000 文字でトリム。
    - レスポンスは JSON Mode（厳密な JSON）を期待しつつ、前後余分テキストを補正してパースする耐性を実装。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
    - レスポンスの検証: results 配列、code/score の存在・型、未知コードの無視、スコアの ±1.0 クリップ。
    - DuckDB 互換性考慮: executemany に空リストを渡さないようガード。
    - テスト容易性: OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - MA 計算では target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロ記事がない場合、または API 失敗時は macro_sentiment = 0.0（フェイルセーフ）。
    - OpenAI は gpt-4o-mini を使用。リトライ・5xx ハンドリングを実装。
    - レジーム結果は市場テーブルへ冪等的に書き込み（BEGIN → DELETE → INSERT → COMMIT。失敗時は ROLLBACK）。
    - テスト差し替えのため OpenAI 呼び出しは独立実装。
- Research（kabusys.research）
  - ファクター算出（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。データ不足時は None。
    - Volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - Value: PER（EPS が無効な場合は None）、ROE（raw_financials から取得）。
    - DuckDB を用いた SQL / ウィンドウ関数中心の実装で、外部 API や実際の発注ロジックとは無関係。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）の fwd_xd を提供。ホライズン検証あり（1〜252）。
    - IC（Information Coefficient）計算（calc_ic）：Spearman（ランク相関）を実装。3 件未満で None を返す。
    - ランク変換ユーティリティ（rank）：同順位は平均ランク。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を算出。
- Data（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を基に営業日判定・次/前営業日取得・期間内営業日取得・SQ 判定を提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB に値がない場合は曜日ベースのフォールバック（土日は非営業日）。
    - 最大探索範囲の上限（_MAX_SEARCH_DAYS = 60）を設けて無限ループを防止。
    - 夜間バッチ calendar_update_job を実装（J-Quants API 経由で差分取得、バックフィル _BACKFILL_DAYS = 7、先読み _CALENDAR_LOOKAHEAD_DAYS = 90、健全性チェック）。
    - jquants_client 経由の fetch / save を利用（外部クライアントを想定）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（ETL の各種取得数・保存数・品質問題・エラーを格納）。
    - 差分取得、バックフィル戦略、品質チェック（quality モジュール）に基づく ETL の基本設計方針を実装想定。
    - エラーと品質問題は詳細を収集して呼び出し元で判断する方針（Fail-Fast ではない）。
    - DuckDB テーブルの存在確認・最大日付取得ユーティリティを提供。
- 互換性・実装上の注意
  - ルックアヘッドバイアス対策: 主要なスコア・ファクター計算は datetime.today()/date.today() を参照せず、target_date に基づいて動作。
  - DuckDB 互換性を考慮した実装（executemany の空リスト回避等）。
  - 外部ライブラリ依存を最小化（Research モジュールは pandas などに依存しない純標準ライブラリ実装）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーは引数 injection か環境変数 OPENAI_API_KEY のいずれかで解決。未設定時は ValueError を発生させ明示的に失敗するように設計。
- .env パーサーのエスケープ処理を適切に扱い、誤解釈を減らす実装を追加。

### Notes / Migration
- settings を利用するコードは Settings に依存するため、環境変数名（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY, KABUSYS_ENV, LOG_LEVEL 等）を正しく設定してください。
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB を使用するため、DuckDB 接続オブジェクトを各関数に渡す必要があります（関数内で接続を開く実装は含まれません）。
- OpenAI 呼び出し箇所はテストのために差し替え可能なポイントを用意しています（unittest.mock.patch 等で _call_openai_api をモック可能）。

---

（注）本 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして公開する際は、リリース時の差分や追加ドキュメントに応じて更新してください。