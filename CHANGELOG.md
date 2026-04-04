CHANGELOG
=========
この CHANGELOG は "Keep a Changelog" のフォーマットに準拠しています。  
このファイルはコードベース（kabusys）から推測した変更点・新機能・設計上の注意点をまとめたもので、リリース履歴の初期版として作成しています。

Unreleased
----------
- 今後の予定（実装予定・改善案）
  - execution / monitoring モジュールのユーザー向け機能強化（実取引周りの安全性向上、監視用メトリクスのエクスポートなど）
  - backtesting / シミュレーション機能の拡充（Strategy の検証ワークフロー）
  - ドキュメント・型注釈の追加強化と CI テストの整備
  - OpenAI 呼び出しのメトリクス収集（コスト監視・レイテンシ計測）
  - DuckDB スキーマのマイグレーション支援ツール

[0.1.0] - 2026-04-04
-------------------
初回リリース。日本株自動売買システムの基盤となる以下の主要コンポーネントを追加しました。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0、主要サブパッケージを __all__ に公開）。
- 設定・環境変数管理（kabusys.config）
  - .env / .env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env 行パーサの実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - Settings クラスによる設定 API（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境モード判定等）。
  - 必須環境変数取得ヘルパー（未設定時は ValueError を送出）。
- AI モジュール（kabusys.ai）
  - news_nlp（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集計し、OpenAI（gpt-4o-mini）に JSON Mode で一括問い合わせして銘柄別センチメント（ai_score）を算出。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたり記事数・文字数制限（デフォルト: 最大10記事・3000文字）。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx 対応、指数バックオフ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リストの検査、コード照合、数値チェック、±1.0 でクリップ）。
    - DuckDB への書き込みは部分成功を許容する方式（対象コードのみ DELETE → INSERT、executemany の空リスト回避措置）。
    - テスト用フック: _call_openai_api をパッチして API 呼び出しを差し替え可能。
    - 時刻ウィンドウの計算（JST基準で前日15:00〜当日08:30 相当の UTC 範囲）。
  - regime_detector（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出はキーワードベース（日本／米国・グローバルの主要語句群）。
    - OpenAI 呼び出しは JSON Mode、リトライとエラー時のフォールバック（macro_sentiment=0.0）。
    - LLM レスポンスパース失敗や API 障害は例外にせず警告ログでフェイルセーフ。
    - テスト用フック: _call_openai_api をパッチ可能。
- データプラットフォーム（kabusys.data）
  - calendar_management（kabusys.data.calendar_management）
    - JPX カレンダー管理（market_calendar テーブルの参照・更新、祝日/半日/SQ判定、営業日取得ユーティリティ）。
    - DB データがない場合は曜日ベースのフォールバック（平日を営業日と扱う）。
    - next_trading_day / prev_trading_day / get_trading_days の最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループ防止。
    - calendar_update_job による J-Quants からの差分取得とバックフィル（直近 _BACKFILL_DAYS の再フェッチ）、健全性チェック（未来日付の異常検出）。
  - pipeline / ETL（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult dataclass を公開（取得件数、保存件数、品質問題、エラーメッセージ等をまとめて返却）。
    - 差分取得、保存（jq.save_* を使った idempotent 保存）、品質チェック統合の設計方針を実装。
    - DuckDB のテーブル存在チェックや最大日付取得などのユーティリティ。
- リサーチ・ファクター（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M のリターン、ma200 乖離（必要データ不足時は None）を算出。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率などを算出。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出。
    - すべて DuckDB と prices_daily / raw_financials テーブルのみ参照（現物注文等の外部作用なし）。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（horizons のバリデーションあり）。
    - calc_ic: スピアマンのランク相関（IC）を計算するユーティリティ（不足レコード時は None）。
    - rank / factor_summary: ランク付け、ファクター統計サマリー（count/mean/std/min/max/median）。
  - research パッケージは主要関数を __all__ で再エクスポート。
- 実装上の設計・安全策（ドキュメントより抽出）
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を直接参照する実装を最小化し、外部から target_date を与える設計。
  - トランザクション制御: DuckDB に対する書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等パターンを使用。失敗時は ROLLBACK を試行。
  - OpenAI 呼び出しの堅牢性: リトライ（指数バックオフ）、5xx の扱い、JSON パースの回復処理。
  - テスト容易性: 外部 API 呼び出しポイントの差し替え（_call_openai_api の patch）を想定。
  - DuckDB 互換性配慮: executemany に空リストを渡さないチェックなど（DuckDB 0.10 の制約回避）。
- 既定値・環境
  - DBパスや監視ファイルのデフォルトパス設定（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）。
  - システムモード検証（KABUSYS_ENV は development|paper_trading|live、LOG_LEVEL の検証）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 機密情報は環境変数での注入を想定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）。.env ファイルはプロジェクトルートから自動で読み込まれるが、KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを抑制可能。
- OpenAI キー未設定時は AI に依存する関数（score_news, score_regime）が ValueError を送出して明示的にエラーにする。

Known issues / Limitations
- schema の事前準備が必要:
  - 本ライブラリは DuckDB 上で特定のテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）を参照/更新します。これらのテーブルは ETL やスキーマ作成処理で事前に用意しておく必要があります。
- OpenAI API 呼び出しにはコストとレイテンシがかかるため、運用時は呼び出し頻度とバッチサイズを調整してください。
- news_nlp の JSON Mode は LLM の挙動に依存するため、将来的にレスポンス形式の微妙な変化が起きる可能性があります（パース回復処理は入れているが、完全ではありません）。
- execution / monitoring の公開 API（実取引・監視ランナー）は本リリースでは限定的なため、本番運用前に十分なレビュー・テストが必要です。

Upgrade notes
- 既存の環境から本バージョンへ移行する場合:
  - 必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY など）を用意してください。
  - DuckDB のスキーマが本ライブラリの期待するテーブル・カラム構成になっていることを確認してください。
  - .env/.env.local を利用する場合、OS 環境変数を保護するため .env.local が .env を上書きする挙動がある点に注意してください。

Contributors
- 初期実装: 開発者チーム（コード内コメント・設計記述に基づく）

-- End of CHANGELOG --