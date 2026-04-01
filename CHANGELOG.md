CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。
フォーマットは Keep a Changelog に準拠しています。

[Unreleased]
-------------

なし

[0.1.0] - 2026-04-01
--------------------

Added
- 初回公開: KabuSys 日本株自動売買システムの基礎モジュール群を追加。
  - パッケージ基底:
    - src/kabusys/__init__.py に __version__="0.1.0"、主要サブパッケージの __all__ を公開。
  - 設定管理:
    - src/kabusys/config.py
      - .env ファイルおよび環境変数からの設定読み込み機能を追加。
      - プロジェクトルート検出: .git または pyproject.toml を基準に自動でプロジェクトルートを探索し .env/.env.local を読み込む（CWD に依存しない実装）。
      - .env パースを強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの取り扱いなどを実装。
      - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを抑止可能。
      - OS 環境変数保護: 初期 OS 環境変数を protected として .env.local の上書きを制御。
      - Settings クラスを公開（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などのプロパティと、env/log_level 判定、パスや閾値のデフォルト値を提供）。
  - AI モジュール:
    - src/kabusys/ai/news_nlp.py
      - ニュース記事を銘柄ごとに集約し、OpenAI (gpt-4o-mini) の JSON Mode を用いて銘柄別センチメント（ai_score）を算出し ai_scores テーブルへ書き込む機能を追加。
      - タイムウィンドウ計算（JST ベース -> UTC 変換）、記事数/文字数トリム、バッチ処理（最大 20 銘柄/リクエスト）を実装。
      - レート制限やネットワーク断、サーバーエラー（5xx）に対する指数バックオフによるリトライ、レスポンスの厳密なバリデーション（JSON 抽出・results キー・コード照合・数値検証）を実装。
      - API キー注入可能（api_key 引数）およびテスト容易性のための _call_openai_api パッチポイント。
      - フェイルセーフ設計: API 失敗時はスキップして処理継続。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321（225 連動型）200 日移動平均乖離 (MA) とマクロニュースの LLM センチメントを重み合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等的に書き込む機能を追加。
      - MA 計算、マクロキーワード抽出、LLM（gpt-4o-mini）呼び出しとリトライ、スコア合成、トランザクションを伴う INSERT/DELETE による冪等書き込みを実装。
      - API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを備える。
  - Research / Analytics:
    - src/kabusys/research/*
      - factor_research.py: Momentum / Volatility / Value 等の定量ファクター計算関数を追加（mom 1/3/6M、ma200 乖離、ATR20、平均売買代金、PER/ROE など）。DuckDB SQL を用いた実装で、結果は (date, code) キーの dict リストで返す。
      - feature_exploration.py: 将来リターン計算 (calc_forward_returns)、IC（スピアマンランク相関）計算 (calc_ic)、ランク計算ユーティリティ (rank)、ファクター統計サマリー (factor_summary) を追加。外部依存を持たずに実装。
      - research パッケージの __init__.py で主要関数を再エクスポート。
  - Data プラットフォーム:
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー管理と営業日判定ロジックを追加（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - market_calendar の有無に応じた DB 優先／曜日フォールバック、探索上限、バックフィルや健全性チェックを実装。
      - calendar_update_job: J-Quants API から差分取得して冪等保存する夜間バッチ処理を実装（バックフィル、最大先読み、異常検知の挙動を含む）。
    - src/kabusys/data/pipeline.py / etl.py
      - ETL パイプライン用の ETLResult データクラスを追加（取得件数、保存件数、品質問題一覧、エラー一覧などを保持）。
      - 差分取得、保存（jquants_client 経由の冪等保存）、品質チェックフレームワークとの連携方針を設計文書に従って実装するインターフェースを整備。
      - jquants_client / quality モジュールとの分離設計（id_token 注入によりテスト容易性を確保）。
  - パッケージ公開インターフェース:
    - data.etl.ETLResult を再エクスポート。

Changed
- 設計上の重要な方針をコードコメントと関数実装に反映:
  - ルックアヘッドバイアス回避のため、datetime.today()/date.today() を直接参照する箇所を極力排除し、target_date を明示的に受け取る形に統一。
  - DuckDB のバージョン互換性（executemany の空リスト制約など）に配慮した実装（ai_scores 書き込みなど）。
  - OpenAI API 呼び出しを各モジュールで独立実装し、テスト時の差し替えポイントを提供（モジュール結合を避ける）。

Fixed
- 初期リリースのため該当なし（開発中の修正は今後のリリースで記載）。

Security / Behavior notes
- 環境変数の扱い:
  - 初期 OS 環境変数は上書き保護され、.env/.env.local の読み込み順序は OS env > .env.local > .env（.env.local は override=True）。
  - 必須の設定キー（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は Settings 経由で取得すると未設定時に明確な例外を送出。
- OpenAI API:
  - デフォルトモデルは gpt-4o-mini。JSON Mode を利用し厳格な JSON 応答を期待する設計。
  - API 失敗時のフェイルセーフやリトライ（指数バックオフ）を実装。

Known issues / Notes
- src/kabusys/data/pipeline.py の末尾に _get_max_date 関数内での return に関する不完全な記述（return date.fro といった未完成のトークン）が見られます。これは現時点での小さな実装上の欠落と思われ、正しい date 型の返却ロジック（例: date.fromisoformat 等）への修正が必要です。
- 一部モジュールの外部依存（jquants_client, quality, Slack 連携等）は抽象インターフェース化されており、実運用では該当クライアント実装と適切な環境変数設定が必要です。
- DuckDB のバージョン差異や型バインドの挙動によっては SQL バインド箇所の調整が必要になる可能性があります（特に配列型バインドの回避処理を行っていますが、環境依存の差が残り得ます）。

Migration / Usage notes
- .env の自動読み込みはデフォルトで有効。テストや CI で自動読み込みを抑制する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API を利用する関数（score_news, score_regime）は引数 api_key を受け取るため、環境変数に依存せずキー注入が可能です（テスト用モックの注入も想定）。
- ETL や calendar_update_job 等は DuckDB 接続を受け取る設計。実行前に必要なテーブルの初期スキーマ準備や jquants_client の設定が必要です。

ライセンスや著作権等の情報は別ファイルに記載してください。今後のリリースではバグ修正、API クライアントの実装サンプル、ドキュメントと使用例の追加を予定しています。