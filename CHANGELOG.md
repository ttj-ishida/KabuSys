Keep a Changelog
=================

すべての注目すべき変更点を記録します。  
フォーマットは Keep a Changelog に準拠します。  

[0.1.0] - 2026-03-29
-------------------

Added
- 基本パッケージ初期バージョンを追加（kabusys v0.1.0）。
  - パッケージ公開情報:
    - __version__ = "0.1.0"
    - パッケージ公開モジュール: data, research, ai, （将来の）strategy, execution, monitoring を想定した __all__ 定義。
- 環境設定モジュール（kabusys.config）を追加
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - 読み込み優先順位: OS環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - .env ファイルパーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルールに対応。
  - 環境変数必須チェック用 _require と Settings クラスを提供。主な設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID （必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL の検証
    - is_live / is_paper / is_dev のユーティリティプロパティ
- AI 関連モジュール（kabusys.ai）を追加
  - ニュースセンチメント集約・スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとに最大記事数・文字数をトリムして OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチ処理（最大 20 銘柄/チャンク）、JSON Mode を利用して厳密な JSON レスポンスを期待。
    - 再試行戦略: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンス検証: JSON 抽出（余分テキストを剥がす処理含む）、results 配列の検証、未知コード無視、スコアの ±1.0 クリップ。
    - DuckDB 互換性考慮: executemany に空リストを渡さない等の保護。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - テスト容易性: _call_openai_api のパッチ差し替えで外部依存をモック可能。
    - ニュースウィンドウ計算 calc_news_window(target_date)（JST 基準の前日 15:00 ～ 当日 08:30 を UTC naive datetime で返す）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロ記事のフィルタリング（キーワードリスト）、LLM 呼び出し（gpt-4o-mini）で macro_sentiment を取得。失敗時は 0.0 にフォールバック。
    - レジームスコア合成・閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。
    - API 呼び出しのリトライ/エラー分類（RateLimit / 接続 / タイムアウト / APIError の扱い）とログ出力。
- Research（解析）モジュール（kabusys.research）を追加
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials の最新財務データと当日株価から PER・ROE を計算（EPS=0/欠損は None）。
    - すべて DuckDB の prices_daily/raw_financials に依存し、ルックアヘッドを防止する設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 任意ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）計算。有効レコード < 3 の場合は None。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（浮動小数の丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
- Data モジュール（kabusys.data）を追加
  - カレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar がない場合は曜日ベース（平日のみ営業）でフォールバック。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得して market_calendar を冪等的に更新。バックフィル・健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラス（target_date, fetched/saved counts, quality_issues, errors, to_dict 等）。
    - 差分取得用ユーティリティ（テーブル存在チェック、最大日付取得、トレーディング日調整等）。
    - デフォルトの backfill_days、calendar lookahead 等の定数を定義。
    - kabusys.data.etl は pipeline.ETLResult を再エクスポート。

Changed
- （初回リリースのため該当なし）設計上の重要注意点をドキュメントに反映:
  - すべての「日付を扱う処理」は datetime.today()/date.today() への直接依存を避け、外部から target_date を注入する設計（ルックアヘッドバイアス防止）。
  - OpenAI 呼び出しは JSON Mode を利用し、受信レスポンスの堅牢な検証処理を実装。
  - DuckDB のバージョン差異（executemany の空リスト等）への互換性配慮を追加。

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の自動ロード時に、既存の OS 環境変数を保護する仕組み（protected set）を導入。  
  .env.local による上書きは可能だが、起動時の既存 OS 環境変数は上書かれないよう配慮。

Notes / Usage hints
- OpenAI API キー: score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を要求します。未設定時は ValueError を送出します。
- デフォルトの DB パス: DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db
- テスト容易性: news_nlp/regime_detector 内の _call_openai_api および regime_detector の LLM 呼び出しは unittest.mock.patch 等で差し替え可能です。
- DuckDB を利用した SQL 実装は「ルックアヘッド防止」「部分失敗時の既存データ保護（コード絞り込みで DELETE→INSERT）」など、実運用を意識した冪等性・堅牢性を重視しています。

今後
- strategy / execution / monitoring 等の実取引周りのモジュール拡張。
- jquants_client 実装の追加（データ取得ロジック）と ETL のパイプライン統合強化。
- CI テスト・ドキュメント拡充、例外ハンドリングやメトリクス出力の改善。