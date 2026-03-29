# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

履歴
----

### [0.1.0] - 2026-03-29
初回公開リリース。

主な追加点
- パッケージ公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージトップに __version__ を定義

- 環境設定 / 起動周り（kabusys.config）
  - .env/.env.local ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）
  - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサ実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - クォート無しの場合のインラインコメント（#）処理（直前が空白/タブのときのみコメントとみなす）
  - OS 環境変数を保護する仕組みを導入（.env の上書きを制御）
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスを設定）
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）
    - LOG_LEVEL のバリデーション（DEBUG / INFO / WARNING / ERROR / CRITICAL）
    - is_live / is_paper / is_dev の便利プロパティ

- AI 関連（kabusys.ai）
  - news_nlp モジュール（score_news）
    - raw_news + news_symbols から銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）のJSONモードでバッチ評価
    - チャンク単位（最大20銘柄）でのAPI送信、トークン肥大化対策（記事数・文字数上限）
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ
    - レスポンスバリデーションとスコア±1.0でのクリップ
    - 結果を ai_scores テーブルへ冪等的に保存（DELETE → INSERT）
    - テスト用に _call_openai_api をモック可能に設計
  - regime_detector モジュール（score_regime）
    - ETF 1321（Nikkei 225 連動型）の200日移動平均乖離率（重み 70%）と、ニュースのLLMセンチメント（重み 30%）を融合して市場レジーム（bull/neutral/bear）を判定・保存
    - prices_daily / raw_news を参照して計算。LLM は gpt-4o-mini を使用
    - API失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - テスト用に _call_openai_api を差し替え可能

- データ処理基盤（kabusys.data）
  - calendar_management モジュール
    - market_calendar を使った営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
    - market_calendar 未登録時は曜日ベースのフォールバック（週末を非営業日扱い）
    - calendar_update_job: J-Quants から差分取得して market_calendar を更新（バックフィル・健全性チェックあり）
    - DuckDB 日付変換ユーティリティ等を実装
  - pipeline モジュール
    - ETLResult データクラス（ETL 実行結果の集約と辞書化ユーティリティ）
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client / quality モジュールと連携）
  - etl モジュールは ETLResult を再エクスポート

- リサーチ（kabusys.research）
  - factor_research モジュール
    - モメンタム、ボラティリティ（ATR, volume, turnover）、バリュー（PER, ROE）の計算関数を実装
    - DuckDB の SQL ウィンドウ関数を活用し、(date, code) ベースの結果を返す
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）
    - IC（Information Coefficient）計算（スピアマンランク相関）
    - rank、factor_summary 等の統計ユーティリティ
  - 一部ユーティリティ（zscore_normalize）を data.stats から再エクスポート

その他の設計／実装上の特徴
- DuckDB を主要なローカル分析 DB として利用（prices_daily / raw_news / ai_scores / market_calendar 等を前提）
- 日付操作は全て date/datetime（タイムゾーン混入を避ける）で統一
- ルックアヘッドバイアスを避けるため、datetime.today()/date.today() を内部ロジックで直接参照しない設計（target_date を引数に取る）
- OpenAI 呼び出しは各モジュール内で独立したプライベート関数実装（モジュール間の結合を避け、テストでの差し替えを容易化）
- API障害は基本的にフェイルセーフ（ログ出力しデフォルト値で継続）で壊れにくい設計

既知の制約 / 注意点
- OpenAI API キー（OPENAI_API_KEY）は必須。score_news / score_regime は明示的な api_key 引数または環境変数が必要。
- DuckDB の executemany は空リストを受け付けないバージョン依存の挙動を考慮している（空リストチェックあり）。
- calendar_update_job 等は外部 J-Quants クライアント（jquants_client）への依存がある（ネットワーク/認証要件）。
- パッケージトップの __all__ に strategy / execution / monitoring が含まれるが、本リリースでの提供実装は上記のモジュール群が中心。
- 日時は UTC naive / date オブジェクトで扱う設計のため、運用時のUTC/JST変換に注意が必要。

セキュリティ関連
- .env 自動読み込み時、既存の OS 環境変数はデフォルトで保護される（.env は上書きしない）。ただし .env.local は override=True（ただし保護されたキーは上書きされない）で読み込まれる。
- 自動読み込みを無効にするフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

破壊的変更
- 初回リリースのため該当なし。

将来の改善案（想定）
- strategy / execution / monitoring モジュールの実装追加（本リリースではインターフェース中心）
- テストカバレッジ強化（特に OpenAI 呼び出しと DB 書き込み周り）
- OpenAI モデルの選択やパラメータの外部化（設定化）
- サードパーティAPI呼び出しの監視・メトリクス追加

--- 

注: 本 CHANGELOG は提供されたコードベースから推測して作成しています。実際のリリースノートはリポジトリのコミット履歴やリリース手順に基づき調整してください。