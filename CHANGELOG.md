CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。  

フォーマットの規約:
- 変更はセクション（Added / Changed / Fixed / Security / etc.）に分類します。
- バージョンはセマンティックバージョニングを想定します。

[Unreleased]
------------

- （次バージョンに向けた変更はここに記載してください）

[0.1.0] - 2026-03-29
-------------------

Added
- 基本パッケージ初期リリースを追加（kabusys v0.1.0）。
  - パッケージエントリポイント: kabusys.__version__ = "0.1.0"。
  - 主要サブパッケージを公開: data, research, ai, monitoring, strategy, execution（__all__ にて指定）。

- 環境設定管理 (kabusys.config)
  - .env/.env.local自動読み込み機能実装:
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探して決定（CWD 非依存）。
    - 読み込み優先度: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
  - .env パーサを実装（export 形式対応、クォート中のエスケープ対応、インラインコメントの扱い等）。
  - 環境変数必須チェック用 _require と Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須プロパティとして定義。
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを提供。
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL のバリデーションを実装。
    - is_live / is_paper / is_dev のヘルパープロパティを追加。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄単位にニューステキストを作成し、OpenAI (gpt-4o-mini) に JSON mode で投げてセンチメント（-1.0〜1.0）を取得。
    - タイムウィンドウは前日 15:00 JST ～ 当日 08:30 JST（UTC 変換済み）を採用。calc_news_window を提供。
    - バッチ処理（1リクエストあたり最大 20 銘柄）・チャンク処理を実装。
    - 再試行ポリシー: 429/接続断/タイムアウト/5xx に対する指数バックオフでのリトライ。
    - レスポンスバリデーションを厳密に実施（JSON 抽出、results 配列検証、code 正規化、数値検査、スコアの ±1.0 クリップ）。
    - DuckDB の executemany に関する互換性考慮（空リストを渡さないガード）。
    - テスト用フック: _call_openai_api を patch して差し替え可能。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロ記事は raw_news からマクロキーワードで抽出（最大 20 件）。
    - OpenAI 呼び出しは独立実装（news_nlp と共有しない）で、API 失敗時は macro_sentiment=0.0 でフェイルセーフ。
    - レトライ・エラー処理（RateLimit, Connection, Timeout, APIError の 5xx 判定）を実装。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - テスト用フック: _call_openai_api を patch 可能。

- Data モジュール (kabusys.data)
  - ETL パイプライン (kabusys.data.pipeline)
    - 差分取得→保存→品質チェックのワークフローを実装。
    - ETL 実行結果を表すデータクラス ETLResult を追加（kabusys.data.etl から再エクスポート）。
    - 市場カレンダ、株価、財務データの取得範囲計算、バックフィルポリシーを実装。
    - DuckDB のテーブル存在チェック、最大日付取得等のユーティリティを実装。

  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を基に営業日判定ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB にデータがない場合は曜日（土日）ベースのフォールバック実装。
    - calendar_update_job を実装し J-Quants API から差分取得して保存（バックフィル / 健全性チェックあり）。
    - 市場カレンダー未整備時でも一貫した next/prev/get の振る舞いを保証する設計。

- Research モジュール (kabusys.research)
  - factor_research
    - モメンタム: 約 1M/3M/6M リターン、200 日 MA 乖離を計算する calc_momentum を追加（データ不足時は None）。
    - ボラティリティ / 流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算する calc_volatility を追加。
    - バリュー: raw_financials を用いた PER / ROE 計算 calc_value を追加（最新財務レコードの取得は ROW_NUMBER）。
    - 全関数は prices_daily / raw_financials のみ参照し、本番口座・発注 API にアクセスしない設計。
  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン、最大 252 営業日までのバリデーション）。
    - IC（Spearman の ρ）計算 calc_ic（ランク化、ties 平均ランク対応）。
    - ランク変換ユーティリティ rank（丸めで ties 検出安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を標準ライブラリのみで計算。

Changed
- なし（初回リリース）

Fixed
- DuckDB 実行時の互換性に関する配慮を多数追加:
  - executemany に空リストを渡すと失敗するバージョン対策（空チェックを追加）。
  - market_calendar / information_schema クエリでのスキーマ差異を考慮。

Security
- なし（公開されている設定だが、API キー等は環境変数での注入を想定。OpenAI API キーは明示的に渡すか OPENAI_API_KEY に設定する必要あり。）

Notes / Breaking changes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings からアクセスする際に未設定だと ValueError を送出します。デプロイ前に .env を用意してください（.env.example を参照）。
- KABUSYS_ENV と LOG_LEVEL:
  - KABUSYS_ENV は "development", "paper_trading", "live" のいずれかでなければ ValueError。
  - LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれかでなければ ValueError。
- OpenAI API:
  - news_nlp.score_news / regime_detector.score_regime は API キーが引数で与えられない場合 OPENAI_API_KEY 環境変数を参照します。未設定時は ValueError を送出します。
  - API が失敗した場合、多くの処理でフェイルセーフ（0.0 を返す、あるいは処理をスキップして続行）する設計です。これは本番運用での堅牢性を高めるための意図的な振る舞いです。
- 必要な DB スキーマ（想定テーブル）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など。ETL / AI / Research の各機能はこれらのテーブルを前提とします。

テスト & 開発者向け
- 自動 .env ロードはデフォルトで有効。ユニットテスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分は各モジュール内の _call_openai_api を unittest.mock.patch して差し替え可能（外部 API 呼び出しをモック化してテスト可能）。

参考
- 実装は「ルックアヘッドバイアスを排除する」設計指針に従っています（datetime.today()/date.today() を利用せず、全ての計算は関数引数 target_date に依存します）。
- DuckDB を想定した SQL を多用しており、運用時は DuckDB のバージョン差異に注意してください。

---
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートや変更履歴と異なる場合があります。）