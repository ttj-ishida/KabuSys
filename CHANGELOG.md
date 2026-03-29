CHANGELOG
=========

すべての重要な変更点は Keep a Changelog の形式に準拠して記載しています。  
リリース日や内容はコードベースから推測して記載しています。

フォーマットの参照: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

v0.1.0 - 2026-03-29
-------------------

Added
- 初回公開（v0.1.0）。
  以下の主要機能・モジュールを実装・公開しました。

- パッケージ初期化
  - パッケージのエントリポイント (src/kabusys/__init__.py) を追加。
  - __version__ = "0.1.0" を設定し、公開モジュールとして data, strategy, execution, monitoring を列挙。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装（ルート検出は .git / pyproject.toml を基準）。
  - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - auto-load を無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - プロテクトされた OS 環境変数を上書きしない読み込みロジック。
  - 必須設定取得用 _require と Settings クラスを提供。以下のプロパティを含む:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルトあり)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（Path として返す）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール (src/kabusys/ai)
  - ニュースセンチメント分析 (news_nlp.py)
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約して OpenAI にバッチ問い合わせを行い、ai_scores テーブルへ書き込む。
    - ニュース時間ウィンドウの計算（JST 前日15:00〜当日08:30 を UTC に変換）。
    - バッチ処理（最大 20 銘柄 / 回）、記事トリム（最大記事数・最大文字数）によるトークン肥大化対策。
    - OpenAI 呼び出しは JSON モードを利用、レスポンスの堅牢なバリデーションと ±1.0 のクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ付きリトライを実装。失敗時は安全にスキップして継続（例外を投げない設計）。
    - DuckDB への書き込みは部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT の冪等処理を実行。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - 市場レジーム判定 (regime_detector.py)
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して daily market_regime を計算・登録する。
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用、データ不足時は中立扱い）。
    - マクロニュース抽出（マクロキーワードに基づくフィルタ、件数上限）。
    - OpenAI（gpt-4o-mini）を用いた JSON レスポンス解析と堅牢なエラー処理（リトライ、フォールバック macro_sentiment=0.0）。
    - 計算結果は BEGIN / DELETE / INSERT / COMMIT の冪等書き込みで保存。
    - LLM 呼び出し実装は news_nlp と独立しており、モジュール間結合を避ける設計。

- データプラットフォーム / ETL / カレンダー (src/kabusys/data)
  - calendar_management.py
    - JPX マーケットカレンダー管理。market_calendar テーブルを参照して営業日の判定・探索を行うユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダーがない場合は曜日ベース（土日非営業）でフォールバックする一貫した挙動。
    - calendar_update_job(conn, lookahead_days=90): J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックあり。
    - 最大探索日数やバックフィル日数などの安全制約を実装。
    - jquants_client を介したフェッチ／保存処理と連携。
  - pipeline.py / ETLResult (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを導入し、ETL の取得数・保存数・品質問題・エラーを集約して返却。
    - 差分更新のための内部ユーティリティ（テーブル存在確認、最大日付取得など）を提供。
    - デフォルトのバックフィルやカレンダー先読み、品質チェックの設計方針が実装済み（品質チェックは別モジュール quality と連携する想定）。
    - data.etl モジュールは ETLResult を再エクスポート。

- Research / ファクター計算 (src/kabusys/research)
  - factor_research.py
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日 MA 乖離を計算。
    - calc_volatility(conn, target_date): 20日 ATR、ATR/株価、20日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials から直近財務情報を取得し PER、ROE を計算（EPS 0・欠損時は None）。
    - いずれも DuckDB SQL を主体に実装し、データ不足時の None 処理やログ出力を含む。
  - feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を実装。必要最小レコード未満なら None を返す。
    - rank(values): 平均ランク（同順位の平均ランク）を返すユーティリティ（浮動小数の丸めで ties を安定化）。
    - factor_summary(records, columns): 各ファクター列の count/mean/std/min/max/median を計算する統計サマリ機能。
  - research パッケージはデータ系ユーティリティ（zscore_normalize）を他モジュールからインポートして公開。

Notes / 設計上の重要ポイント
- DuckDB を主要な相互作用先として想定しており、SQL + Python の組み合わせで計算を実行しています。
- OpenAI API 呼び出しは OpenAI SDK の OpenAI クライアントを利用する前提（gpt-4o-mini を指定）。テスト時に差し替え可能な設計（モック容易）。
- LLM 利用部分は以下の安全策を採用:
  - ルックアヘッドバイアス回避のため datetime.today()/date.today() を内部参照しない設計（全て target_date を明示）。
  - API エラー時はフェイルセーフ（デフォルトスコアやスキップ）で継続する方針。
  - レスポンスは JSON モードで受け取り、パース失敗時の復元ロジックや検証を厳格に実施。
  - スコアは仕様に従いクリップ（±1.0 等）。
- DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT を想定）し、トランザクション/ROLLBACK 保護を行います。
- 環境変数や API キーが未設定の場合は明示的な ValueError を送出する箇所があるため、運用時の設定ミスが早期に分かる設計。
- .env パーサは多くの shell 形式をサポートするが、特殊なケースは注意（実運用での検証を推奨）。

Breaking Changes
- v0.1.0 は初回リリースのため既存互換に関する破壊的変更はありません。

Security
- API キーやシークレットは環境変数から取得する設計。.env の自動読み込みは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

開発・運用上の補足（推奨）
- OpenAI キーを環境変数 OPENAI_API_KEY または各関数の api_key 引数で提供する必要があります。
- DuckDB に必要なテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を事前に用意してください。
- テスト時は _call_openai_api を patch して外部 API 呼び出しをモックすることを推奨します。
- カレンダー・ETL 周りは jquants_client と quality モジュールの実装に依存するため、連携実装に注意してください。

Contributors
- コードベースからの推測で初期実装者情報は未記載。

--- 
（上記は公開されているコードの内容・ドキュメント文字列・設計注釈から推測した CHANGELOG です。実際のリリースノートや日付はプロジェクト運営方針に従い適宜修正してください。）