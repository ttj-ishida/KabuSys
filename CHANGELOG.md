CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の慣例に従っています。
語彙: Added = 新機能, Changed = 変更, Fixed = 修正, Removed = 削除, Security = セキュリティ関連

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - 基本パッケージ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加し、公開モジュールを定義。

- 環境設定/ロード機能 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出は .git または pyproject.toml を使用）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ実装: export 形式、クォート内のエスケープ、インラインコメント処理に対応。
  - Settings クラスを提供し、必須環境変数取得（_require）と以下プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス (duckdb/sqlite) のデフォルト
    - KABUSYS_ENV と LOG_LEVEL の検証（有効値を限定）
    - is_live / is_paper / is_dev ヘルパー

- ニュースNLP（AI） (src/kabusys/ai/news_nlp.py, src/kabusys/ai/__init__.py)
  - raw_news と news_symbols から銘柄別にニュースを集約し、OpenAI (gpt-4o-mini, JSON Mode) によるセンチメント評価を行い ai_scores テーブルへ書き込み。
  - タイムウィンドウ計算（JST 基準）と calc_news_window を提供。
  - バッチ処理、トークン肥大化対策（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）、_BATCH_SIZE による分割。
  - API レート制限・ネットワーク障害・5xx サーバーエラー等に対する指数的バックオフとリトライ実装。
  - 応答のバリデーション（JSON の復元、results 構造、スコアの数値判定、既知コードフィルタリング）と ±1.0 でのクリップ。
  - テスト容易性のため _call_openai_api を patch 可能に実装。
  - 処理はフェイルセーフ設計（API 失敗時はスキップして継続し、例外を投げない方針）。

- 市場レジーム判定（AI + 指標合成） (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離とマクロニュース LLM センチメントを合成して日次市場レジーム（bull/neutral/bear）を判定。
  - マクロキーワードによるニュース抽出、OpenAI (gpt-4o-mini) によるマクロセンチメント評価、重み合成（MA 70% / マクロ 30%）を実装。
  - API リトライ、5xx 判定、JSON パース失敗時のフォールバック（macro_sentiment = 0.0）を確保。
  - 結果は market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で書き込み。
  - ルックアヘッドバイアス対策: 内部で date.today() を参照しない、DB クエリに date < target_date 等の排他条件を使用。

- 研究（Research）モジュール (src/kabusys/research/*)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。データ不足時は None。
    - calc_value: raw_financials から最新財務を取得し PER/ROE を計算。
    - 設計として DuckDB 上の SQL と Python を組み合わせ、外部 API を呼ばない実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン (デフォルト [1,5,21]) を計算。horizons の検証を実施。
    - calc_ic: スピアマンランク相関（IC）を計算（ties 平均ランク処理）。
    - rank: 同順位は平均ランクで扱う安定的なランク関数を実装（丸めで誤差対策）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - research パッケージ __all__ に主要関数を再エクスポート。

- データ管理（Data）モジュール (src/kabusys/data/*)
  - calendar_management:
    - JPX カレンダー取得・保存の夜間バッチ calendar_update_job を実装（J-Quants API 経由）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。market_calendar がない場合は曜日ベースでフォールバック。
    - 最大探索日数やバックフィル、健全性チェックを実装して誤動作を防止。
  - pipeline / etl:
    - ETLResult データクラスを実装して ETL の集計結果（取得数、保存数、品質問題、エラー）を返却可能に。
    - ETL パイプライン用ユーティリティ（最終取得日の検出、テーブル存在チェック、差分取得・バックフィル方針）を実装。
    - jquants_client と quality モジュールを使った idempotent 保存と品質チェックの設計を反映。
  - etl を外部公開するための簡易インターフェース（src/kabusys/data/etl.py で ETLResult を再エクスポート）。

- DuckDB/SQL 周りの互換性と安全対策
  - DuckDB の executemany に空リストを渡さないチェックや、list 型バインドの回避（個別 DELETE 実行）など互換性考慮。
  - トランザクション中の例外発生時に ROLLBACK を試行し、ROLLBACK 自体の失敗を警告ログで記録する実装。

Changed
- （新規リリースのため該当なし）

Fixed
- （新規リリースのため該当なし）

Security
- （本リリースで特別なセキュリティ修正は含まれていませんが、API キーは明示的に引数経由または環境変数 OPENAI_API_KEY を参照する実装で、未設定時は ValueError を発生させることで誤配置を防止しています）

Notes / 実装上の重要な仕様
- ルックアヘッドバイアス対策として、主要なスコア計算関数は内部で現在時刻を参照せず、呼び出し元が target_date を明示的に渡す方式を採用。
- OpenAI 呼び出しは JSON Mode を利用し、厳密な JSON 応答を期待する設計。応答パース失敗時はフォールバックして処理を継続する。
- 自動 .env ロードはプロジェクトルート判定に __file__ を起点とした探索を用いるため、パッケージ配布後も CWD に依存しない動作を目指しています。
- 各種定数（バッチサイズ、リトライ回数、ウィンドウ時間など）はモジュールトップに定義され、容易に調整可能です。

ライセンスや既知の制限、今後の予定についてはリポジトリの README / docs を参照してください。