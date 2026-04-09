Keep a Changelog
================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

[0.1.0] - 2026-04-09
-------------------

Added
- 初回公開リリース。パッケージ名: `kabusys` (バージョン 0.1.0)。
- コア初期構成
  - src/kabusys/__init__.py
    - パッケージのエクスポート定義とバージョン情報 (`__version__ = "0.1.0"`) を追加。
- 設定・環境変数管理
  - src/kabusys/config.py
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みする仕組みを実装。
    - .env のパースはコメント行、`export KEY=val` 形式、クォート文字列とバックスラッシュエスケープ、インラインコメントなどに対応。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - OS 環境変数を保護するため、.env ロード時に既存の環境変数を上書きしない/保護するロジックを実装。
    - `Settings` クラスを提供し、J-Quants / kabu API / LINE / DB パス /監視閾値 / 環境種別 等のプロパティを型付きで取得可能に。
    - 以下の入力検証を実装:
      - PAPER_FILL_MODE（instant|partial|never|reject）
      - KABUSYS_ENV（development|paper_trading|live）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - デフォルトパス: DuckDB `data/kabusys.duckdb`、監視用 SQLite `data/monitoring.db`、paper trading SQLite `data/paper_trading.db` など。
    - PID/kill フラグ関連設定と振る舞い（`KILL_FLAG_CLEAR_ON_START` 等）。

- AI: ニュースNLP / 市場レジーム判定
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI (gpt-4o-mini, JSON mode) によるセンチメントスコアを銘柄単位で取得。
    - 時間ウィンドウ（前日15:00 JST ～ 当日08:30 JST）の算出ユーティリティ `calc_news_window` を提供。
    - バッチ処理（最大 20 銘柄/回）、1銘柄当たりの最大記事数・文字数制限（トークン肥大化対策）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライを実装。
    - レスポンス検証ロジック（JSON パース、"results" 形式、コード照合、スコア数値性、±1.0 クリップ）を実装。
    - DuckDB への冪等書き込み（DELETE → INSERT）を行い、部分失敗時に他銘柄データを保持する設計。
    - OpenAI API キー未指定時は ValueError を送出。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュースはキーワードベースで抽出し、OpenAI による JSON スコア取得を行う（失敗時は macro_sentiment=0.0 のフォールバック）。
    - レジームスコアの合成・閾値判定と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 呼び出しはリトライ・バックオフ処理を持ち、テスト用に _call_openai_api をモック可能。
    - OpenAI API キー未指定時は ValueError を送出。

- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - Momentum, Volatility, Value, Liquidity 系のファクター計算を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
      - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率（データ不足時は None）。
      - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS 0/欠損時は None）。
    - DuckDB 上で SQL とウィンドウ関数を使って効率的に計算。外部 API にアクセスしない設計。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）の将来リターンを一括取得する SQL 実装。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足（<3）で None を返す。
    - rank: 同順位は平均ランクとするランク付け。浮動小数の丸め対策あり。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出。
    - いずれも datetime.today()/date.today() を直接参照しない（ルックアヘッド回避）。

- Data platform（カレンダー管理・ETL）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダーを扱う市場カレンダー管理:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の判定ユーティリティを実装。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバックする一貫した挙動。
    - next/prev_trading_day は最大探索日数制限を設け無限ループを防止。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得し、バックフィルと健全性チェック（最大未来日数）を行い、冪等保存を試行。API 失敗時は 0 を返す。
  - src/kabusys/data/pipeline.py
    - ETL の設計に基づくユーティリティ集（差分更新、保存、品質チェックの連携想定）。
    - ETLResult データクラスを実装:
      - ETL 実行結果（取得数・保存数・品質問題・エラー一覧）を保持。
      - has_errors / has_quality_errors / to_dict を提供。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。

- パッケージ公開インターフェース
  - src/kabusys/ai/__init__.py, src/kabusys/research/__init__.py を通じて主要関数を公開。

Notable design decisions / behaviors
- ルックアヘッドバイアス対策:
  - AI・リサーチ系の処理は target_date 未満 / 指定ウィンドウのみを参照し、datetime.today() を直接参照しない。
- フェイルセーフ:
  - OpenAI API や外部 API の失敗は基本的に例外で全停止させず、ログ出力のうえフォールバック（0.0）やスキップで継続する設計。
- DuckDB 互換性:
  - 一部処理（DELETE → INSERT の executemany）で DuckDB のバージョン差を考慮した実装。
- テストしやすさ:
  - OpenAI 呼び出しや内部 sleep/リトライのエントリポイントは差し替え（モック）可能に設計。
- 環境変数の安全性:
  - .env 自動ロード時に OS 環境変数を保護する仕組みを導入。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能（テスト用途含む）。

Compatibility / Requirements
- DuckDB を用いる前提の SQL 実装。
- OpenAI Python SDK を利用（gpt-4o-mini を想定、JSON mode を使用）。
- J-Quants 関連のクライアント (`kabusys.data.jquants_client`) を想定した呼び出しが含まれる（クライアント実装は別途）。
- OpenAI API キー未設定時は該当関数が ValueError を投げるため、実運用では環境変数 `OPENAI_API_KEY` の設定が必要。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- .env 自動読み込みはデフォルトで有効。OS 環境を保護する実装あり。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- API キーやパスワード等は Settings を通じて環境変数から取得。運用時のキー管理に注意してください（本パッケージ側で暗号化等は行いません）。

Acknowledgements / Notes
- 実装コメントや docstring に設計方針・注意点（例: ルックアヘッド回避、DuckDB の挙動互換、部分失敗時の保護など）を多く記載しています。内部ロジックの変更・拡張はこれら方針を尊重して行ってください。