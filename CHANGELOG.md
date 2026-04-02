CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。
このプロジェクトはセマンティックバージョニングを採用しています。

v0.1.0 - 2026-04-02
-------------------

Added
- パッケージ初期リリース。
  - src/kabusys/__init__.py
    - パッケージのバージョンを "0.1.0" として定義。公開モジュールを __all__ で指定。

- 環境設定と自動 .env ロード機能（kabusys.config）
  - .env/.env.local ファイルおよび既存 OS 環境変数から設定を読み込む自動ロード実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - .env パーサ実装（export 形式、シングル/ダブルクォート、エスケープ、行内コメント処理に対応）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - 必須環境変数チェック関数 `_require` と Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等のプロパティを公開。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）や監視設定（PID_FILE_PATH、閾値）をプロパティ化。
    - KABUSYS_ENV 値検証（development, paper_trading, live）や LOG_LEVEL 検証を実装。
  - OS 側の既存環境変数を保護する上書きロジック（protected set）。

- AI モジュール（kabusys.ai）
  - news_nlp（ニュースの NLP スコアリング）
    - raw_news / news_symbols を集約して銘柄ごとに記事テキストを結合。
    - OpenAI (gpt-4o-mini) の JSON Mode を使ったバッチスコアリング（最大バッチサイズ 20）。
    - タイムウィンドウ計算（JST の前日 15:00 ～ 当日 08:30 を UTC に変換して比較）。
    - API 呼び出しのリトライ（429、ネットワーク断、タイムアウト、5xx を対象）と指数バックオフ。
    - レスポンスの堅牢なバリデーションとスコアクリッピング（±1.0）。
    - DuckDB の executemany 空リスト制約を考慮した安全な DELETE/INSERT 処理。
    - API キー解決は引数優先、未指定時は OPENAI_API_KEY 環境変数を参照。未設定時は ValueError。
    - 公開関数: score_news(conn, target_date, api_key=None)
    - calc_news_window(target_date) ユーティリティを提供。

  - regime_detector（市場レジーム判定）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と
      マクロニュースの LLM センチメント（重み 30%）を合成して 'bull'/'neutral'/'bear' を判定。
    - ma200_ratio 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュース抽出はキーワードベースで raw_news からタイトルを取得。
    - OpenAI 呼び出しの独立実装、JSON パース、リトライ、フェイルセーフ（API 失敗時 macro_sentiment=0.0）。
    - idempotent な market_regime テーブル書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開関数: score_regime(conn, target_date, api_key=None)

  - 共通設計上の注意点
    - OpenAI 呼び出し部分はテスト時に差し替え可能な設計（モジュール内プライベート関数で分離）。
    - レスポンスパース失敗や API エラー時のフォールバック（例外を上げずに継続）に重点。

- データプラットフォームモジュール（kabusys.data）
  - calendar_management（マーケットカレンダー管理）
    - market_calendar を用いた営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先、未登録日は曜日ベースのフォールバック（週末判定）。
    - next/prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）を設けて無限ループを防止。
    - 夜間バッチ job: calendar_update_job(conn, lookahead_days=90) により J-Quants から差分取得して保存。バックフィルと健全性チェックを実装。
    - DuckDB からの date 型変換ユーティリティを提供。

  - pipeline / ETL（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（target_date, フェッチ／保存件数、品質問題、エラー一覧など）。
    - 差分更新・バックフィル・品質チェックを想定した設計方針（実装の骨子を提供）。
    - jquants_client と quality モジュールを用いる想定のインターフェース（実装依存）。

  - jquants_client 再利用を想定した設計（fetch/save の呼び出し箇所を用意）。

- 研究（research）モジュール（kabusys.research）
  - factor_research
    - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を計算する calc_momentum(conn, target_date)。
    - Volatility/Liquidity: atr_20, atr_pct, avg_turnover, volume_ratio を計算する calc_volatility(conn, target_date)。
    - Value: per（株価/EPS）、roe を raw_financials と prices_daily を組み合わせて計算する calc_value(conn, target_date)。
    - SQL を主体にして DuckDB 上で完結する実装。データ不足時の None 戻しを明確化。
  - feature_exploration
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons=[1,5,21])（LEAD を使用した一括取得）。
    - IC 計算 calc_ic(...)（スピアマンランク相関を自前実装。十分な有効レコード数がない場合は None）。
    - ランキング関数 rank(values)（同順位は平均ランク、丸め処理あり）。
    - 統計サマリー factor_summary(records, columns)（count, mean, std, min, max, median を算出）。
  - research パッケージの __init__ で主要関数を再エクスポート。

Misc / Implementation details
- DuckDB 互換性を考慮した実装（executemany の空引数回避、date 型処理）。
- ルックアヘッドバイアス防止：datetime.today()/date.today() に依存しない API（target_date を明示的に受け取る）。
- OpenAI モデルは gpt-4o-mini を想定、JSON mode で厳密な JSON 出力を要求するプロンプトを採用。
- ロギングを各モジュールに導入し、警告・情報ログで問題を可視化する設計。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Notes / Known limitations
- OpenAI API キーは環境変数 OPENAI_API_KEY か関数引数で提供する必要がある（未設定時は ValueError を送出）。
- news_nlp と regime_detector は OpenAI 呼び出しに依存するため、API コストやレート制限に注意。
- DuckDB スキーマ（prices_daily, raw_news, ai_scores, market_calendar, raw_financials 等）が事前に整備されていることを前提としている。

Contributors
- コードベースの説明に基づく初期作成。