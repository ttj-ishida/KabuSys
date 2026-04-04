# CHANGELOG

すべての重要な変更をここに記載します。フォーマットは「Keep a Changelog」に準拠しています。

最新リリース
============

Unreleased
----------
（現在のブランチに対する未リリースの変更はありません）

リリース履歴
===========

0.1.0 - 2026-04-04
------------------

Added
- 初期リリースとしてパッケージを追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読込する機能を実装。
  - 自動読込は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを正しく扱う実装を搭載。
  - OS 環境変数（既存の os.environ）は保護され、.env.local は override=True で上書きできるが保護されたキーは上書きされない。
  - 必須環境変数取得用の _require と Settings クラスを提供。以下の主要設定にプロパティアクセス可能：
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU/MEMORY/DISK の閾値
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL の検証
    - is_live / is_paper / is_dev の便利プロパティ

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとにニュースを連結し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントをスコアリング。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄/チャンク、1銘柄あたりの最大記事数/文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - リトライとエラーハンドリング: 429/接続断/タイムアウト/5xx は指数バックオフでリトライ。その他のエラーはスキップして継続（フェイルセーフ）。
    - レスポンス検証: JSON 抽出、"results" リスト、各要素の code/score 検査、スコアを ±1.0 にクリップ。
    - 書き込みは idempotent な DELETE（対象コードのみ）→ INSERT をトランザクション内で実行。部分失敗時に既存データを保護。

  - regime_detector.score_regime
    - ETF 1321（Nikkei 225 ETF）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定・保存。
    - マクロ記事抽出は定義済みキーワード群に基づくフィルタリング、最大記事数制限あり。
    - OpenAI 呼び出しは再試行ロジック（RateLimit, Connection, Timeout, 5xx）を実装。API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - 結果は market_regime テーブルに対して冪等的（DELETE/INSERT）に保存。

  - 共通設計方針:
    - datetime.today()/date.today() を直接参照せず、target_date ベースでウィンドウを計算。ルックアヘッドバイアスを防止。
    - OpenAI 呼び出しは JSON mode を利用し、テストのために _call_openai_api をパッチ差替え可能に設計。

- データモジュール（kabusys.data）
  - calendar_management
    - JPX カレンダー管理：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が存在しない場合は曜日（平日）ベースのフォールバックを行う。
    - next/prev/get_trading_days は DB 登録値を優先しつつ未登録日は曜日ベースで補完。一貫性を保つ実装。
    - calendar_update_job: J-Quants クライアントを用いて差分取得し、バックフィル（直近 _BACKFILL_DAYS）と健全性チェックを行った上で保存。API 失敗や異常時は 0 を返す。

  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.ETLResult）。ETL 実行結果の集約、品質問題リスト、エラーリストを保持。辞書化 to_dict を実装。
    - ETL パイプラインの骨子（差分更新、保存、品質チェック）のためのユーティリティを含む。差分のバックフィルやエラー/品質問題の収集方針（Fail-Fast ではない）を明記。

- research モジュール（kabusys.research）
  - ファクター計算（factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（単純平均）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得し PER/ROE を計算（EPS が 0 または欠損だと PER は None）。PBR/配当利回りは未実装。
    - DuckDB を直接用いた SQL 実装で、外部 API 呼び出しは行わない。

  - 特徴量解析（feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証あり。
    - calc_ic: スピアマンのランク相関（IC）を計算。有効レコードが 3 件未満なら None を返す。
    - rank / factor_summary: ランク化（同順位は平均ランク）、基本統計量（count/mean/std/min/max/median）を提供。
    - pandas 等に依存せず、標準ライブラリ + DuckDB ベースで実装。

Changed
- （初期リリースのため過去からの変更というよりは実装の方針・設計点を明記）
  - すべての日時・ウィンドウ計算は target_date ベースで実施し、ルックアヘッドバイアス防止の設計を採用。
  - DuckDB に対する書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT または ROLLBACK）で冪等性・部分失敗時の保護を重視。

Fixed
- N/A（初回リリース）

Security
- OpenAI API キーは引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照。キー未設定時は ValueError を送出して明示的に失敗する設計（誤動作防止）。
- .env 自動読込時、既存 OS 環境変数は保護されるため、システム環境変数の上書きを防止。

Notes / Known limitations
- OpenAI との通信は gpt-4o-mini を前提に実装しているが、将来のモデル変更によりレスポンス形式や例外型が変わる可能性があるため、例外の扱いや status_code の取得は安全に実装している（getattr 等）。
- ai モジュールは API 失敗時にスコアを 0.0（またはその銘柄をスキップ）して継続するフェイルセーフ設計。運用時は外部モニタリングで API 健康を確認することを推奨。
- ETL / calendar の J-Quants クライアント（kabusys.data.jquants_client）への依存があるため、実行環境には該当クライアント実装と認証情報が必要。

導入・実行時チェックリスト（簡易）
- 必須環境変数を設定:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - OPENAI_API_KEY（AI 機能を使う場合）
- 必要に応じて .env / .env.local をプロジェクトルートに配置。自動読込はデフォルトで有効。
- DuckDB ファイルパス等は Settings によりデフォルトで data/ 以下が使われる（必要に応じて DUCKDB_PATH を設定）。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートや運用上の注意事項はプロジェクトの意思決定に基づいて調整してください。