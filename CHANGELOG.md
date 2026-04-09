CHANGELOG
=========

すべての公開リリースは「Keep a Changelog」準拠の形式で記載しています。  
日付は本コードベースのスナップショット日です。

[Unreleased]
------------

- 今後のリリースで追記予定。

[0.1.0] - 2026-04-09
-------------------

Added
- 初回公開リリース。パッケージメタ:
  - パッケージバージョンを src/kabusys/__init__.py に __version__ = "0.1.0" として設定。
  - パッケージトップで data, strategy, execution, monitoring を __all__ で公開。

- 環境設定管理:
  - src/kabusys/config.py
    - .env ファイルまたは OS 環境変数から設定値を自動読込（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサー実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの適切な処理。
    - protected セットを用いた既存 OS 環境変数保護と override 制御。
    - Settings クラスを提供（J-Quants / kabu API / LINE / DB パス / Paper Trading モード / 監視閾値 / ログ・環境判定等）。
    - 値検証を実装（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等で不正値検出時に ValueError を送出）。

- AI（NLP）モジュール:
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成。
    - OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価（JSON Mode）を実装。
    - チャンク処理（最大20銘柄/回）、記事トリム、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）。
    - レスポンス検証ロジック（JSON 抽出、"results" 構造検証、スコアの数値変換、既知コードフィルタリング、±1 でのクリップ）。
    - DB への冪等書き込み（DELETE→INSERT、DuckDB executemany の空リスト回避を考慮）。
    - calc_news_window を提供し JST ベースのニュースウィンドウ（前日15:00～当日08:30）を UTC naive datetime として返す。
    - テスト容易性のため、OpenAI 呼び出し箇所を差し替え可能に設計（内部 _call_openai_api を patch 可能）。

  - src/kabusys/ai/regime_detector.py
    - 日次で市場レジーム（bull/neutral/bear）を判定するスコアリングを実装。
    - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成。
    - Ma 計算、マクロ記事の抽出、OpenAI 呼び出し（リトライ/バックオフ）、フェイルセーフ（API エラー時は macro_sentiment=0.0）。
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK を試行）。
    - 設計上、ルックアヘッドバイアスを防ぐため datetime.today()/date.today() を参照しない実装。

- データ処理（Data Platform）:
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）と営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 優先、未登録日は曜日ベースでフォールバック。探索上限（_MAX_SEARCH_DAYS）や健全性チェックを実装。
    - calendar_update_job により J-Quants から差分取得し冪等保存（バックフィル・健全性チェックあり）。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインの骨格実装。
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラーの収集、has_errors/has_quality_errors/proc to_dict）。
    - 差分更新・バックフィルの方針、品質チェックとの連携設計を反映。
    - etl モジュールで ETLResult を再エクスポート。

- Research（因子研究）:
  - src/kabusys/research/factor_research.py
    - calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials を参照）。
    - 各関数は (date, code) ベースの dict を返す設計。欠損データは None。
    - 移動平均・ATR・売買代金平均などを SQL＋Python で計算。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）で将来リターンを計算。horizons の検証を実施。
    - calc_ic: スピアマンのランク相関（IC）を実装（None/不足レコード時の取り扱い）。
    - rank: 同順位は平均ランクを返す実装（丸めで ties の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。

Changed
- 設計・実装方針の明示:
  - 多くのモジュールで「ルックアヘッドバイアスを避ける」「外部副作用を抑える」「DB 操作は冪等に」「テスト容易性を考慮（内部呼び出しの差し替え可能化）」といった設計方針を採用。

Fixed
- 安定性向上のため複数箇所でフォールバック/フェイルセーフを追加:
  - OpenAI API 呼び出しでの回復処理（リトライ・ログ出力・ゼロフォールバック）。
  - DuckDB executemany の空リストに対する回避処理。
  - calendar_update_job の健全性チェック（過剰に未来日がある場合のスキップ）。
  - .env 読み込み時の I/O エラーを warnings で扱いプロセス停止を防止。

Security
- 環境変数取り扱いの注意:
  - .env 読み込みで既存の OS 環境変数を保護するロジック（protected set）を導入。
  - OpenAI API キーは引数で注入可能／環境変数から取得するが、未設定時は ValueError を発生させ明示的に要求。

Notes / 致命的な変更
- 本リリースは初回実装であり、将来的に API の仕様変更（OpenAI SDK、DuckDB の振る舞い等）により修正が必要となる可能性があります。
- OpenAI との通信部分は外部 SDK 間の差異に備えて status_code の存在チェック等を行っていますが、SDK のマイナーバージョン差異に注意してください。

参考
- コード内ドキュメントに各処理フロー・設計方針を詳述しています。テスト時は各モジュールの内部 _call_openai_api などを patch して API 呼び出しを差し替えることを想定しています。