Keep a Changelog
=================
すべての重要な変更をこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

[Unreleased]
------------

[0.1.0] - 2026-03-29
--------------------
初回リリース。日本株自動売買システム「KabuSys」のコアライブラリを追加しました。主な追加点・設計方針は以下のとおりです。

Added
- パッケージ構成
  - kabusys パッケージの公開（__version__ = 0.1.0）。主要サブパッケージを __all__ で公開: data, research, ai, monitoring, strategy, execution 等を想定。
- 環境設定周り（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロード優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パーサを実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなしでのインラインコメント認識（直前がスペース/タブの場合）
    - 無効行（空行・コメント・= がない行）は無視
  - .env 読み込み時の上書き制御（override と protected set の概念）を実装。
  - Settings クラスを提供し、アプリ設定をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須（未設定時 ValueError を送出）
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH にデフォルトを設定
    - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値検査）
    - is_live / is_paper / is_dev の簡易判定プロパティ

- AI モジュール（kabusys.ai）
  - news_nlp (score_news)
    - raw_news と news_symbols を使って銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）に JSON モードでバッチ送信してセンチメントを取得。
    - バッチ処理、銘柄あたりの最大記事数および文字トリム実装（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - リトライ/バックオフ戦略（429/ネットワーク断/タイムアウト/5xx を対象、指数バックオフ）。
    - レスポンス検証とスコアクリッピング（±1.0）。
    - DuckDB への書き込みは部分的な置換（DELETE → INSERT）で冪等性を確保し、DuckDB 互換性のため executemany の空リストガードを実装。
    - calc_news_window を公開し、JST で前日 15:00 〜 当日 08:30 のウィンドウ（内部は UTC naive datetime）を算出。
    - OpenAI 呼び出し部分は _call_openai_api を経由しておりテスト時にモック可能。
  - regime_detector (score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来の LLM マクロセンチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定。
    - MA 計算は target_date 未満のデータのみ使用（ルックアヘッド回避）。
    - マクロ記事がない場合は LLM 呼び出しを行わず macro_sentiment=0.0 とするフェイルセーフ。
    - OpenAI 呼び出しにはリトライ・バックオフを実装。API 失敗時には 0.0 にフォールバックして継続。
    - 結果は market_regime テーブルへトランザクションで冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。失敗時は ROLLBACK を試行。
    - OpenAI クライアントは引数 api_key または環境変数 OPENAI_API_KEY を使用。未設定なら ValueError を送出。

- Research モジュール（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を用いて計算。
    - データ不足時は None を返す設計。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）に対応。複数ホライズンを一度のクエリで取得してパフォーマンスを配慮。
    - IC（calc_ic）: スピアマンランク相関を実装（同順位は平均ランク処理）。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を実装。
  - zscore_normalize を data.stats から再エクスポート（研究ユーティリティ連携）。

- Data モジュール（kabusys.data）
  - calendar_management
    - market_calendar テーブルを使った営業日判定ロジックを実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供
      - DB にデータがあれば DB 値を優先。未登録日は曜日ベースでフォールバック（週末は非営業日）。
      - 最大探索日数の上限（_MAX_SEARCH_DAYS）を設定して無限ループを防止。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル・健全性チェック含む）。
  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。ETL の実行結果（取得数・保存数・品質問題・エラー等）を集約。
    - ETL 内部ユーティリティ: テーブル存在確認、最大日付取得、トレーディング日調整などを実装。
    - 設計上の配慮: 差分更新・バックフィル・品質チェックは Fail-Fast にしない（呼び出し元で判断可能に）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キー・各種トークン等の取り扱いは環境変数経由を想定。自動 .env ロードはデフォルトで有効だが、明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID はいくつかの機能で必須（Settings のプロパティで参照）。
  - OPENAI_API_KEY は AI 機能（score_news, score_regime）を使う際に必須（api_key 引数で上書き可能）。
- デフォルト DB パス:
  - DUCKDB_PATH デフォルト: data/kabusys.duckdb
  - SQLITE_PATH デフォルト: data/monitoring.db
- DuckDB 互換性:
  - DuckDB のバージョン差異（executemany の空リスト等）を考慮した実装を行っています。
- テスト容易性:
  - OpenAI 呼び出し部は内部関数（_call_openai_api 等）を経由しており、unittest.mock.patch で差し替え可能。
- 設計方針の明記:
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を計算の根拠に使用しない関数設計を徹底。

既知の制限 / TODO（今後の作業候補）
- PBR・配当利回りなどのバリューファクターは未実装（calc_value に注記あり）。
- モデル名やプロンプトは現行実装（gpt-4o-mini, JSON mode）に固定しているため将来的なモデル移行方針を検討する余地あり。
- news_nlp における LLM レスポンスの厳密検証やフォールバックロジックはあるが、より詳細な監査ログやメトリクスの追加を検討。
- calendar_update_job と J-Quants client の連携部分は外部 API の仕様変更に依存するため、リトライ/エラーハンドリングの拡充を検討。

--- 

この CHANGELOG はコードベースの現状から実装意図と主要な機能を推測して作成しています。開発履歴やリリースノートとして正式に利用する場合は、実際のコミット履歴・リリース日・変更差分を併せて反映してください。