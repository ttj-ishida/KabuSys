CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
このプロジェクトでは "Keep a Changelog" の形式に準拠しています。
リリースは Semantic Versioning に従います。

0.1.0 - 2026-03-31
-----------------

Added
- 初回公開。本リリースでは日本株自動売買システムのコアライブラリを提供します。
  主な機能・モジュール:
  - kabusys.config
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
    - export KEY=val 形式やクォート・エスケープ、インラインコメントの扱いに対応する独自パーサを実装。
    - OS 環境変数を保護する protected 機能、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み抑止対応。
    - Settings クラスを提供し、必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や
      パス（DUCKDB_PATH, SQLITE_PATH）・環境（KABUSYS_ENV）・ログレベル（LOG_LEVEL）をバリデーション付きで参照可能に。
    - settings = Settings() をパッケージ外から利用可能に公開。

  - AI モジュール（kabusys.ai）
    - news_nlp
      - raw_news / news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）へ送信し、
        JSON モードでセンチメントスコアを取得・検証して ai_scores テーブルへ書き込む。
      - バッチ処理（最大20銘柄/チャンク）、記事トリム（記事数上限・文字数上限）を実装。
      - API 呼び出しに対して 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライを実装。
      - レスポンスの堅牢なバリデーション（JSON 抽出処理、未知コードの無視、数値チェック、スコアの ±1 クリップ）。
      - テスト容易性のため _call_openai_api の差し替えを想定（unittest.mock.patch によるモック化）。

    - regime_detector
      - ETF 1321（Nikkei225 連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して
        日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込み。
      - マクロ記事抽出はマクロキーワード（日本・米国／グローバル系）でフィルタし、LLM 呼び出しは記事がある場合のみ実施。
      - API エラー・パースエラーは macro_sentiment=0.0 にフォールバックする堅牢な設計。
      - OpenAI 呼び出しは news_nlp と独立した実装でモジュール結合を避ける。

  - Research モジュール（kabusys.research）
    - factor_research
      - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR）、
        流動性（20日平均売買代金・出来高変化率）、バリュー（PER, ROE）を DuckDB 上の SQL + Python で計算。
      - データ不足への明示的ハンドリング（十分な履歴がない場合は None を返す等）。
    - feature_exploration
      - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリー、ランク変換ユーティリティを提供。
      - pandas 等に依存せず標準ライブラリのみで実装。

  - Data モジュール（kabusys.data）
    - calendar_management
      - JPX カレンダー（market_calendar）管理と夜間バッチ更新ジョブ（calendar_update_job）を実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API を提供。
      - market_calendar が未取得のときは曜日ベースでフォールバックする堅牢な挙動。
      - 最大探索日数やバックフィル、健全性チェック（将来日付の異常検出）を実装。
    - pipeline / etl
      - ETLResult dataclass を公開し、ETL 実行結果の集約（取得件数・保存件数・品質問題・エラー）を保持。
      - 差分取得・バックフィル・品質チェックのための設計方針を実装（詳細ロジックは pipeline に準拠）。

  - 共通設計・運用面
    - DuckDB を主要なデータストアとして利用するクエリ実装。
    - DB 書き込みは冪等性を意識（DELETE → INSERT、ON CONFLICT 想定）して実装。
    - ルックアヘッドバイアス防止: datetime.today()/date.today() への直接依存を避け、ターゲット日を明示的に引数指定する設計。
    - ロギングを各処理に導入し、情報・警告・例外時に十分なメッセージを記録。
    - テスト容易性: API キー注入、内部 OpenAI 呼び出しの差し替えポイントなどを用意。

Fixed
- 初期リリースにつき該当なし（実装時の防御的処理やフォールバック挙動を "Added" として含む）。

Security
- OpenAI API キーや各種トークンは環境変数経由で取得する設計。必須項目は Settings で検証し、未設定時は明示的に ValueError を投げるため
  実行時に秘密情報が欠けていることが分かるようになっています。

Notes / 備考
- OpenAI との通信は JSON Mode（response_format={"type":"json_object"}）を前提にしており、レスポンスパースに失敗した場合は安全にスキップまたはフォールバックする実装です。
- DuckDB のバージョン差異（executemany の空リスト制約など）を考慮した実装上の配慮があります。
- 本リリースはデータ取得 / スコア算出 / リサーチロジックまでを含む「分析・決定支援」部分が中心で、
  実際の売買実行（kabuステーション等）やモニタリングの詳細は別モジュールとして分離されています（パッケージ公開 API は __all__ で data, strategy, execution, monitoring を想定）。
  
今後の予定（例）
- 実運用時のモニタリング・アラート強化（Slack 通知など）の実装。
- strategy / execution モジュールの具体的な発注ロジックと安全制御の実装。
- テストカバレッジの拡充と CI 設定の公開。

既知の制約
- OpenAI 呼び出しは外部 API に依存しており、実行には有効な OPENAI_API_KEY が必要です。
- DuckDB スキーマ（prices_daily, raw_news, ai_scores, market_calendar, raw_financials 等）が前提となります。サンプルスキーマやマイグレーションは別途用意する必要があります。