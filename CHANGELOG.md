CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠し、セマンティックバージョニングを採用します。
(https://keepachangelog.com/ja/1.0.0/)

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-29
--------------------

初回リリース。以下の主要機能・モジュールを実装・公開しました。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（バージョン 0.1.0）。
  - パッケージ __all__ に data, strategy, execution, monitoring を定義。

- 設定 / 環境管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を読み込む（配布後も CWD に依存しない検索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できる。
    - OS 環境変数は保護（protected）され、.env の上書きが不要な限り行われない。
  - .env パーサーは以下に対応：
    - 空行・コメント行、export KEY=val 形式、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い（クォート有無での挙動差異）。
  - Settings クラスを提供し、アプリケーション設定をプロパティで取得：
    - J-Quants / kabuステーション / Slack / DB パス / 環境フラグ (env/is_live/is_paper/is_dev) / log_level 等。
    - 必須項目未設定時は ValueError を送出。
    - env/log_level の値検証（許容値の定義）。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を基に銘柄毎のニュースを集約し、OpenAI（gpt-4o-mini）によりセンチメントを算出する機能を実装（score_news）。
  - 特徴：
    - JST ベースのタイムウィンドウ（前日 15:00 ～ 当日 08:30）を計算する calc_news_window。
    - 1 銘柄あたりの記事数・文字数を制限してトークン膨張を抑制（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - バッチ（最大 20 銘柄）での API 呼び出し、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - OpenAI JSON mode を前提としたレスポンスバリデーション（results リスト、code/score 検証、数値クリップ）。
    - 部分失敗時にも既存スコアを保護するため、対象コードのみを DELETE → INSERT で置換する冪等書き込み戦略。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に実装。
    - API キー注入（api_key 引数 or OPENAI_API_KEY 環境変数）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
  - 特徴：
    - DuckDB から過去データのみ（target_date 未満）を取得してルックアヘッドバイアスを排除。
    - マクロニュース抽出はキーワードベース（複数キーワード）でフィルタし、最大記事数を制限。
    - OpenAI 呼び出しに対する再試行ロジック、API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコアは所定の閾値でラベル付けし、market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT）。書込み失敗時は ROLLBACK を試行。
    - news_nlp と共通する点はあるが、モジュール結合防止のため OpenAI 呼び出し関数は独立実装。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間差分更新処理（calendar_update_job）を実装。J-Quants クライアント経由で差分取得 → 冪等保存。
    - 営業日判定/取得ユーティリティを提供：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーがある場合は DB 値優先、未登録日は曜ベースでフォールバックする一貫した挙動。
    - 最大探索範囲やバックフィル、健全性チェック（将来日付の異常検出）などの保護機構を実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを実装し、ETL の取得数・保存数・品質問題・エラー等を格納・集計できるようにした。
    - 差分取得ロジック、backfill、品質チェック（quality モジュール）との連携設計を含む。
    - _get_max_date、_table_exists などの汎用 DB ヘルパーを実装。
  - etl モジュールは ETLResult を再エクスポート。

- 研究用ユーティリティ（kabusys.research）
  - factor_research
    - モメンタム、ボラティリティ、バリュー系の量的ファクターを計算する関数を実装:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離（行数不足時は None）
      - calc_volatility: 20日 ATR, ATR 比率, 20日平均売買代金, 出来高比率
      - calc_value: PER（EPS が 0/欠損の場合は None）, ROE（財務データ取得ロジック）
    - DuckDB のウィンドウ関数を活用し、営業日ベースの窓を考慮。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算。入力検証（horizons 範囲）あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 件未満の場合は None。
    - rank: 同順位は平均ランクとするランク付け。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - zscore_normalize は kabusys.data.stats から再利用可能（__init__ で再エクスポート）。

Design / Implementation Notes
- DuckDB を主要な分析用ローカル DB として使用。SQL と Python の組合せで処理を記述。
- すべての分析系/AI 系処理は内部で datetime.today()/date.today() を直接参照せず、target_date ベースで動作する設計（ルックアヘッドバイアス防止）。
- OpenAI への呼び出しは JSON mode を利用し、レスポンスの堅牢なバリデーションと失敗時のフェイルセーフ（スコア 0 や部分スキップ）を採用。
- テストしやすさを考慮し、外部 API 呼び出しポイント（_call_openai_api 等）を差し替え可能に実装。
- DB 書込みは可能な限り冪等化（DELETE → INSERT、ON CONFLICT（外部クライアント側）等）し、部分失敗時に既存データを守る工夫を実装。
- ログ出力と警告（logger.warning / logger.info / logger.exception）を各所に配置して運用時の可観測性を確保。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Removed
- なし（初回リリース）

Notes
- OpenAI API キーや各種トークンは設定が必須なものがあり、未設定時はValueError が発生します（使用前に .env または環境変数の設定を推奨）。
- 今後のリリースでは、strategy / execution / monitoring 関連の実装詳細やテストカバレッジ、ドキュメントの拡充を予定しています。