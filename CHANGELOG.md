# Keep a Changelog
すべての重要な変更をこのファイルに記録します。  
このプロジェクトはセマンティックバージョニング (https://semver.org/) に従います。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-28
初回リリース。

### Added
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート: data, strategy, execution, monitoring

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local を自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env のパース機能を実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - クォートなし値でのインラインコメント処理（直前がスペース/タブの場合のみ '#' をコメントとして扱う）。
    - 無効行（空行・コメント・誤った行）をスキップ。
  - _load_env_file によるファイル読み込みで:
    - 既存の OS 環境変数を保護する protected 引数を導入（.env.local は override=True だが protected により OS 環境変数は上書きされない）。
    - ファイル読み込み失敗時に警告を出す。
  - Settings クラスを導入し型安全に設定を取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須キーを _require で検証。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等のデフォルト値を提供。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）と便利なプロパティ is_live / is_paper / is_dev。

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）の JSON mode を使ってセンチメントを算出。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST に対応する UTC の範囲）を calc_news_window として提供。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの最大記事数・文字数トリム、結果のバリデーション、スコアの ±1.0 クリップ。
    - レート制限/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ、失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みは部分失敗時に既存データを保護するため、対象コードのみ DELETE → INSERT を実施。executemany の空リストに対する注意喚起（DuckDB 互換性）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull / neutral / bear）。
    - prices_daily, raw_news, market_regime テーブルを参照し、冪等に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - マクロニュースは kwords でフィルタ、最大記事数制限、LLM 呼び出しは独立実装。API 失敗時は macro_sentiment = 0.0 として継続。
    - OpenAI 呼び出しのリトライ・エラー処理（RateLimit, APIConnectionError, APITimeout, APIError の扱い）を実装。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算する calc_momentum。
    - Volatility / Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算する calc_volatility。
    - Value: raw_financials から最新の財務指標を取り出し PER, ROE を計算する calc_value。
    - DuckDB によるウィンドウ関数を活用した実装、データ不足時の None 処理、ログ出力。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（任意ホライズン、入力検証）。
    - IC 計算 calc_ic（Spearman ランク相関）と rank ユーティリティ（同順位は平均ランク処理、丸め対策）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。

- Data モジュール（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを定義（取得件数・保存件数・品質チェック結果・エラー一覧を格納）。
    - 差分更新、バックフィル、品質チェックのためのユーティリティ関数（_get_max_date 等）。
    - 市場カレンダー補助（_adjust_to_trading_day 等）を実装（後続処理に利用）。
  - calendar_management モジュール
    - market_calendar を元に営業日判定や next/prev_trading_day / get_trading_days / is_sq_day 等のユーティリティを提供。
    - DB データ優先、未登録日は曜日ベースのフォールバック、最大探索日数制限で無限ループ回避。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル・健全性チェック含む）。
  - jquants_client を利用したカレンダー取得保存処理の採用（外部 API クライアントとの連携ポイント）。

- API/実装上の設計方針（全体）
  - ルックアヘッドバイアス回避のため、datetime.today()/date.today() を直接参照しない設計（関数引数で target_date を受ける）。
  - DuckDB を主要なデータストアとして想定し、SQL（ウィンドウ関数等）と Python の組合せで処理を実装。
  - DB 書き込みは冪等性を意識（DELETE → INSERT、ON CONFLICT 相当）しトランザクション管理（BEGIN/COMMIT/ROLLBACK）を明示。
  - ロギング/警告を多用し、外部 API 失敗時は例外を直接投げずフォールバックして継続する（フェイルセーフ）箇所を多く設ける。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Removed
- 初版のため該当なし。

### Security
- 環境変数の自動ロードで OS 環境変数を保護する仕組み（protected set）を導入し、意図しない上書きを防止。

Notes:
- OpenAI 連携部分は外部キー（OPENAI_API_KEY）を要求するため、本番で利用する際は適切に API キーを設定してください。
- DuckDB のバージョン間の差異（executemany に空リストを渡せない等）に考慮した実装が含まれます。運用環境での互換性確認を推奨します。