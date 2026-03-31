CHANGELOG
=========

このドキュメントは Keep a Changelog の形式に準拠しています。
語句は日本語で記載しています。

フォーマット:
- Unreleased: 今後の変更用（現時点では空）
- 各リリースには Added / Changed / Fixed / Deprecated / Removed / Security のカテゴリを使用

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージルート: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
  - 公開サブパッケージ候補: data, strategy, execution, monitoring を __all__ に定義（各サブパッケージは段階的実装想定）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび OS 環境変数から設定を自動読み込み。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを特定（CWD 非依存）。
  - .env パーサの強化:
    - export KEY=val 形式への対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - コメント扱いルール（クォート外かつ直前が空白/タブ）。
    - 無効行は無視。
  - _load_env_file により既存 OS 環境変数を保護する protected 機能を実装（override=True/False に対応）。
  - Settings クラスにてアプリ設定をプロパティで提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須（未設定時は ValueError）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等にデフォルトを用意。
    - CPU/MEM/DISK の閾値、LOG_LEVEL、KABUSYS_ENV (development/paper_trading/live) 検証ロジック。
    - is_live / is_paper / is_dev の簡易判定プロパティ。

- AI 関連モジュール (src/kabusys/ai/)
  - news_nlp (ニュースセンチメント)
    - raw_news と news_symbols を集約して銘柄ごとのセンチメントを算出し ai_scores テーブルへ書き込み。
    - OpenAI (gpt-4o-mini) の JSON mode を利用し、出力を厳密な JSON として扱う設計。
    - チャンク処理（1 API 呼び出しで最大 20 銘柄）とトークン肥大化対策（記事数上限、文字数上限）。
    - リトライ戦略: レート制限(429)、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ。
    - レスポンス検証: 結果の構造（results リスト、code/score）と型検査、未知コードの無視、スコアを ±1.0 にクリップ。
    - フェイルセーフ: API 失敗時は該当チャンクをスキップして処理を継続。スコア未取得時は DB 書き込みを行わない。
    - 時間ウィンドウ: JST ベースで前日 15:00 ～ 当日 08:30（UTC に変換して DB と比較）を対象。datetime.today()/date.today() に依存しない。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。

  - regime_detector (市場レジーム判定)
    - ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロニュース LLM センチメント (重み 30%) を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュースの抽出に使うキーワード群を内包（日本・米国系キーワード）。
    - OpenAI 呼び出しは独立した内部実装（news_nlp と共有しない）でモジュール結合を低減。
    - API エラー時は macro_sentiment=0.0 にフォールバックして処理継続（フェイルセーフ）。
    - リトライ・バックオフ・500 系とそれ以外の扱いの分離、JSON パース例外時のフォールバックを実装。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- データ処理関連 (src/kabusys/data/)
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB への依存度: market_calendar が存在する場合は DB 値優先、未登録日は曜日ベースでフォールバック。
    - next/prev は _MAX_SEARCH_DAYS の範囲で探索し、無限ループを防止。
    - calendar_update_job にて J-Quants からの差分取得 → 保存（バックフィル・健全性チェックあり）。
  - pipeline / ETL
    - ETLResult dataclass を公開（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py で再エクスポート）。
    - ETL の設計方針をコードドキュメント化: 差分更新、バックフィル、品質チェックの集約、エラー／品質問題の集計。
    - 内部ユーティリティ: テーブル存在検査、最大日付取得（途中まで実装ファイルあり）。
  - jquants_client と quality モジュールを介した API 取得・保存の想定（実装は別ファイル／外部モジュール）。

- リサーチ / ファクター (src/kabusys/research/)
  - factor_research
    - Momentum, Value, Volatility, Liquidity 等の定量ファクターを DuckDB クエリで計算する関数を実装:
      - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m/ma200_dev を計算。データが不足する場合は None を返す。
      - calc_volatility(conn, target_date): atr_20 / atr_pct / avg_turnover / volume_ratio を計算。窓不足で None を返す挙動。
      - calc_value(conn, target_date): per / roe を raw_financials と prices_daily から計算。
    - 設計方針: DuckDB の SQL ウィンドウ関数を活用し外部 API にはアクセスしない。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（LEAD を利用）を一度に取得する実装。horizons のバリデーションあり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク）相関（IC）を計算。データ不足時は None。
    - rank(values): 同順位に平均ランクを割り当てる実装（浮動小数丸めで ties 検出の安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリ関数。
  - research パッケージの __init__.py にて主要関数を再エクスポート（zscore_normalize は data.stats から取得）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- OpenAI / J-Quants 等の API キーは Settings により環境変数で管理する想定。コード内に機密情報は含めない設計方針。

注意事項 / 使用上のポイント
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID またはそれらに相当する設定が必要な箇所あり（Settings の各プロパティを参照）。
  - OpenAI API を利用する機能 (score_news / score_regime) は api_key 引数または環境変数 OPENAI_API_KEY を必須で参照（未設定時は ValueError）。
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視用): data/monitoring.db
- 自動 .env 読み込みはデフォルトで有効。テストや CI で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- AI 呼び出しは gpt-4o-mini の JSON mode を前提とした実装（レスポンスの厳密な JSON 出力を期待）。
- ルックアヘッドバイアス排除: 主要な関数は date.today() 等の現在時刻参照を行わず、必ず target_date を外部から与える設計。

今後の予定（想定）
- strategy / execution / monitoring サブパッケージの具現化（実取引・バックテスト・監視周りの実装）。
- jquants_client や quality モジュールの実装・強化、ETL の完全実装とスケジューリング対応。
- テストカバレッジと CI ワークフローの整備。

貢献・報告
- バグ報告・機能提案は Issue を通じて行ってください。README / CONTRIBUTING の整備を順次追加予定です。