CHANGELOG
=========

すべての注目すべき変更を記載します。フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

（現在なし）

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
  - サブパッケージ公開: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定/設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを追加。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行い、配布後の動作を考慮して CWD に依存しない実装。
    - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサを実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等に対応。
    - 無効行や不正フォーマットの行はスキップ。
  - Settings クラスを提供（settings オブジェクトをデフォルトで公開）:
    - J-Quants / kabuステーション / Slack / DB パス / 実行環境 /ログレベルなどのプロパティ。
    - 必須環境変数未設定時に明示的なエラーを投げる（_require）。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション、および is_live / is_paper / is_dev の判定ユーティリティ。

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントスコアを生成。
    - チャンク処理（最大 20 銘柄/コール）、1 銘柄あたり記事数・文字数上限、JSON レスポンスの厳密バリデーションを実装。
    - リトライ／指数バックオフ（429 / ネットワーク / タイムアウト / 5xx）を実装。非リトライ例外はスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みは冪等（DELETE → INSERT）で、部分失敗でも他銘柄の既存スコアを保護する実装。
    - calc_news_window による JST ベースの収集ウィンドウ計算（ルックアヘッド防止のため UTC naive datetime を返す）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を読み、OpenAI を呼び出して macro_sentiment を算出（記事が無い場合は LLM 呼び出しをスキップ）。
    - OpenAI 呼び出しのリトライ、JSON パース失敗時は macro_sentiment=0.0 にフォールバック。
    - 結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書込失敗時は ROLLBACK を試行して例外を伝播。
  - 共通設計:
    - OpenAI 呼び出しは各モジュールで独立実装（モジュール結合を避ける）。
    - テスト時に差し替え可能なフック（関数名を patch する想定）あり。

- データプラットフォーム / ETL / カレンダー (src/kabusys/data/)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダー（market_calendar）を扱うユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫した判定ロジック。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
    - 最大探索日数の上限を設け無限ループを防止。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を定義（取得数・保存数・品質問題・エラーの収集など）。
    - 差分取得、保存（jquants_client 経由で冪等保存）、品質チェック（quality モジュール）を想定した設計。
    - _get_max_date 等のユーティリティでテーブルの最大日付取得等を提供。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）を計算する関数を実装。
    - DuckDB に対する SQL ベースの実装で、prices_daily / raw_financials のみを参照。結果は (date, code) ベースの辞書リストを返す。
    - データ不足時の扱い（必要行数未満なら None を返す）やログ出力あり。
  - feature_exploration.py:
    - 将来リターン計算 (calc_forward_returns)：複数ホライズンに対応、入力検証、一度のクエリで複数ホライズンを取得する実装。
    - IC（calc_ic）: Spearman（ランク相関）によるファクター有効性評価を実装（ties の平均ランク対応）。
    - ランク変換ユーティリティ rank、統計サマリー factor_summary（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- 共通実装上の注意点 / 設計決定
  - ルックアヘッドバイアス防止: 日付計算で datetime.today()/date.today() を直接参照しない（関数引数で target_date を受ける）。
  - DuckDB をデータストアに利用。SQL と Python を組み合わせて計算／集計を実装。
  - DB 書き込みは冪等性を意識（DELETE → INSERT など）し、部分失敗で既存データを不必要に消さない設計。
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンスの厳密なバリデーション実装。API エラーは基本フェイルセーフ（スコア 0 やスキップ）で継続。
  - テスト容易性のため、API 呼び出しや遅延関数（time.sleep など）を差し替え可能に実装。
  - 外部依存を極力減らす（pandas 等を使用せず標準ライブラリ + duckdb）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes
- 今後の課題として、order 実行関連（strategy / execution）、監視（monitoring）モジュールの実装拡充や、単体テスト・統合テストの追加、CI による自動検証、より詳細な品質チェックルールの実装が想定されます。
- OpenAI API キーは引数で注入可能（api_key）であり、環境変数 OPENAI_API_KEY を使うこともできます。テスト時はキー不要で API 呼び出しをモックすることを推奨します。