Changelog
=========

すべての変更は Keep a Changelog のフォーマットに従って記載しています。  
安定化・互換性のためセマンティックバージョニングを採用しています。

[Unreleased]
------------

（現時点のリポジトリ状態から推測した最初の公開バージョンを下に記載しています。今後の変更はここに追加してください。）

[0.1.0] - 2026-04-03
--------------------

Added
- 初回リリース: KabuSys — 日本株自動売買支援ライブラリの骨子を実装。
  - パッケージ公開情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ を定義。
  - 設定・環境変数管理 (kabusys.config)
    - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
      - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して特定（CWD 非依存）。
      - .env / .env.local を読み込み、OS 環境変数を保護しつつ .env.local は上書き可能。
      - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export 文やシングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - Settings クラスを公開（settings）：J-Quants、kabuステーション、LINE、DB パス、監視パラメータ、ログレベル、実行環境フラグ等のプロパティを提供。
    - 必須キー未設定時は明確な ValueError を投げる _require を実装。
  - AI モジュール (kabusys.ai)
    - news_nlp.score_news
      - raw_news と news_symbols を使い「前日 15:00 JST 〜 当日 08:30 JST」の窓で記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄別センチメントを付与して ai_scores テーブルへ書き込み。
      - バッチ処理（最大20銘柄/コール）、各銘柄は最大記事数・文字数でトリム。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。APIエラー・検証失敗はログを出してスキップ（フェイルセーフ）。
      - レスポンス検証（JSON 抽出、results 配列、code/score 検証、数値チェック、スコアクリップ）。
      - DuckDB executemany の互換性を考慮した安全な DELETE → INSERT の置換ロジック。
    - regime_detector.score_regime
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、market_regime テーブルへ冪等書き込み。
      - マクロ記事はキーワードフィルタ（日本・米国系キーワード群）で抽出、OpenAI 呼び出しは別実装の _call_openai_api を使用（モジュール結合を抑止）。
      - API リトライ、障害時の macro_sentiment=0.0 フォールバック、レスポンスパースエラーのハンドリングを実装。
      - ルックアヘッドバイアス対策: date 比較は target_date 未満を明示して使用、datetime.today() を参照しない設計。
  - データモジュール (kabusys.data)
    - calendar_management
      - JPX カレンダー管理（market_calendar）と営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - DB 登録がない/未登録日の場合は曜日ベースのフォールバック（週末は非営業日扱い）。
      - 最大探索日数や健全性チェック、バックフィル戦略を実装。
      - calendar_update_job: J-Quants API から差分取得 → 冪等保存。API失敗時は安全に 0 を返す設計。
    - pipeline / etl
      - ETLResult データクラスを公開（kabusys.data.ETLResult を再エクスポート）。
      - ETL の方針・結果格納（取得件数、保存件数、品質問題リスト、エラーリスト等）を定義。
      - 差分更新、バックフィル、品質チェックの取り扱い方針を実装（詳細は pipeline モジュールに記述）。
    - jquants_client との連携を前提とした差分取得・保存フロー（モジュール内で利用）。
  - 研究・リサーチモジュール (kabusys.research)
    - factor_research
      - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER / ROE）を計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
      - DuckDB の SQL ウィンドウ関数を活用し、一貫して prices_daily / raw_financials のみを参照する実装。
      - データ不足時は None を返すなど安全に欠損を扱う仕様。
    - feature_exploration
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
      - pandas 等に依存せず標準ライブラリのみで実装。
  - パッケージ構成
    - 主要な公開関数／モジュールを __all__ 等で整理して再エクスポート（research, data, ai 等）。

Security / Required configuration
- AI 関連機能を使うには OpenAI API キー（OPENAI_API_KEY もしくは api_key 引数）が必須。未設定時は ValueError を送出するようになっています。
- 初期設定として期待される主な環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabuステーション API）
  - OPENAI_API_KEY（AI 機能）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知連携：任意）
  - DUCKDB_PATH / SQLITE_PATH / 各種監視ファイルパス（デフォルトあり）
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後には .env の配置に注意。

Design / Implementation Notes
- ルックアヘッドバイアス対策: 各種処理（ニュース窓・指標計算・ETL 等）で datetime.today()/date.today() の直接参照を避け、target_date を明示的に渡す設計。
- DB 書き込みは冪等性を意識（DELETE→INSERT のパターンや ON CONFLICT を想定）。
- OpenAI 呼び出しは JSON Mode を利用して厳密な JSON 出力を期待しつつ、現実の雑多な出力に耐える復元ロジック（{} の抽出等）を実装。
- ネットワーク／API 障害に対してはリトライ（指数バックオフ）を標準実装、致命的ではない場合はスキップして処理継続（フェイルセーフ）。
- Research モジュールはあくまで分析用で、実際の発注や取引 API にはアクセスしない方針。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 特記事項なし（ただし OpenAI/API キー取扱いに注意）。

Migration notes
- 初回リリースのためアップグレード手順は不要です。将来のバージョンで API 変更がある場合はここに記載します。

参考（実装上の注意）
- DuckDB に依存するため、ターゲット環境には duckdb が必要です。
- OpenAI SDK（およびネットワーク接続）は AI 機能利用時に必須です。
- .env 取り扱いの挙動（.env と .env.local の優先度や OS 環境変数保護）に依存したテストや運用を行う場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動ロードを抑止してください。

---

（この CHANGELOG は、提供されたコードベースの内容・コメント・設計注釈から推測して作成しています。実際のリリース履歴や日付／内容はリポジトリの運用方針に合わせて調整してください。）