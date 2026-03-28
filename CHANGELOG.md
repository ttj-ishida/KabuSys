CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
-------------

（現在のリリースは 0.1.0 です。未リリースの変更はここに記載してください。）

[0.1.0] - 2026-03-28
-------------------

Added
- 初回公開: KabuSys 日本株自動売買 / データ基盤 / 研究ツール群を実装。
  - パッケージ概要
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - top-level __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト等向け）。
  - .env パーサーは次の機能を備える:
    - 空行・コメント行（#）を無視
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォート外で '#' の直前が空白/タブの場合はコメントと見なす）
  - 必須環境変数取得ヘルパー _require を提供（未設定時は ValueError を送出）。
  - Settings クラスを提供し、以下のプロパティを公開:
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path (デフォルト data/kabusys.duckdb), sqlite_path (デフォルト data/monitoring.db)
    - env（development / paper_trading / live の検証）、log_level（DEBUG, INFO, ... の検証）
    - is_live / is_paper / is_dev のショートハンド

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news と news_symbols から記事を集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとのセンチメントを算出して ai_scores テーブルへ保存する機能を実装。
    - 処理の特徴:
      - JST ベースのニュースウィンドウを計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して処理）
      - 1 銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
      - 最大 20 銘柄を 1 チャンクでバッチ処理（_BATCH_SIZE）
      - 429 / 接続断 / タイムアウト / 5xx に対する指数バックオフ再試行
      - レスポンスの厳密バリデーション（JSON 抽出、"results" リスト、code/score の存在・型チェック）
      - スコアの ±1.0 でのクリッピングと有限値チェック
      - 部分失敗に備え、ai_scores への書き込みは対象 code に限定して DELETE → INSERT を実行（冪等・既存データ保護）
      - テスト容易性のため OpenAI 呼び出し関数を差し替え可能に設計（ユニットテストで patch 可能）
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - 主な特徴:
      - prices_daily から ma200_ratio を計算（ルックアヘッドを避けるため target_date 未満のデータのみ使用）
      - raw_news からマクロキーワードによるタイトル抽出（最大 20 件）
      - OpenAI（gpt-4o-mini）へ JSON Mode で投げて macro_sentiment を取得
      - API エラー時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）
      - スコア合成後に market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
      - API キー注入可能（api_key 引数 or OPENAI_API_KEY 環境変数）
      - レート制限や 5xx 等を考慮した再試行ロジックを実装

- データ基盤モジュール (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX マーケットカレンダー（market_calendar）に基づく営業日判定ユーティリティを提供:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - DB にカレンダー登録がない場合は曜日ベースのフォールバック（平日を営業日扱い）を使用する設計。
    - next/prev/get_trading_days は DB 値を優先し、未登録日は曜日フォールバックと一貫性を保つ。
    - calendar_update_job を実装: J-Quants API から差分取得し market_calendar を更新（バックフィル、健全性チェック含む）。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETL のための ETLResult データクラスを公開（取得数、保存数、品質チェック結果、エラー一覧などを格納）。
    - 差分更新・バックフィル・品質チェック・保存（jquants_client の save_* を利用した冪等保存）を想定したユーティリティ群を実装。
    - 内部ユーティリティ:
      - テーブル存在確認、最大日付取得、market_calendar 調整ヘルパー等。
    - エラー・品質問題は収集して呼び出し元に返す設計（Fail-Fast せず上位で判断可能にする）。

- リサーチ / ファクター群 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（prices_daily を参照）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近の財務データを取得し PER / ROE を計算（EPS が 0 または欠損の場合は None）。
    - 設計: DuckDB SQL を直接利用して高速に処理。外部 API へはアクセスしない。
  - feature_exploration モジュール:
    - calc_forward_returns: 将来リターン（指定ホライズン）を一度のクエリで取得可能に実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。データ不足時は None を返す。
    - rank: 同順位は平均ランクを与えるランク化実装（丸め処理で ties の判定を安定化）。
    - factor_summary: 各ファクター列に対する count/mean/std/min/max/median を返す。

- テストおよび運用面の配慮
  - API 呼び出し部分（OpenAI クライアント）やファイル読み込み失敗時に警告を出しつつ処理を継続する設計。
  - DB 書き込みではトランザクションとロールバック処理を備え、ROLLBACK 失敗もログ出力して安全性を高める。
  - 日付の扱いはすべて日付/UTC-naive datetime を使用し、datetime.today() / date.today() を直接参照しない設計（ルックアヘッドバイアス対策）。ただし calendar_update_job では今日の日付を参照して範囲計算を行う。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須としているため、実行環境で設定してください。
  - OpenAI API を利用する機能（score_news, score_regime）は api_key 引数または環境変数 OPENAI_API_KEY を必要とします。
- DuckDB / SQLite のデフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 環境設定の自動読み込みを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を 1 に設定してください（テスト実行時に便利です）。
- OpenAI 関連の呼び出しはユニットテスト時に差し替え可能 (_call_openai_api を patch)。

Acknowledgements
- 本バージョンでは主要な機能（データ ETL、カレンダー管理、研究用ファクター、ニュース NLP、レジーム判定）を実装しました。実際の運用や大規模データに対する負荷試験、より細かなエッジケースの検証は今後のリリースで継続して改善します。