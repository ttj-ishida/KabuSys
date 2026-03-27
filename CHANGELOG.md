CHANGELOG
=========
（このCHANGELOGは Keep a Changelog 準拠の要約です。コードベースの内容から推測して作成しています。）

Unreleased
----------
- なし

0.1.0 - 2026-03-27
-----------------
Added
- パッケージ初期リリース: kabusys v0.1.0 を追加。
  - パッケージ公開 API: kabusys.__all__ = ["data", "strategy", "execution", "monitoring"]。
- 環境設定 / ロード機能（kabusys.config）
  - .env/.env.local ファイルの自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export KEY=val 形式やクォート・エスケープ、行末コメントなどを考慮した独自の .env パーサーを実装。
  - OS 環境変数を保護する protected 機構、override フラグのサポート、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 必須環境変数取得用の _require ユーティリティと Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - 設定項目: DB パスのデフォルト（duckdb/data/kabusys.duckdb, sqlite/data/monitoring.db）、環境（development/paper_trading/live）とログレベルのバリデーション、is_live/is_paper/is_dev プロパティを実装。
- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON モードで銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores に書き込む。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST を UTC に変換）計算機能（calc_news_window）。
    - バッチ処理（1コール最大 BATCH_SIZE=20 銘柄）、1銘柄あたり記事トリム（最大記事数/文字数）によりトークン肥大を抑制。
    - API 呼び出しのリトライ（429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフで最大 _MAX_RETRIES 回）およびレスポンスの厳密なバリデーション処理を実装。
    - レスポンスの JSON 抽出・フォールバック、スコアのクリッピング（±1.0）、部分成功時の DB 置換ロジック（該当 code のみ DELETE → INSERT）を採用。
    - テストしやすさのため _call_openai_api をモック差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime に冪等書き込みする score_regime を実装。
    - マクロ記事のフィルタリング（定義済みマクロキーワード群）・最大記事数制限、OpenAI 呼び出しの同様のリトライ/フェイルセーフ処理（失敗時は macro_sentiment=0.0）を実装。
    - レジーム合成スコアのクリップや閾値によるラベリング、トランザクション（BEGIN/DELETE/INSERT/COMMIT）と ROLLBACK のフォールバックを実装。
    - 設計方針としてルックアヘッドバイアスを防ぐため datetime.today()/date.today() を参照しない実装になっている点を明記。
- データ処理 / ETL / カレンダー（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を使った営業日判定 API（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を実装。
    - DB 登録がない場合は曜日ベース（土日除外）でのフォールバックを行い、DB と一貫した挙動を保証。
    - calendar_update_job により J-Quants からの差分フェッチ・バックフィル・健全性チェック（異常に将来の last_date の検出時はスキップ）・保存処理を実装。
  - ETL パイプライン基盤（kabusys.data.pipeline / kabusys.data.etl）
    - ETL 実行結果を表現する ETLResult データクラスを提供（取得数・保存数・品質チェック結果・エラー一覧を保持）。
    - 差分取得、backfill、品 質チェック（quality モジュール利用）を想定した設計。DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティを含む。
    - ETLResult.to_dict() は quality_issues をシリアライズ可能な形式に変換。
  - jquants_client を介した外部クライアント連携を想定（fetch/save 関数を利用する設計）。
- リサーチ / ファクター（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン, ma200_dev）、Volatility（20日 ATR / ATR比 / 20日平均売買代金 / 出来高比）、Value（PER, ROE）を DuckDB 上で計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 扱いや、スキャン範囲にバッファ（calendar 日数換算）を設ける設計を採用。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、任意ホライズンをサポート、入力検証あり）。
    - IC（Information Coefficient）計算（スピアマンのランク相関を実装する calc_ic）。
    - ランク化ユーティリティ（rank: 同順位は平均ランク）、ファクター統計サマリ（factor_summary）を提供。
- ロギングと安全性
  - 各所で警告・情報ログを適切に出力し、例外発生時のトランザクションロールバックや警告ログを導入。
  - API 呼び出し失敗時はフェイルセーフ（スコア 0.0 あるいはスキップ）を採用し、システム全体の継続性を重視。

Changed
- 初回公開のため変更履歴なし。

Fixed
- 初回公開のため修正履歴なし。ただしコードには以下の堅牢化が含まれる:
  - .env 読み込み時のファイルアクセス例外を warnings.warn で通知して処理継続。
  - DuckDB の executemany 空リスト問題に対応するチェック（空パラメータ群は実行しない）。
  - OpenAI API レスポンスパース失敗や HTTP 5xx に対して明確なログとフォールバックを追加。

Security
- 環境変数の自動ロードにおいて OS 環境変数を protected として上書きから隔離する設計を採用。
- API キーは関数引数で注入可能（テスト容易性）かつ未設定時は明確な ValueError を投げる。

Notes / Requirements
- OpenAI API（gpt-4o-mini）を利用する機能（score_news, score_regime）は OPENAI_API_KEY の設定が必要。未設定時は ValueError を送出する。
- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings のプロパティ参照で必須チェックされる）。
- データストアは DuckDB を想定（接続オブジェクトを各関数に注入）。デフォルトの duckdb ファイルパスは data/kabusys.duckdb。
- 設計上、ルックアヘッドバイアスを防ぐため date/times の取得は呼び出し側で行い、モジュール内部では datetime.today()/date.today() を直接参照しない実装方針を採用。

（以上）