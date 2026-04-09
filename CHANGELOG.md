CHANGELOG
=========

このプロジェクトは Keep a Changelog の形式に準拠して変更履歴を記載します。  
すべての並びはリリース順（新しいものが上）です。

[Unreleased]
------------

- （現在なし）

[0.1.0] - 2026-04-09
-------------------

初回リリース — KabuSys: 日本株自動売買システムの基盤ライブラリを追加しました。

Added
- パッケージ基礎
  - パッケージメタデータ: src/kabusys/__init__.py に __version__ = "0.1.0"、主要サブパッケージを公開。
  - 公開モジュール: data, strategy, execution, monitoring を export。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーは export KEY=val 形式、クォートとバックスラッシュエスケープ、インラインコメントの処理に対応。
  - 上書き禁止キー（protected）をサポートし OS 環境変数の保護を実現。
  - Settings クラスを提供し、各種設定プロパティを取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等必須キーチェック（未設定時は ValueError）。
    - KABU_API_BASE_URL, LINE API、データベースパス（DuckDB / SQLite）等のデフォルト値。
    - PAPER_FILL_MODE（instant/partial/never/reject）のバリデーション。
    - KABUSYS_ENV（development/paper_trading/live） と LOG_LEVEL（DEBUG/INFO/...） のバリデーション。
    - 監視系設定（pid/kill flag パス、閾値）を環境変数から取得。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - score_news(conn, target_date, api_key=None): raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込み。
  - ニュース時間ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（DB は UTC 前提で比較）。
  - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大 10 記事・3000 文字にトリム。
  - OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を利用し、厳密な JSON を期待。
  - エラーハンドリング: 429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ（最大 _MAX_RETRIES）。その他エラーはスキップしてフェイルセーフに動作。
  - レスポンス検証: results 配列・各要素の code/score チェック、スコアを ±1.0 にクリップ。
  - DuckDB への書き込みは部分失敗に備え、取得済みコードのみを DELETE → INSERT（冪等）で置換。
  - テスト容易性: OpenAI 呼び出しを差し替えるために内部関数 _call_openai_api を patch 可能。

- AI 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を market_regime テーブルへ保存。
  - マクロニュース選定はニュース NLP の時間ウィンドウを利用（calc_news_window を使用）。
  - OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメントの評価（JSON 出力期待）を行い、失敗時は macro_sentiment=0.0 にフォールバック。
  - 冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）、DB 書き込み失敗時は ROLLBACK を試行して例外を再送出。
  - テスト容易性: news_nlp とは別実装の _call_openai_api を提供しモジュール間の結合を低減。

- リサーチ / ファクター（src/kabusys/research/*）
  - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離率を計算（データ不足時は None）。
  - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
  - calc_value(conn, target_date): raw_financials から最新の EPS/ROE を取得し PER/ROE を計算（EPS が 0 または欠損の場合は None）。
  - calc_forward_returns(conn, target_date, horizons=None): 任意ホライズンの将来リターンを一括取得（デフォルト [1,5,21]）。
  - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。十分なサンプルがない場合は None を返す。
  - factor_summary(records, columns) / rank(values) / zscore_normalize の再エクスポートを含むユーティリティ群。
  - 実装設計: DuckDB + 標準ライブラリのみ、ルックアヘッドバイアス回避（date.today() 未使用）。

- データプラットフォーム（src/kabusys/data/*）
  - calendar_management.py:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得の場合は曜日ベース（平日）でフォールバック。
    - calendar_update_job(conn, lookahead_days): J-Quants API（jquants_client）から差分取得して market_calendar を冪等更新。バックフィルと健全性チェックを実装。
  - pipeline.py / etl.py:
    - ETLResult データクラスを追加（取得件数、保存件数、品質問題、エラー等を保持）。
    - ETLResult.to_dict() で品質問題を辞書化して監査ログに利用可能。
    - ETL に関する定数（初期データ開始日、バックフィル日数等）と設計方針を実装。
    - data.etl は ETLResult を再エクスポート。

- モジュール初期化
  - src/kabusys/ai/__init__.py: score_news のエクスポート。
  - src/kabusys/research/__init__.py: 主要関数のエクスポート。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- 新規リリースのため該当なし。

Notes / Implementation details / 設計上の注意
- ルックアヘッドバイアス対策: 多くの関数で date.today() / datetime.today() を参照せず、必ず target_date を呼び出し側が明示的に与える設計。
- OpenAI 関連: gpt-4o-mini を想定した JSON Mode を利用。API エラーは多段的にハンドリングして安全なフォールバックを行う（スコア 0.0 または該当銘柄スキップ）。
- DuckDB 前提: 多くの集計・ウィンドウ関数は DuckDB 接続（DuckDBPyConnection）を受け取る実装。
- テストサポート: OpenAI 呼び出しや時間依存性を差し替えやすくして単体テストが行いやすい設計（内部関数の patch を想定）。
- DB 書き込みは基本的に冪等となるよう DELETE → INSERT または ON CONFLICT を用いる方針（部分失敗時に既存データを破壊しない配慮）。

Breaking Changes
- 新規リリースのため該当なし。

今後の予定（例）
- strategy / execution / monitoring の実装拡張（発注ロジック、broker clients、監視エージェント等）。
- テストカバレッジの強化とサンプルデータを用いた統合テスト。
- パフォーマンス改善（大規模データ処理時のチャンク制御・並列化など）。

もし特定ファイルや変更点について詳細な説明や、別バージョン向けのリリースノート分割（例: Unreleased として差分を管理）を希望される場合は指示してください。