保持された変更ログ (Keep a Changelog 準拠)
=======================================

すべての重要な変更はこのファイルに記録します。  
フォーマットの詳細は https://keepachangelog.com/ja/ を参照してください。

0.1.0 - 2026-03-26
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ名とバージョンは src/kabusys/__init__.py にて定義。

- 環境設定/ロード機能
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装（src/kabusys/config.py）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント等に対応。
  - Settings クラスを提供し、以下のプロパティ経由で必須/任意設定を取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV (development/paper_trading/live の検証), LOG_LEVEL（検証）
    - is_live / is_paper / is_dev のブール判定
  - 必須環境変数未設定時は ValueError を送出する振る舞いを採用。

- AI（LLM）モジュール
  - ニュース NLP スコアリング: score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols を集約して銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - OpenAI の gpt-4o-mini を JSON Mode で呼び出し、結果を ai_scores テーブルへ冪等的に書き込み。
    - バッチ処理（最大 20 銘柄/コール）、記事数/文字数トリム、リトライ（429/タイムアウト/ネットワーク/5xx に対する指数バックオフ）を実装。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリッピング。
    - API キー未指定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を送出。
    - テスト用に _call_openai_api をパッチ差し替え可能（unittest.mock で差し替えられる実装）。
  - 市場レジーム判定: score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して
      市場レジーム ('bull' / 'neutral' / 'bear') を算出し market_regime テーブルへ冪等書き込み。
    - マクロニュースは raw_news からマクロキーワードでフィルタして取得。
    - LLM 呼び出しは独立実装（モジュール間の内部関数共有を避ける設計）。
    - API 呼び出し失敗時は macro_sentiment=0.0 でフォールバックし継続（フェイルセーフ）。
    - リトライ/バックオフ、JSON パースの安全処理を実装。

- データ / ETL 機能
  - ETL の公開インターフェースとして ETLResult を提供（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py で再エクスポート）。
    - ETLResult は取得/保存件数、品質チェック結果、エラー一覧などを保持し、to_dict() で辞書化可能。
  - ETL パイプライン基盤を実装（差分取得、バックフィル、品質チェックの流れを想定）。
    - J-Quants クライアント経由の差分取得、idempotent 保存（ON CONFLICT 相当）を想定。
    - デフォルトのバックフィル日数やカレンダー先読みの定義を含む。
    - DuckDB を前提にした日付最大値取得ユーティリティ等を実装。

- カレンダー管理（JPX カレンダー）
  - market_calendar を使った営業日判定ユーティリティ群を実装（src/kabusys/data/calendar_management.py）:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - market_calendar が未取得時は曜日（土日）ベースのフォールバックを使用。
    - next/prev_trading_day は最大探索日数を制限して無限ループを防止。
  - 夜間バッチ更新 job（calendar_update_job）を実装:
    - J-Quants から差分取得し market_calendar を冪等更新。
    - バックフィル期間の再フェッチ、健全性チェック（未来日付が不正に大きい場合はスキップ）を実装。
    - API エラーや保存失敗時は例外を上位へ伝えず 0 を返してフェイルセーフに動作。

- リサーチ / ファクター計算
  - factor_research モジュールで以下のファクター計算を実装（prices_daily / raw_financials を参照）:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日 MA が不足時は None）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ウィンドウ不足時は None）
    - calc_value: per（EPS が 0/欠損なら None）, roe（raw_financials の最新報告を結合）
  - feature_exploration モジュールで統計解析ユーティリティを提供:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD で一括取得
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（有効レコードが 3 未満なら None）
    - rank: 同順位を平均ランクで扱うランク関数（round(..., 12) による安定化）
    - factor_summary: count/mean/std/min/max/median を算出
  - すべてのリサーチ機能は DuckDB 接続を受け取り、外部発注/口座 API へはアクセスしない設計。

- モジュール再エクスポート / API
  - kabusys.ai.__all__ に score_news を公開。
  - kabusys.research.__init__ で主要な関数（calc_momentum/calc_value/calc_volatility/zscore_normalize/calc_forward_returns/calc_ic/factor_summary/rank）を再エクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは関数引数で注入可能で、未指定時に環境変数 OPENAI_API_KEY を参照。キー管理は環境変数で行う設計。

Notes / 実装上の重要な設計判断
- ルックアヘッドバイアス防止: date/datetime の取得は target_date を引数として受け取り、datetime.today()/date.today() を直接参照しない方針を採用（AI スコアリング / レジーム判定 / ETL / リサーチ全体で一貫）。
- フェイルセーフ: LLM/API 呼び出しや外部 API エラーは基本的に処理を継続し、局所的に 0 や空結果へフォールバックして上位処理を保護する設計。
- 冪等性: DB 書き込みは可能な限り冪等（DELETE → INSERT、ON CONFLICT 相当）で実装し、部分失敗時に既存データを不必要に消さない。
- DuckDB との互換性配慮: executemany の空リスト制約や LIST バインドの差異を回避するための実装上の注意事項を行っている。
- テスト性: API 呼び出し関数（_call_openai_api 等）や自動 .env ロードの無効化フラグによりユニットテストで差し替え可能な設計。

既知の制約 / TODO（初期リリース時の留意点）
- 一部ファクター（PBR・配当利回り）は未実装（calc_value に注記あり）。
- OpenAI 呼び出しは gpt-4o-mini に固定している（将来的にモデル変更のパラメタ化を検討）。
- jquants_client や quality モジュールの具体的挙動は外部依存。テスト時はモック化を推奨。

作者注
- 各モジュールには詳細な docstring と設計方針が含まれており、運用時の挙動やエラー処理方針を明示しています。API 変更やバグ修正は次バージョンで semver に従って記録します。