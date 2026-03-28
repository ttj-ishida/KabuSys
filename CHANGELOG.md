Keep a Changelog
=================

すべての重要な変更点を記載します。  
フォーマットは Keep a Changelog に準拠します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-28
--------------------

Added
- 初回リリース。パッケージ名: kabusys（__version__ = 0.1.0）。
- パッケージ公開 API の整備:
  - top-level export: data, strategy, execution, monitoring（__all__）。
- 環境設定管理 (kabusys.config):
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動ロード機能: プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動読み込み。
  - 読み込み制御: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサ実装: コメント行、export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - .env 読み込み時の上書きルール: OS 環境変数は protected として上書き禁止、.env.local は .env を上書き可能。
  - 必須環境変数取得ヘルパー _require と各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など）。
  - 環境値検証: KABUSYS_ENV と LOG_LEVEL の許容値チェック、および is_live/is_paper/is_dev のユーティリティ。

- AI モジュール (kabusys.ai):
  - news_nlp.score_news:
    - raw_news / news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ送信（最大 20 銘柄 / リクエスト）、1 銘柄あたりの記事数・文字数上限（トリム）を導入してトークン肥大化に対応。
    - JSON Mode のレスポンスパースに対する堅牢性（前後余計テキストの復元ロジック含む）。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。非リトライ対象エラーはスキップして継続。
    - スコア検証・クリップ（±1.0）、部分成功時の DB 書き込みは対象コードのみ置換（DELETE → INSERT）して既存スコアを保護。
    - テスト容易性: _call_openai_api を patch 可能に設計。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日 SMA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出（マクロキーワード群）→ OpenAI（gpt-4o-mini）で評価 → スコア合成（クリップ）→ market_regime へ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出しは再試行・フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - テスト容易性: _call_openai_api の差し替え可能性を確保。
    - 設計方針として datetime.today()/date.today() を直接参照せず、ルックアヘッドバイアスを回避する実装。

- Data モジュール (kabusys.data):
  - calendar_management:
    - market_calendar テーブルを用いた営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - 最大探索範囲の制限や健全性チェックを導入（_MAX_SEARCH_DAYS 等）。
    - JPX カレンダーを J-Quants から差分取得して更新する calendar_update_job（バックフィル・健全性チェック・J-Quants クライアント呼び出し／保存のラッピング）。
  - pipeline / etl:
    - ETLResult データクラスを追加（ETL の実行結果、品質問題、エラーの収集と to_dict）。
    - ETL 基本ユーティリティ（テーブル存在チェック、最大日付取得等）を実装し、差分取得／バックフィル／品質チェック方針に則った設計。
  - etl の公開インターフェースとして ETLResult を再エクスポート。

- Research モジュール (kabusys.research):
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER・ROE を計算（EPS が 0/NULL の場合は None）。
    - 全関数は DuckDB 接続を受け取り、prices_daily / raw_financials のみ参照する安全な実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算するユーティリティ（欠損・同値処理あり、3 件未満は None）。
    - rank: 同順位は平均ランクとするランク化関数（丸め処理を行い ties を防止）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を返す集計関数。
  - 研究ユーティリティの再エクスポート（zscore_normalize は kabusys.data.stats から）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 実装上の重要ポイント
- ルックアヘッドバイアス対策:
  - AI モジュール・リサーチ・ETL の各処理は datetime.today()/date.today() を直接参照せず、明示的な target_date を受け取る設計。
  - DB クエリにおける date の範囲指定は target_date 未満（排他）などルックアヘッドを防ぐ工夫あり。
- フェイルセーフ設計:
  - OpenAI API の失敗やレスポンスパースエラーは基本的に例外で全体を止めず、フォールバック（例: macro_sentiment=0.0）または該当チャンクのスキップで継続する方針。
- テストのしやすさ:
  - OpenAI 呼び出し部分（_call_openai_api）や sleep の注入、api_key の引数注入など、ユニットテストで差し替えやすい設計を意図。
- トランザクション安全:
  - market_regime や ai_scores への書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等化パターンを採用し、失敗時は ROLLBACK を試みる。ROLLBACK に失敗した場合は警告ログを出力して上位へ例外を伝播。
- 依存および設定:
  - DuckDB を主要なデータ格納およびクエリ処理に使用。
  - OpenAI API（gpt-4o-mini）を利用するための OPENAI_API_KEY が必要（関数呼び出し時に引数で注入可能）。
  - 環境変数の既定値: DUCKDB_PATH= data/kabusys.duckdb, SQLITE_PATH= data/monitoring.db など。

Breaking Changes
- なし（初回リリース）

Security
- なし（初回リリース）

Acknowledgements
- 設計方針に関する注記（データプラットフォーム設計・StrategyModel・Research・DataPlatform の各ドキュメントに準拠した実装方針を採用）。

---- 

必要であれば、リリースノートを英語版や機能ごとの使用例（コードスニペット）で追記します。どの形式がよいか指示ください。