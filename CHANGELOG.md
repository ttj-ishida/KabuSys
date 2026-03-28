CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報: src/kabusys/__init__.py に __version__ = "0.1.0"、主要サブパッケージをエクスポート（data, strategy, execution, monitoring）。
- 環境変数・設定管理（src/kabusys/config.py）
  - .env/.env.local 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DBパス 等の設定取得プロパティを提供。
    - 必須環境変数は _require() で明示的に検査し、未設定時には ValueError を発生。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値を限定）。
    - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"（expanduser 対応）。
- ニュース NLP モジュール（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を基に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ書き込むワークフローを実装。
  - 時間ウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）を UTC に変換して使用（calc_news_window を公開）。
  - バッチ処理: 1 API コールで最大 _BATCH_SIZE(20) 銘柄を処理、1銘柄当たり最大記事数/文字数でトリム（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
  - OpenAI 呼び出しは JSON mode を利用し、レスポンスを厳密に検証（_validate_and_extract）。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数的バックオフリトライ（_MAX_RETRIES=3, _RETRY_BASE_SECONDS=1.0）。
  - スコアは ±1.0 にクリップして保存。
  - DuckDB 側の互換性を考慮し、executemany に空リストを渡さない安全処理を導入（DuckDB 0.10 対応）。
  - テスト用に OpenAI 呼び出し関数を patch で差し替え可能に設計（_call_openai_api をローカル定義）。
- 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離 (MA) とニュース NLP によるマクロセンチメントを合成して日次レジーム（bull/neutral/bear）を判定する機能を実装。
  - 合成ルール: MA 重み 0.7（スケール係数 10）、マクロ重み 0.3、出力を [-1,1] にクリップ。閾値でラベル判定（BULL_THRESHOLD/BEAR_THRESHOLD）。
  - マクロニュース抽出（_fetch_macro_news）・LLM スコア取得（_score_macro）を実装。LLM 呼び出し失敗時はフェイルセーフとして macro_sentiment=0.0 を利用。
  - DuckDB に対する冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装し、失敗時は ROLLBACK とログ出力。
  - API クライアントは OpenAI SDK（OpenAI(api_key=...)）を利用。テスト用に _call_openai_api を差し替え可能。
- リサーチ（ファクター）モジュール（src/kabusys/research/*）
  - ファクター計算: calc_momentum, calc_value, calc_volatility を実装（prices_daily / raw_financials を参照）。
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。データ不足時は None を返す。
    - Volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を算出。
    - Value: latest 財務情報（raw_financials）を用いて PER・ROE を算出。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）:
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）で LEAD を用いたリターン取得。horizons の入力検証あり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関をランク関数で実装。データが少ない場合は None を返す。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク、浮動小数誤差対策の丸めを実施。
  - research パッケージの公開 API を整理（__all__ に主要関数を列挙）。
- データプラットフォーム: カレンダー管理（src/kabusys/data/calendar_management.py）
  - JPX カレンダー管理ロジックを提供:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar が未取得の場合は曜日ベース（土日非営業日）でフォールバック。
    - DB 登録あり → DB 値優先、未登録日は曜日フォールバックで整合性を保つ。
    - calendar_update_job: J-Quants API（jquants_client.fetch_market_calendar）から差分取得し保存、バックフィル直近 _BACKFILL_DAYS を常に再フェッチ。健全性チェックで過度の未来日付はスキップ。
- データ ETL（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
  - ETLResult データクラスを実装し ETL 実行結果（フェッチ/保存件数、品質問題、エラー等）を集約。to_dict で品質問題をシリアライズ可能。
  - 差分取得・バックフィル・品質チェックの設計（DataPlatform.md に基づく実装方針を反映）。
  - 内部ユーティリティ: テーブル存在チェック・最大日付取得などを実装。
  - etl パッケージは pipeline.ETLResult を再エクスポート。
- データアクセス互換性のための細かな配慮
  - DuckDB の場合分け（ROW_NUMBER を使った latest_fin の取得等）、executemany の空リスト回避など互換性対応を実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数注入または環境変数（OPENAI_API_KEY）で解決。未設定時は ValueError を投げ、誤使用を防止。

Notes / 設計上の重要ポイント（ドキュメントとして）
- ルックアヘッドバイアス防止:
  - News/Regime/Research モジュールは internal において datetime.today() / date.today() を参照せず、呼び出し側から target_date を与える設計。
  - DB クエリでは target_date 未満 / 排他条件等を用いてルックアヘッドを防止。
- フェイルセーフ:
  - LLM/API 失敗時は例外を全体に投げず、フェイルセーフ値（例: macro_sentiment=0.0）で継続する箇所がある。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、ROLLBACK 失敗時のログ出力も実装。
- テスト容易性:
  - OpenAI 呼び出しをラップした内部関数を定義し、unittest.mock.patch で差し替え可能にしている。

今後
- strategy / execution / monitoring の実装拡張（現状はパッケージスケルトンを公開）。
- 追加の品質チェックルールやバックテスト用ユーティリティの拡充。