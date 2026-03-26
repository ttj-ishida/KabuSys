# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。セマンティックバージョニングを採用しています。

[0.1.0] - 2026-03-26
====================

Added
-----
- 初回リリース (0.1.0)。
- パッケージの公開エントリポイントを追加
  - kabusys.__version__ = 0.1.0
  - __all__ に data, strategy, execution, monitoring を設定。

- 環境設定/自動 .env ロード機能（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み。
  - 読み込み順: OS 環境変数 > .env.local > .env。`.env.local` は上書き（override）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - 高度な .env パース実装（export プレフィックス、クォート内エスケープ、インラインコメント判定等）。
  - 必須環境変数取得ヘルパー _require を提供。
  - Settings クラスで主要設定をプロパティで提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）、DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証、is_live/is_paper/is_dev 補助）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - 環境変数未設定時は明確なエラーを送出。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini / JSON Mode）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime に変換）。
    - バッチサイズ: 最大 20 銘柄／コール。1 銘柄あたり最大 10 記事・3000 文字でトリム。
    - 再試行: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフで再試行（最大リトライ回数設定）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、"results" 配列、code/score 検証、未知コードは無視、スコアを ±1.0 にクリップ）。
    - 書き込み: 成功した銘柄のみ ai_scores テーブルへ置換（DELETE → INSERT）して部分失敗時に既存データを保護。
    - テスト容易性: OpenAI 呼び出しは内部 _call_openai_api を patch で差し替え可能。
    - score_news は書き込んだ銘柄数を返す。

  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュース LLM センチメントを合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window を用いてウィンドウ抽出し、定義済みのマクロキーワードでタイトルを抽出。
    - 合成ロジック: 重み 70%（MA 乖離） / 30%（マクロセンチメント）、スコアを -1.0〜1.0 にクリップ。閾値により label を分類。
    - OpenAI 呼び出しで失敗した場合は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - 書き込み: market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）し、失敗時は ROLLBACK 試行と警告ログ。
    - テスト容易性: _call_openai_api を patch で置き換え可能。
    - score_regime は成功時に 1 を返す。

  - 共通設計方針
    - 両モジュールともルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない。target_date を明示的に渡す設計。
    - OpenAI の JSON Mode を利用し、堅牢なパース・フォールバック処理を実装。
    - gpt-4o-mini をデフォルトモデルとして使用。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar テーブルに基づく営業日判定ユーティリティ:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック（週末は非営業日）。
    - 最大探索範囲を設定して無限ループを防止（_MAX_SEARCH_DAYS）。
    - calendar_update_job を実装: J-Quants API から差分取得し market_calendar を冪等（ON CONFLICT）に保存。バックフィル・健全性チェックあり。
    - jquants_client と連携して fetch/save を行う。

  - ETL パイプライン（pipeline）
    - ETLResult dataclass を公開（kabusys.data.etl で再エクスポート）。
      - ETL 実行結果、品質チェック結果、エラーリストなどを保持し、to_dict によるシリアライズを提供。
    - 差分更新、バックフィル、品質チェックを念頭に置いた設計（詳細実装は pipeline 内部ユーティリティ含む）。
    - DuckDB 上での最大日付取得やテーブル存在チェック等のユーティリティ実装。

- リサーチモジュール（kabusys.research）
  - ファクター計算（factor_research）
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。データ不足時は None。
    - calc_value: raw_financials から最新財務データを取得し PER/ROE を計算（EPS=0/欠損時は None）。
    - DuckDB の SQL ウィンドウ関数を利用し高効率に集計。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。horizons のバリデーションを実施。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満なら None。
    - rank: 同順位は平均ランクとするランク変換を提供（丸め処理で ties の検出漏れを回避）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - kabusys.research.__init__ で主な関数と kabusys.data.stats.zscore_normalize を再公開。

- その他
  - DuckDB を想定した API（関数引数は DuckDBPyConnection を受け取る）で、ローカル DB（.duckdb）上での処理を前提に設計。
  - 各所でログ出力（logger）を充実させ、警告・エラー時のフォールバック挙動を明示。
  - トランザクション処理時の冪等性とエラーハンドリング（ROLLBACK 試行・警告ログ）を徹底。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Removed
-------
- （初回リリースのため該当なし）

Security
--------
- OpenAI API キーは明示的に api_key 引数または環境変数 OPENAI_API_KEY を必要とする。未設定時は ValueError を送出して誤動作を防止。

Notes / Usage tips
------------------
- テスト時や CI で自動 .env 読み込みを抑制したい場合、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出し部分はユニットテストで差し替え可能な内部関数（_call_openai_api）が用意されています。
- DuckDB のバージョン依存（executemany の空リスト不可など）に対する注意点がコード中に記載されています。
- ai 系処理は API 失敗時に安全側のフォールバック（スコア 0.0 やスキップ）を行うため、外部 API の一時障害に対しても堅牢です。

---  
今後のリリースでは、strategy / execution / monitoring の実装追加、テスト補強、ドキュメント（Usage & Deployment）の整備を予定しています。