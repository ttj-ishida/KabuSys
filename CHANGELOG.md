CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。
バージョン番号は semver に従います。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-04
-------------------

初回リリース。本リポジトリの主要機能と設計方針を実装したバージョン。

Added
- パッケージ構成の追加
  - kabusys パッケージ（サブパッケージ: data, research, ai, config, monitoring/execution を想定する公開 API）
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local を自動ロードする仕組みを追加（プロジェクトルートを .git または pyproject.toml から検出）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装（export プレフィックス、クォート内エスケープ、行内コメントルール対応）。
  - 上書き制御（override 引数）と OS 環境変数の保護（protected set）に対応。
  - Settings クラスを追加し、以下の設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEMORY/DISK のしきい値
    - KABUSYS_ENV（development / paper_trading / live を検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL を検証）
    - ヘルパー: is_live / is_paper / is_dev

- AI モジュール（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から記事を集約し、OpenAI（gpt-4o-mini）の JSON モードで銘柄ごとのセンチメントを生成。
    - タイムウィンドウ計算（JST ベース）calc_news_window を提供。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、記事数・文字数のトリム制御（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - 再試行戦略: RateLimit/接続断/タイムアウト/5xx を指数バックオフでリトライ。
    - レスポンスの堅牢なバリデーション（JSON の前後ノイズ復元、results リスト・code/score の検査、±1.0 でクリップ）。
    - DuckDB への安全な書き込み（部分失敗時に他銘柄の既存スコアを消さない DELETE→INSERT の一貫操作。DuckDB の executemany 空リスト制約に配慮）。
    - テスト容易性: _call_openai_api をパッチ置換できるフックを用意。

  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースはキーワードフィルタで抽出、LLM により -1.0〜1.0 を返すことを期待（JSON のみ）。
    - API 呼び出しの再試行/バックオフ、API失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 結果は冪等に market_regime テーブルへ書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB エラー時は ROLLBACK を試行して例外伝播。
    - テスト用に _call_openai_api を差し替え可能。

- Research（src/kabusys/research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離を計算（prices_daily を利用、データ不足時は None を返す）。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせ PER（EPS=0/欠損時は None）、ROE を計算。
    - すべて DuckDB 上の SQL＋ウィンドウ関数で実装。外部 API や本番発注コードへのアクセスなし。

  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算。
    - calc_ic: スピアマンランク相関（IC）を実装。有効レコードが 3 未満なら None。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を提供。

  - research パッケージは data.stats の zscore_normalize を再エクスポート。

- Data プラットフォーム（src/kabusys/data）
  - calendar_management モジュール
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダーがないまたは未登録日は曜日（平日）ベースでフォールバック。
    - calendar_update_job: J-Quants API から差分取得して冪等に保存（バックフィル・健全性チェックを実装）。
    - 安全装置: 最大探索日数（_MAX_SEARCH_DAYS）、バックフィル日数、未来日健全性チェックを実装。

  - pipeline / etl モジュール
    - ETLResult データクラスを公開（取得/保存数、品質問題、エラーの集約）。
    - ETL の設計: 差分更新、idempotent 保存（ON CONFLICT）、品質チェック収集（Fail-Fast ではなく全件収集）。
    - デフォルトの backfill、calendar lookahead などの定数を設定。

Changed
- （初回リリースにつき変更履歴はなし）

Fixed
- （初回リリースにつき修正履歴はなし）

Security
- OpenAI API キーは必須（api_key 引数または環境変数 OPENAI_API_KEY）。キー漏洩に注意。
- 環境変数管理において OS 環境変数は自動ロード時に保護される（.env の上書きを防止する仕組みあり）。

Notes / Limitations
- DuckDB 依存: 実行時には DuckDB と OpenAI Python SDK が必要（コードは openai.OpenAI クライアントを利用）。
- 一部実装は DuckDB のバージョンによる挙動（executemany の空リストなど）を考慮しているため、古い/特殊なバージョンでの動作確認が推奨される。
- 日時の取り扱いは「ルックアヘッドバイアス防止」のため datetime.today()/date.today() の直接参照を避ける設計。ただし calendar_update_job は内部で date.today() を使用している（夜間バッチ想定）。
- AI 呼び出しは JSON Mode を想定しているが、LLM の出力ノイズをある程度復元する実装（JSON 前後の余分なテキストの取り除きなど）を含む。
- DB 書き込みは冪等性を意識して設計。部分失敗時に既存データを不必要に消さない方式を採用。

参考: 主な設定名とデフォルト
- KABUSYS_ENV (development|paper_trading|live) — デフォルト development
- LOG_LEVEL — デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化フラグ（値が存在すれば無効化）
- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db
- KABU_API_BASE_URL — http://localhost:18080/kabusapi

今後の予定（例）
- monitoring / execution の公開 API 実装・ドキュメント整備
- 単体テスト・統合テストの追加および CI ワークフロー整備
- OpenAI 呼び出しのロギング/メトリクス集約、コスト制御機能の強化

---- 

（この CHANGELOG は、ソースコードの実装内容・コメント・命名規約・設計ノートから推測して作成しています。実際の変更履歴やバージョン運用方針はリポジトリの運用ルールに従って調整してください。）