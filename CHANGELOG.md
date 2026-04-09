Keep a Changelog
=================

すべての重要な変更をここに記録します。  
本ファイルは Keep a Changelog のフォーマットに準拠しています。

フォーマット
----------
- 変更は "Added", "Changed", "Deprecated", "Removed", "Fixed", "Security" のカテゴリで記載します。
- バージョンごとにリリース日を付与します。

[0.1.0] - 2026-04-09
-------------------

Added
-----
- 基本パッケージ初期実装
  - パッケージ名: kabusys、バージョン 0.1.0。
  - パッケージルートでの公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読込機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env 行パーサの実装:
    - export KEY=val 形式、クォート、バックスラッシュエスケープ、インラインコメント対応（スペース直前の # をコメントと認識）などを考慮。
  - Settings クラスを提供し、環境変数経由で設定値をプロパティとして取得可能:
    - J-Quants / kabuステーション / LINE / DB パス（DuckDB/SQLite） / 監視（PID/killフラグ/閾値） / システム（環境、ログレベル）など。
  - 必須環境変数チェック (_require) と値検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）を実装。

- AI / NLP 機能 (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメントを算出。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり最大記事数・文字数の制限、JSON Mode 使用。
    - 再試行（429/ネットワーク/TCP タイムアウト/5xx）に対する指数バックオフ実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、resultsキーと型検査、未知コード除外、数値の有限性チェック）とスコアの ±1.0 クリップ。
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存データを保護）。
    - テスト容易性: _call_openai_api をモック差し替え可能。
    - calc_news_window: タイムウィンドウ（JST 前日 15:00 〜 当日 08:30 相当の UTC 範囲）計算を提供。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 (日経225連動) の 200 日移動平均乖離 (重み 70%) とマクロニュース LLM センチメント (重み 30%) を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - ma200_ratio の計算、マクロキーワードに基づく raw_news 抽出、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント算出、重み付け合成、結果の market_regime テーブルへの冪等書き込みを実装。
    - API エラーやレスポンスパース失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - OpenAI 呼び出しは独立実装（news_nlp と内部関数を共有しない）でモジュール結合を避ける。
    - 再試行・バックオフ、5xx 判定、最大リトライ回数を実装。

- データ基盤機能 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を用いた営業日判定 API を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダーがない/未登録日の場合は曜日ベース（平日を営業日）でフォールバックする一貫した振る舞い。
    - next/prev_trading_day は最大探索範囲（_MAX_SEARCH_DAYS）を設けて無限ループを防止。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等保存。バックフィルと健全性チェック（将来日付の異常検出）を実装。
    - DuckDB 型変換ユーティリティ、テーブル存在チェック等の内部ユーティリティを実装。

  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETL の高レベル設計に基づく ETLResult データクラスを公開（kabusys.data.etl は ETLResult を再エクスポート）。
    - 差分更新、バックフィル、品質チェック連携（quality モジュール）を想定した設計。ETLResult は品質問題・エラー情報を保持し、has_errors / has_quality_errors プロパティ、辞書変換メソッドを提供。
    - jquants_client 経由の保存関数呼び出しを前提とした構成。

- リサーチ機能 (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム: mom_1m, mom_3m, mom_6m, ma200_dev（200 日 MA 乖離）。不足データ時の None ハンドリング。
    - ボラティリティ/流動性: 20 日 ATR (atr_20), atr_pct, avg_turnover, volume_ratio。true_range の NULL 伝播制御。
    - バリュー: PER（EPS が 0 / 欠損なら None）、ROE（raw_financials の最新レコードを使用）。
    - 各関数は prices_daily / raw_financials のみ参照し副作用なし。結果は (date, code) をキーとする dict のリストで返却。

  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算: calc_forward_returns（デフォルト horizons=[1,5,21]）、lead/lag を用いた一括 SQL 取得。
    - IC 計算: calc_ic（Spearman ランク相関を実装）、欠損や ties の扱い、最小有効サンプルチェック。
    - ランク計算ユーティリティ rank（同順位は平均ランク）。
    - ファクター統計サマリ: factor_summary（count/mean/std/min/max/median）。

Changed
-------
- （初版のため該当なし）

Fixed
-----
- （初版のため該当なし）

Security
--------
- 環境トークン等の取り扱いに関する注意:
  - OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出して明示的に通知。
  - OS 環境変数は .env ロードで上書きされないよう保護（protected set を使用）。

Notes / ユーザー向け注意事項
--------------------------
- 必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（kabu API）, OPENAI_API_KEY（AI 機能を使用する場合）
- DuckDB を使用する設計のため、DuckDB 接続オブジェクト（DuckDBPyConnection）を多くの関数で受け取ります。
- AI モジュールは OpenAI のレスポンス形式に依存しており、レスポンス不正時はフェイルセーフで処理を続行します（スコア 0.0 を使用）。
- テスト容易性のため、各種内部関数（_call_openai_api 等）は unittest.mock.patch により差し替え可能です。
- 日付処理はルックアヘッドバイアス回避のため、datetime.today()/date.today() を直接参照せず、target_date に基づく計算を行う設計になっています（再現性重視）。

今後の予定（非網羅）
-------------------
- strategy / execution / monitoring 周りの実装拡張（現リリースではトップレベルの公開のみ）。
- ETL の具体的な差分取得ロジック・quality チェックの詳細実装強化。
- テストカバレッジと例外処理の更なる堅牢化。

---