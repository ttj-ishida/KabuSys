# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-28

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージ公開情報:
    - __version__ = "0.1.0"
    - パブリックモジュール: data, research, ai, config, etc.

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml をルート判定基準）から自動読み込みする仕組みを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
  - .env パーサ実装: export プレフィックス対応、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応。
  - Settings クラスを提供し、環境変数をプロパティ経由で型安全に参照:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須値を _require() で検査。
    - KABUSYS_ENV（development / paper_trading / live）のバリデーション。
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）のバリデーション。
    - DuckDB / SQLite のデフォルトパス設定（expanduser 対応）。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols テーブルを集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）へ JSON Mode でバッチ送信してセンチメント（-1.0〜1.0）を取得。
    - 時間ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime で扱う calc_news_window を提供）。
    - バッチサイズ、記事数・文字数制限、チャンク処理（最大 _BATCH_SIZE=20）を実装。
    - 再試行ロジック: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。その他のエラーはスキップ（フェイルセーフ）。
    - レスポンス検証: JSON パース復元（前後余分テキストの抽出）・results 検証・コード照合・数値検証・スコアのクリップ。
    - 書き込みは部分置換戦略（対象コードのみ DELETE → INSERT）で、部分失敗時に他コードの既存スコアを保護。
    - テスト容易性: _call_openai_api をモック差し替え可能。
    - Public API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
    - マクロニュースはマクロキーワードでフィルタ（定義済みキーワード群）。
    - OpenAI 呼び出しを独自実装し、retry / エラー時のフェイルセーフ（macro_sentiment=0.0）。
    - レジーム算出後は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。失敗時はROLLBACKを試行して例外を伝播。
    - Public API: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。

- データ基盤モジュール (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー管理ロジック: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベース（平日）でフォールバックする一貫した振る舞い。
    - 夜間バッチジョブ calendar_update_job(conn, lookahead_days=90) を実装し、J-Quants API から差分取得 → 保存（jq.save_market_calendar）を行う（バックフィル、健全性チェック含む）。
    - 最大探索範囲やバックフィル日数、異常時の安全措置を実装。

  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETL の結果を格納する ETLResult データクラスを実装（kabusys.data.etl は ETLResult を再エクスポート）。
    - 差分取得ロジック、backfill、品質チェック（quality モジュール）を想定した設計。
    - DuckDB 上でのテーブル有無 / 最大日付取得等のユーティリティを提供。

  - jquants_client など外部クライアントとの連携を想定（モジュールをインポートして使用）。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - ボラティリティ (calc_volatility): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比などを計算。
    - バリュー (calc_value): raw_financials から EPS/ROE を取り、PER/ROE を算出（EPS 0 や欠損は None）。
    - 全て DuckDB の prices_daily / raw_financials のみ参照し外部 API に依存しない設計。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Information Coefficient）calc_ic（ランク相関 / スピアマン ρ）および rank ユーティリティ。
    - 統計サマリー factor_summary（count/mean/std/min/max/median を計算）。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- 実装上の設計方針（全体）
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照しない実装（関数に target_date を渡す設計）。
  - OpenAI 呼び出しは JSON Mode を利用し、厳格なレスポンス検証を行う。
  - エラー耐性: API エラー時は例外を投げずにフェイルセーフ動作（中立スコアやスキップ）にフォールバックする箇所を多く実装。
  - トランザクション制御: DuckDB への書き込みは BEGIN/DELETE/INSERT/COMMIT のパターンで冪等性を確保し、失敗時に ROLLBACK を試行。
  - テスト容易性: 外部 API 呼び出しポイント（_call_openai_api など）をモック差し替え可能にしている。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Notes
- OpenAI API の呼び出しに関する設定や API キーは関数引数から注入可能（api_key 引数）で、環境変数 OPENAI_API_KEY も参照します。テスト時は明示的に差し替えてください。
- DuckDB に対する executemany の空リストバインドに関する互換性考慮（DuckDB 0.10 での注意点）を実装で吸収しています。
- .env の自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後に環境での動作を変える際は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

開発者向け公開 API（代表）
- kabusys.settings: 各種環境設定を参照する Settings インスタンス
- kabusys.ai.score_news(conn, target_date, api_key=None)
- kabusys.ai.score_regime(conn, target_date, api_key=None)
- kabusys.research.calc_momentum / calc_volatility / calc_value
- kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- kabusys.data.etl.ETLResult

----- 
今後のリリースでは、ユニットテストカバレッジ、ドキュメント（API 仕様／運用手順）、および運用モニタリング・例外ハンドリングの更なる強化を予定しています。