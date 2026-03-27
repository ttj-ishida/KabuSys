CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

[0.1.0] - 2026-03-27
-------------------

Added
- 初期リリース: kabusys パッケージ（__version__ = 0.1.0）。
- 環境設定管理（kabusys.config）
  - プロジェクトルートを .git または pyproject.toml から自動検出して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ対応、行末コメントの扱い（クォート有無での取り扱いを区別）。
    - override フラグと protected（OS 環境変数保護）を考慮した環境変数の読み込み。
  - Settings クラスを提供し、主要設定プロパティを公開（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等）。値検証（env と log level の有効性チェック）を実装。
- AI（kabusys.ai）
  - news_nlp モジュール:
    - raw_news と news_symbols を集約して銘柄ごとに記事を結合し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントスコアを算出。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に合わせて扱う calc_news_window）。
    - 1チャンク最大 20 銘柄、1銘柄当たりの記事数・文字数上限でトリム。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ、レスポンスの厳密バリデーション（JSON 抽出、results 配列、code/score 検証）、スコアを ±1.0 にクリップ。
    - 成功銘柄のみ ai_scores テーブルへ（DELETE → INSERT）で冪等的に書き込み。戻り値は書き込んだ銘柄数。
    - API キー未設定時に ValueError を送出。
  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム判定（'bull' / 'neutral' / 'bear'）を行う score_regime を提供。
    - マクロニュース抽出（キーワード一覧によるタイトルフィルタ）、OpenAI 呼び出し（gpt-4o-mini、JSON Mode）による macro_sentiment 評価、API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - レジームスコアの合成ロジック、しきい値判定、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API キー未設定時に ValueError を送出。
  - OpenAI 呼び出しラッパーはテスト用に差し替え可能（ユニットテスト用に patch を想定）。
- Research（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials から直近財務データを取得して PER / ROE を計算（EPS が 0/欠損時は None）。
    - すべて DuckDB 接続を受け取り SQL ベースで高速に計算。結果は (date, code) ベースの dict リストで返却。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。ホライズンの妥当性チェックあり。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算（有効レコード < 3 の場合は None）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）、統計サマリ（count/mean/std/min/max/median）を提供。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
- Data（kabusys.data）
  - calendar_management:
    - market_calendar テーブルを利用した営業日判定 API（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants API からの差分取得、バックフィル（直近数日再取得）と健全性チェック実装。jquants_client 経由での取得 → jq.save_market_calendar による冪等保存。
  - pipeline（ETL）:
    - ETLResult データクラス（target_date、取得/保存カウント、quality_issues、errors、ヘルパプロパティ等）。
    - 差分取得用の最大日付取得ユーティリティ、backfill ロジック、品質チェック統合のためのフック設計。DuckDB を前提とした idempotent な保存を想定。
  - etl モジュールは ETLResult を公開。
- 共通設計/運用面の追加
  - 主要モジュールで「ルックアヘッドバイアス防止」のため datetime.today()/date.today() を直接参照しない設計を採用（target_date を明示的に受け取る）。
  - DuckDB を主要な分析 DB として利用（関数は DuckDBPyConnection を引数に取る）。
  - ロギングと詳細な警告メッセージを各処理に追加。
  - 多くの DB 書き込み処理はトランザクション（BEGIN/COMMIT/ROLLBACK）を用いて冪等性と整合性を確保。
  - API 呼び出しに対してリトライ（指数バックオフ）とフェイルセーフ（スコア 0.0／スキップ）ポリシーを導入。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Known issues / Notes
- パッケージ公開時点では monitoring モジュールはパッケージの __all__ 等で言及されているが、対応する実装が別途提供される可能性があります（利用時は実装の有無を確認してください）。
- J-Quants / kabuステーション / Slack / OpenAI 等の外部サービス利用には環境変数設定が必須。設定がない場合は一部 API 呼び出しで ValueError が発生します（エラーメッセージで案内）。
- DuckDB の executemany に関する互換性（空リスト不可）を考慮した実装になっています。古い DuckDB バージョンでの挙動には注意してください。

References
- 各モジュールは README / DataPlatform.md / StrategyModel.md 等の設計文書に基づいて実装されています（コード内の docstring に詳細説明あり）。