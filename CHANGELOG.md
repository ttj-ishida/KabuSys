CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" を準拠しています。
このパッケージの初回公開バージョンは 0.1.0 です。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-03
--------------------

追加 (Added)
- パッケージ初期リリース。
- 基本パッケージ情報
  - kabusys パッケージのエントリポイントを追加（__version__ = "0.1.0", __all__ を公開）。
- 環境設定 / ロード (kabusys.config)
  - .env / .env.local ファイルおよび環境変数から設定値を読み込む自動ロード実装。
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - OS 環境変数を保護する protected セットの仕組みを実装。
  - .env のパースは次に対応：
    - 空行・コメント行（先頭#）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの行でのインラインコメント処理（'#' の前が空白/タブの場合のみ）
  - 必須環境変数取得用の _require 実装（未設定時は ValueError を送出）。
  - Settings クラスを提供（settings = Settings()）：
    - J-Quants、kabuステーション、LINE、データベースパスなどの設定プロパティ。
    - デフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）。
    - 監視用設定（PID ファイル、kill flag、CPU/メモリ/ディスク閾値）。
    - 環境値バリデーション（KABUSYS_ENV, LOG_LEVEL の有効値チェック）および helper プロパティ（is_live / is_paper / is_dev）。
- データ層 (kabusys.data)
  - ETL パイプラインインターフェース
    - ETLResult dataclass を公開（kabusys.data.etl から再エクスポート）。
    - ETLResult に処理結果・品質問題・エラー情報の集約、辞書変換メソッドを実装。
  - pipeline モジュール（kabusys.data.pipeline）
    - 差分更新、バックフィル、品質チェックの設計方針とユーティリティを実装。
    - DuckDB 操作のための内部ユーティリティ（テーブル存在確認、最大日付取得など）。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダー管理用ユーティリティを実装。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB 値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック）。
    - 最大探索範囲やバックフィル日数、サニティチェック等の安全措置を導入。
- 研究用モジュール (kabusys.research)
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を SQL / DuckDB で計算。
      - データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR, 相対ATR(atr_pct), 20日平均売買代金, 出来高比率を計算。
      - true_range の NULL 伝播を考慮した実装。
    - calc_value: raw_financials の最新財務データと株価から PER / ROE を算出（EPS=0/欠損は None）。
    - 各関数は date, code をキーとする dict のリストを返却。
  - feature_exploration モジュール
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算を実装。入力検証あり（horizons は 1..252）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。データ不足時は None。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能。
    - 全て DuckDB の prices_daily を主に参照し、外部依存を避けた実装。
- AI / NLP モジュール (kabusys.ai)
  - news_nlp モジュール
    - raw_news / news_symbols を元に、銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へバッチ送信しセンチメント（ai_score）を ai_scores テーブルへ書込む機能を実装。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive で扱う）。
    - バッチ処理、最大チャンクサイズ、記事数／文字数トリム、JSON Mode を用いた堅牢なレスポンス検証を実装。
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）、レスポンス検証（JSON パース、results フォーマット、コードの一致、数値性、クリップ）。
    - API 呼び出しはテスト差し替えしやすいように _call_openai_api を抽象化。
    - score_news(conn, target_date, api_key=None) パブリック API を提供（戻り値: 書き込んだ銘柄数）。
  - regime_detector モジュール
    - ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM センチメントを重み合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む機能を実装。
    - マクロニュース抽出（キーワード群）、LLM 評価（gpt-4o-mini、JSON モード）、スコア合成（MA 重み 0.7 / マクロ 0.3）を実装。
    - API の冗長性対策（リトライ・フェイルセーフとして macro_sentiment=0.0）や、DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - score_regime(conn, target_date, api_key=None) パブリック API を提供。
- DuckDB をデフォルトストレージとして全面採用
  - 各モジュールで DuckDB 接続を受け取り、SQL/ウィンドウ関数を用いた効率的な集計を実装。
- 設計上の注意点（ドキュメント化された設計方針）
  - ルックアヘッドバイアス防止のため各処理で datetime.today()/date.today() を直接参照しない（target_date を明示）。
  - API 失敗時はフェイルセーフ（例: スコア 0.0、スキップ）を基本方針とし、処理継続性を優先。
  - DB 書き込みはできる限り冪等に（DELETE→INSERT、ON CONFLICT 等）して部分失敗で既存データを不必要に消さない。
  - テスト容易性を意識した API 抽象化（_call_openai_api の差し替え等）。
- ロギング
  - 各モジュールで詳細な debug/info/warning ログを追加し、失敗時の挙動が追跡しやすいように実装。

変更 (Changed)
- 初回リリースのため該当なし。

修正 (Fixed)
- 初回リリースのため該当なし。

注記 (Notes)
- OpenAI API を利用する機能（news_nlp, regime_detector）を利用する際は OPENAI_API_KEY を設定してください（関数の api_key 引数でも注入可）。未設定時は ValueError を送出します。
- J-Quants 関連やカレンダー更新は外部クライアント（kabusys.data.jquants_client）への依存があるため、そのクライアント実装に応じた動作となります。
- データベース（DuckDB）・テーブル構成（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）は本リリース時点の仕様に従います。テーブル構成の変更は将来のリリースで互換性に影響する可能性があります。

今後の予定
- モニタリング・実行（execution / monitoring）周りの公開 API と実装強化。
- 追加のファクター / ストラテジー実装とバックテスト機能の拡充。
- テストカバレッジの拡大および CI/CD の整備。