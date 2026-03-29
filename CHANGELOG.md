Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-29
-------------------

初回リリース。日本株自動売買/データ基盤の基礎機能を実装しました。主な追加点・実装方針は以下のとおりです。

Added
- パッケージ基本情報
  - kabusys パッケージ初期バージョンを追加（バージョン 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - Settings クラスを追加し、環境変数から設定値を取得するプロパティを提供。
    - J-Quants / kabuステーション / Slack / DB パス / システム設定をサポート。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から自動検出）。
    - 読み込み順: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサを実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
  - 必須環境変数未設定時は _require() が ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の妥当性検証を実装（許容値制限）。
  - duckdb/sqlite パスは Path オブジェクトで取得。

- AI ニュース解析（src/kabusys/ai/news_nlp.py）
  - score_news(conn, target_date, api_key=None) を実装:
    - 前日 15:00 JST ～ 当日 08:30 JST のニュースウィンドウを calc_news_window() で算出（UTC naive）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（記事数・文字数を制限してトリム）。
    - 最大 _BATCH_SIZE（デフォルト 20）銘柄ずつ OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信。
    - リトライ方針: 429 / 接続断 / タイムアウト / 5xx は指数バックオフでリトライ。
    - レスポンスの堅牢なバリデーションと JSON の復元処理（余計なテキストを含む場合の {} 抽出）。
    - スコアは ±1.0 にクリップ、DB 書き込みは部分失敗を想定して対象コードのみ DELETE → INSERT（冪等性・部分保護）。
    - DuckDB の executemany の制約（空リスト不可）に対応。
  - 補助関数:
    - calc_news_window(target_date): ニュース収集ウィンドウ（UTC）を返す。
    - _fetch_articles, _score_chunk, _validate_and_extract などを実装。
  - 設計方針:
    - datetime.today()/date.today() を参照せず、ルックアヘッドバイアスを防止。
    - API 失敗時はスキップして継続（フェイルセーフ）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - score_regime(conn, target_date, api_key=None) を実装:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime に書き込み。
    - マクロニュース抽出（マクロキーワード群）→ OpenAI 呼び出し → 正規化・クリップ → スコア合成。
    - LLM 呼び出しは独自の _call_openai_api を使用（news_nlp と実装分離）。
    - API エラー時は macro_sentiment=0.0 で続行（WARN ログ）。
    - 書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等性を保つ。失敗時に ROLLBACK を試行。

- 研究用ファクター計算（src/kabusys/research/*.py）
  - factor_research.py:
    - calc_momentum(conn, target_date): 1M/3M/6M リターンと 200 日 MA 乖離を計算。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、平均売買代金、出来高比等を計算。
    - calc_value(conn, target_date): raw_financials から EPS/ROE を取得し PER/ROE を計算。
    - SQL を主体に DuckDB 上で高性能に計算する実装。
    - データ不足時に None を返す挙動を明確化。
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons=None): 複数ホライズンの将来リターンを LEAD で一括計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を実装（同順位は平均ランク処理）。
    - rank(values): 同順位は平均ランク、丸めで ties の扱いを安定化。
    - factor_summary(records, columns): count/mean/std/min/max/median の集計を実装。
  - すべて DuckDB と標準ライブラリのみで実装（pandas 等に依存しない）。

- データ基盤 / カレンダー管理（src/kabusys/data/*.py）
  - calendar_management.py:
    - 市場カレンダー管理機能を実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が存在しない場合は曜日（平日）ベースのフォールバックを行い一貫性を保つ設計。
    - calendar_update_job(conn, lookahead_days=90) を実装: J-Quants API から差分取得して market_calendar を冪等保存（バックフィル・健全性チェックあり）。
    - 最大探索日数やバックフィル等の安全策（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）を導入。
  - pipeline.py / etl.py:
    - ETLResult データクラスを追加（ETL 結果・品質問題・エラー情報を保持）。
    - ETL パイプラインのユーティリティ（最終取得日の算出、テーブル存在チェック、差分取得のための補助）を実装。
    - 設計方針として差分更新・バックフィル・品質チェックを採用。品質チェックで重大な問題が検出されても ETL は継続し結果で判断可能。
    - etl モジュールは ETLResult を再エクスポート。

Changed
- （初回リリースのため履歴上の変更はなし）

Fixed
- （初回リリースのため履歴上の修正はなし）

Security
- .env の自動ロードで OS 環境変数を上書きしない保護（protected set）を導入。
- 必須トークン（OpenAI / Slack / Kabu API など）は未設定時に明示的なエラーを発生させることで誤動作を抑止。

Notes / 設計方針（重要な実装判断）
- ルックアヘッドバイアス回避:
  - 各種スコア計算・ETL・AI ルーチンは datetime.today()/date.today() を参照せず、必ず caller が target_date を与える設計。
- OpenAI 呼び出しの堅牢化:
  - JSON Mode を利用しつつ、JSON パース失敗時の復元処理やレスポンスバリデーション、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフを実装。
  - API エラーは安全にフォールバック（ゼロまたはスキップ）し、システム全体が停止しないようにする。
- DuckDB 互換性配慮:
  - executemany に空リストを渡せないバージョンへの対応や日付値の取り扱いユーティリティ（_to_date）などを実装。

今後の予定（参考）
- strategy / execution / monitoring モジュールの実装拡充（現在パッケージ API としては公開済みだが実体は別途実装予定）。
- 追加の品質チェックルール、監視・アラート機能（Slack 統合の活用等）。
- 単体テスト・統合テストの整備（API 呼び出しのモックパターン等）。

ライセンス・貢献
- 本 CHANGELOG はコードベースの現状から推測して作成しています。実際の差分管理はソース管理（Git）と併用してください。