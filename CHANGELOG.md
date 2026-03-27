CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。以下は、提示されたコードベースの内容から推測してまとめた変更履歴（初期リリース相当）です。実際のコミット履歴ではなく、コードの機能説明をもとにした要約であることにご留意ください。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-27
------------------

Added
- パッケージ初期公開
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"。パッケージの公開・バージョニングを導入。
  - パッケージ公開 API: __all__ で data, strategy, execution, monitoring を公開。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local の自動ロード機能を実装。プロジェクトルート（.git または pyproject.toml を探索）を基準に .env を読み込む。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ実装: export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどをサポート。
  - Settings クラスを提供し、アプリケーションで必要な環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得（未設定時は ValueError を送出）。
    - KABU_API_BASE_URL / DUCKDB_PATH / SQLITE_PATH 等はデフォルト値を持つ。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値のチェック）、is_live / is_paper / is_dev のユーティリティプロパティ。

- データ基盤周り (kabusys.data)
  - calendar_management:
    - 市場カレンダー管理: market_calendar テーブルの有無に応じた営業日判定ロジックを提供（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB 登録あり時は DB の値優先、未登録日は曜日ベースでフォールバックする設計。
    - カレンダー夜間更新ジョブ calendar_update_job を実装。J-Quants クライアント（jquants_client）経由で差分取得し冪等保存。バックフィル・健全性チェックを内蔵。
  - ETL / pipeline:
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を re-export）。
    - ETL パイプライン用ユーティリティ（最終取得日の判定、テーブル存在確認など）を実装。差分取得／バックフィル／品質チェックの設計方針を反映。
  - その他:
    - DuckDB を主データストアとして想定。多くの処理が DuckDB 接続を受け取る仕様。

- 自然言語処理 / AI (kabusys.ai)
  - news_nlp:
    - score_news 関数を実装。raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとにセンチメント（-1.0〜1.0）を算出。
    - ニュース取得ウィンドウ（JST 前日 15:00 ～ 当日 08:30 に対応する UTC 範囲）計算ユーティリティ calc_news_window を実装。
    - バッチ処理（1回につき最大 20 銘柄）、1銘柄あたりの記事数上限・文字数トリム、レスポンスのバリデーション（JSON 抽出、results 配列の検証、コード照合、数値チェック）、スコアの ±1.0 クリップを実装。
    - API 呼び出しのリトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで処理。失敗はロギングしてスキップ（フェイルセーフ）。
    - スコア取得後は ai_scores テーブルに対して部分的に置換（該当コードのみ DELETE → INSERT）し、部分失敗時に既存データを保護。
    - テスト容易性のため _call_openai_api の差し替えを想定（unittest.mock.patch でモック可能）。
  - regime_detector:
    - score_regime 関数を実装。ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - ma200_ratio の計算（target_date より前のみ参照、データ不足時は中立 1.0 を返す）と、raw_news からマクロキーワードでフィルタしたタイトル取得を実装。
    - OpenAI 呼び出しでのリトライとエラー処理、API 失敗時は macro_sentiment=0.0 のフェイルセーフを採用。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）する実装。

- リサーチ（因子・特徴量探索） (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range の NULL 伝播制御など堅牢な実装。
    - calc_value: raw_financials から最新財務データ（EPS, ROE）を取得し PER / ROE を算出（EPS が 0/欠損の際は None）。
    - DuckDB 上の SQL ウィンドウ関数を多用した実装で、外部 API にはアクセスしない（安全性）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一括取得。ホライズン検証を実施。
    - calc_ic: スピアマン（ランク相関）による IC 計算を実装。結合や None/有限値のフィルタを行い、有効レコードが不足する場合は None を返す。
    - rank / factor_summary: ランク化ユーティリティ（同順位は平均ランク）と、count/mean/std/min/max/median の統計サマリーを提供。
  - 研究 API を外部で利用しやすいように一括エクスポート（kabusys.research.__all__）を整備。

- 設計品質と運用上の配慮（横断的事項）
  - ルックアヘッドバイアス対策: 各所で datetime.today() / date.today() を直接参照する処理を避け、target_date を明示的に受け取る設計を徹底。
  - DB 書き込みは冪等性を重視（既存行を削除して挿入、あるいは ON CONFLICT を想定）。
  - OpenAI 呼び出しは明示的なリトライ方針（429/5xx/ネットワーク/タイムアウトに対する指数バックオフ）を持ち、API エラー時のフォールバックが実装されている。
  - テストしやすい設計: API キー注入可能（api_key 引数）、内部 API 呼び出し関数の差し替えを想定した構成。
  - ロギングを各処理に配置し、異常時の情報を出力する実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

注記（補足）
- 本 CHANGELOG は提示されたソースコードから機能・振る舞いを推測して作成しています。実際の変更履歴（コミット単位）や追加のモジュール（strategy, execution, monitoring 等）の実装詳細は、リポジトリのコミットログや設計ドキュメントを参照してください。