CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-27
--------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージのバージョンは src/kabusys/__init__.py にて定義（__version__ = "0.1.0"）。
- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装。優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して判定（CWD 非依存）。
  - .env パーサを実装し、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 環境変数上書き時の protected セット（OS 環境変数保護）機能を導入。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（主にテスト用途）。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / システム設定（env, log_level, is_live 等）を環境変数から取得・バリデーション。
- AI 関連機能（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄別に記事をまとめて OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - バッチサイズ、最大記事数・文字数トリム、JSON Mode を用いたレスポンス検証、結果の ±1.0 クリップなどのロジックを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。API 失敗時は対象銘柄をスキップして処理継続（フェイルセーフ）。
    - DuckDB への書き込みは部分的失敗に備え、取得済みコードのみ DELETE → INSERT で置換（冪等保存・既存スコア保護）。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
    - 公開 API: score_news(conn, target_date, api_key=None)：書き込み銘柄数を返す。
    - 時刻ウィンドウ計算ユーティリティ calc_news_window(target_date) を提供（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news からデータを取得し、OpenAI 呼び出しで macro_sentiment を得る。API 失敗時は macro_sentiment = 0.0 として継続（警告ログ）。
    - LLM 呼び出しは独立した内部実装でモジュール結合を抑制。レスポンスの JSON パースやエラー時のリトライを堅牢に実装。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None)：成功時に 1 を返す。
  - ai パッケージ公開インターフェースに score_news を追加（src/kabusys/ai/__init__.py）。
- Research（因子計算・特徴量探索）（src/kabusys/research）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER / ROE）を DuckDB 上の prices_daily / raw_financials から計算する関数を実装。
    - 各関数は（date, code）をキーとした辞書リストを返す。データ不足は None を返す設計。
    - 公開関数: calc_momentum, calc_volatility, calc_value。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）。
    - IC（Spearman の rank correlation）計算 calc_ic(...)、ランク変換 rank(...)、ファクター統計サマリー factor_summary(...) を実装。
    - pandas 等に依存せず、標準ライブラリのみで実装。
  - パッケージ公開インターフェースに主要関数をエクスポート（src/kabusys/research/__init__.py）。
- Data（データ処理／ETL／カレンダー管理）（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を利用した営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未取得時の曜日ベースフォールバック、最大探索日数制限、バックフィル・健全性チェック等を実装。
    - nightly job calendar_update_job(conn, lookahead_days=...) を実装し、J-Quants API との差分取得 → 保存（jq.fetch_market_calendar / jq.save_market_calendar）をサポート。
  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを実装し、ETL 実行の取得数・保存数・品質問題・エラーを集約して返せるようにした。
    - 差分取得、バックフィル、品質チェック（quality モジュールとの連携）等の設計方針を明文化。
    - etl モジュールは pipeline.ETLResult を再エクスポート。
  - DuckDB 互換性と安全性への配慮（ex. executemany に空リストを渡さない guards）。
- utilities / 設計方針の明記
  - ルックアヘッドバイアス回避のため各モジュールで datetime.today() / date.today() を直接参照しない設計が徹底されている（target_date 引数を使用）。
  - OpenAI API 呼び出しロジックはリトライ・フェイルセーフ・レスポンス検証を行い、システム全体が単一の API 障害で停止しないよう工夫。

Changed
- （本リリースは初版のため該当なし）

Fixed
- （本リリースは初版のため該当なし）

Security
- 環境変数の扱いに注意:
  - .env 読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - Settings._require により必須環境変数未設定時は明示的に例外を発生させ、起動時の不整合を早期に検出。

Deprecated
- （本リリースは初版のため該当なし）

Removed
- （本リリースは初版のため該当なし）

Notes / 実装上の重要な注意点
- OpenAI 呼び出し部分はテストの容易さを考慮して内部関数を patch できるようにしている（unittest.mock.patch を想定）。テスト時はネットワーク / API 呼び出しを差し替えて使用してください。
- DuckDB のバージョン差異（executemany の空リスト扱い等）に配慮した実装になっています。実運用環境では使用している DuckDB バージョンの挙動を確認してください。
- news_nlp / regime_detector の LLM ベース処理は外部 API に依存するため、API キーの管理・利用制限・コストに注意してください。

今後の予定（参考）
- さらなる指標（PBR、配当利回り等）の追加
- モデル / ストラテジー層との接続部分（execution, monitoring）の実装強化
- テストカバレッジ拡充と CI ワークフロー整備

---