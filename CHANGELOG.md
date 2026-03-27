# CHANGELOG

すべての変更は Keep a Changelog 準拠のフォーマットで記載しています。  
このファイルは、与えられたコードベースの内容から推測して作成した初回リリース向けの変更履歴です。

全般的な注記
- 本パッケージは DuckDB をデータ格納・クエリ基盤として利用し、J-Quants / kabu ステーション / OpenAI（gpt-4o-mini）等の外部サービスと連携する設計です。
- 設計方針として「ルックアヘッドバイアスを防ぐため datetime.today()/date.today() を参照しない」「DB 書き込みは冪等に行う（DELETE→INSERT 等）」「外部 API 呼び出しはリトライ/フォールバックを実装してフェイルセーフ化する」といった点が一貫して採用されています。

Unreleased
- （なし）

## [0.1.0] - 2026-03-27
### Added
- パッケージ基本情報
  - kabusys パッケージの初期リリース（__version__ = "0.1.0"）。
  - パッケージの公開サブモジュールとして data, research, ai, execution, monitoring, strategy, etc を想定した __all__ を用意。

- 設定/環境変数管理 (kabusys.config)
  - .env および環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索して特定（CWD に依存しない）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
    - .env と .env.local の読み込み優先順を実装（OS 環境変数は保護し .env.local が .env を上書き）。
  - .env 行パーサを実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
  - Settings クラスを提供し、主要設定に対するプロパティを公開：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）の Path 解決
    - KABUSYS_ENV（development / paper_trading / live）の検証
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証
    - is_live / is_paper / is_dev の補助プロパティ
  - 必須環境変数未設定時に分かりやすい ValueError を送出する _require 関数を実装。

- ニュースNLP（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None) を実装。
    - 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換済）の記事を対象に集計。
    - news_symbols と結合して銘柄ごとに最新記事をまとめ、1銘柄あたりの記事数・文字数でトリム。
    - OpenAI（gpt-4o-mini）へ銘柄バッチ（最大 20 銘柄）で送信し JSON Mode でレスポンスを受け取る。
    - 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
    - レスポンスを厳密にバリデート（results 配列、code と score、既知コードのみ採用、score を ±1.0 にクリップ）。
    - 成功した銘柄のみ ai_scores テーブルへ置換（DELETE → INSERT）し、部分失敗時に既存データを保護。
    - API キーを引数で注入可能。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を送出。
    - エラー耐性：API 呼び出し失敗時はスキップして処理を継続（例外で全体を停止しない）。

  - calc_news_window(target_date) を提供（ウィンドウの UTC naive datetime を返す）。

  - 内部ユーティリティ：
    - _fetch_articles, _score_chunk, _validate_and_extract など。テスト容易性のため _call_openai_api 呼び出しを差し替え可能に設計。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None) を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算は target_date 未満のデータのみ使用しルックアヘッドを防止。
    - マクロニュースは news_nlp.calc_news_window を用いて取得、該当タイトルが無ければ LLM 呼び出しを省略して macro_sentiment=0.0。
    - OpenAI 呼び出しは retry や 5xx 判定を含む堅牢な実装。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - 判定結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API キーは引数で注入可能。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError。

- Research（kabusys.research）
  - factor_research モジュールを追加:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、ma200_dev（200日 MA 乖離）等を SQL ウィンドウ関数で計算。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などを計算。
    - calc_value(conn, target_date): raw_financials から最新の財務データを取得して PER/ROE を計算。
    - いずれも DuckDB の prices_daily/raw_financials を参照し、データ不足時は None を返す設計。
  - feature_exploration モジュールを追加:
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト [1,5,21]）を LEAD を用いて計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を実装（同順位は平均ランク）。
    - rank(values): 丸め（round(..., 12)）で ties の扱いを安定化。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリ。

- データ基盤・ETL（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）用ユーティリティを実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等を提供。
      - calendar データがない場合は曜日（土日）ベースでフォールバック。
      - calendar_update_job(conn, lookahead_days): J-Quants API から差分取得して market_calendar を冪等更新。バックフィル、健全性チェック（将来日付の異常検出）を実装。
  - pipeline: ETL パイプラインの骨格を実装。
    - ETLResult dataclass を提供（取得件数・保存件数・品質問題・エラー概要を格納）。
    - 差分取得、backfill、J-Quants クライアント経由の保存（idempotent）と品質チェックのワークフロー設計を反映。
    - 内部ユーティリティとしてテーブル存在確認、最大日付取得などを実装。
  - etl.py で ETLResult を再エクスポート。

- 設計上の共通改善点 / 実装方針（ドキュメント的な追加）
  - ルックアヘッドバイアス防止のため日付参照方法を統一。
  - 外部 API のエラーに対するフォールバックルール（LLM の場合 macro_sentiment=0.0、ニューススコアリングは失敗チャンクをスキップ）を明示。
  - DB 書き込みは部分失敗時に既存データを守る（対象コードのみ DELETE して INSERT）。
  - テスト容易性のため OpenAI 呼び出しポイントを差し替え可能に設計（unittest.mock.patch を想定）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 環境変数管理により API キー等は環境変数経由で扱うよう実装。自動 .env 読み込みは無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意。

Notes / 既知の想定挙動
- score_regime は成功時に int 1 を返す仕様（例外は DB 書き込み失敗等で伝播）。
- score_news は書き込んだ銘柄数を返す。スコア取得が一切できない場合は 0 を返す。
- 一部モジュール（execution, monitoring, strategy 等）は __all__ に含まれているが、該当ファイルはこのスナップショットに含まれていません（今後追加予定）。
- 実環境での運用にあたっては、必要な環境変数（OpenAI / J-Quants / kabu / Slack 等）の設定が必須です。

もし望まれるなら、各モジュール毎の API 仕様（関数引数・返り値・例外）をより詳細にまとめたリファレンス風の CHANGELOG セクションを追記できます。どの程度の粒度で記載するか指示してください。