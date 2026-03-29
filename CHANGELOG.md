CHANGELOG
=========

すべての重要な変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の形式に従って記載しています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-29
------------------

初回リリース。日本株自動売買システム "KabuSys" の基盤機能を実装しました。
主な追加点、設計方針、既知の挙動を以下にまとめます。

Added
- パッケージ基盤
  - kabusys パッケージ初期化を実装（__version__ = "0.1.0"）。
  - public API として data, strategy, execution, monitoring モジュールを公開。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能（プロジェクトルートの .git または pyproject.toml を探索して .env/.env.local を読み込み）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルールに対応。
  - 環境変数の必須チェック（_require）とデフォルト値（KABUS_API_BASE_URL、データベースパス等）を提供。
  - 設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等）を実装。KABUSYS_ENV と LOG_LEVEL のバリデーションあり。
  - OS 環境変数を保護する protected バインディング機能実装（.env.local は上書き可能だが OS の既存キーは保護）。

- AI（kabusys.ai）
  - news_nlp.score_news: raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）の JSON Mode を用い銘柄別センチメントを評価し、ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄/コール）、記事数と文字数のトリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ実装。
    - レスポンス検証ロジック（JSON 抽出、"results" フォーマット検証、コード照合、数値チェック、スコア ±1.0 クリップ）。
    - DB への置換は部分更新（対象コードのみ DELETE → INSERT）とし、部分失敗時に既存データを破壊しない設計。
    - ルックアヘッドバイアス対策として datetime.today()/date.today() を参照せず、target_date ベースでウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を行う。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（unittest.mock.patch を想定）。

  - regime_detector.score_regime: ETF (1321) の 200 日移動平均乖離とニュース由来のマクロセンチメントを重み合成して市場レジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等書き込み。
    - ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッド回避）。データ不足時は中立（1.0）を採用。
    - マクロ記事抽出は定義済みキーワードでフィルタし、最大 N 件を LLM に送信。API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - OpenAI 呼び出しは専用実装でモジュール結合を抑制。レスポンスパース・リトライ処理を実装。

- Research（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算関数を実装。
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日 MA 乖離）を返す。データ不足時は None。
    - calc_volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを結合して PER, ROE を算出（EPS が 0/欠損 の場合は None）。
    - すべて DuckDB 内 SQL とウィンドウ関数で実装し、外部 API には依存しない。
  - feature_exploration: 将来リターン・IC（Information Coefficient）・統計サマリー用関数を提供。
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons に対する入力検証あり。
    - calc_ic: スピアマンのランク相関（ランク付けは同順位の平均ランク）で IC を返す。十分なデータがなければ None。
    - factor_summary: count/mean/std/min/max/median を計算。
    - rank: 値のランク化で丸め処理（round(..., 12)）を用い浮動小数点の ties 判定を安定化。

- Data（kabusys.data）
  - calendar_management: JPX マーケットカレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job を提供。
    - DB にカレンダーがない/未登録の日は曜日ベースのフォールバック（週末を非営業日）を使用。
    - calendar_update_job は J-Quants クライアント（jquants_client.fetch_market_calendar/save_market_calendar）を呼び出して冪等更新を行う。バックフィルと健全性チェックを実装。
  - pipeline / etl: ETL フレームワークと ETLResult を実装。
    - ETLResult: ETL の集計結果を表す dataclass（品質問題のリスト、エラー一覧、保存件数等）。
    - data.etl は pipeline.ETLResult を再エクスポート。
    - pipeline モジュールは差分取得、バックフィル、品質チェック（quality モジュール連携）を想定した設計。重大度のある品質問題は収集するが自動的に処理を中断しない方針。

Changed
- （初回リリースのため該当なし）

Fixed
- .env パーサの挙動に関して、export プレフィックス、クォート内部のバックスラッシュエスケープ、インラインコメントの取り扱い等を丁寧に実装。OS 環境変数が .env で意図せず上書きされないよう protected 機構を導入。

Security
- 環境変数や API キーの取り扱いに注意するよう設計（OpenAI API キーは引数注入または OPENAI_API_KEY 環境変数で提供。必須チェックあり）。

Notes / Design decisions / Known limitations
- ルックアヘッドバイアス防止:
  - AI モジュール・リサーチモジュールは内部で datetime.today()/date.today() を参照せず、呼び出し側が渡す target_date に対して過去データのみを参照する設計になっています。バックテスト用途での安全性を重視しています。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定し JSON Mode を利用する実装。API レスポンスの不整合や一時エラー時はフェイルセーフ（0.0 やスキップ）で処理を継続します。
  - テスト時には _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
- DB 書き込み:
  - ai_scores / market_regime 等への書き込みは部分更新・トランザクション（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK を試みて上位へ例外を伝播します。部分失敗時に既存データを保護する実装です。
- DuckDB 互換性:
  - executemany に空リストを渡すとエラーとなるバージョンを考慮して、空チェックを行っています。
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で必須扱い。OpenAI API は score_news/score_regime 呼び出し時に引数で注入するか OPENAI_API_KEY を環境変数に設定してください。

開発上のメモ（将来の改善候補）
- news_nlp と regime_detector の OpenAI 呼び出しロジックは意図的に同一モジュールで共有していません。将来的に共通ユーティリティ化することで重複削減が可能です。
- J-Quants クライアント（jquants_client）の詳細実装は外部依存として分離されています。API レートや認証更新ロジックの実装が必要です。
- strategy / execution / monitoring モジュールの具体的な実装は今後追加される想定です（パッケージ API としては既に公開済み）。

作者
- KabuSys チーム

以上。