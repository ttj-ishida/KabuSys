CHANGELOG
=========

すべての変更は Keep a Changelog の書式に準拠して記載しています。  
リリースはセマンティックバージョニングに従います。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース。kabusys の基本コンポーネントを実装。
- パッケージ公開情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートの特定は .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 複雑な .env パース処理を実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - インラインコメントの取り扱い（クォートあり/なしでの振る舞い差分）
  - .env 上書き挙動: .env は既存 OS 環境変数を上書きせず、.env.local は上書き（ただし OS 環境変数は保護）。
  - Settings クラスを提供（環境変数から設定を取得するプロパティ群）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス: DUCKDB_PATH, SQLITE_PATH（Path 型で返す）
    - システム設定: KABUSYS_ENV（development/paper_trading/live を検証）、LOG_LEVEL（DEBUG/INFO/... を検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - 必須環境変数が未設定の場合は明示的に ValueError を送出する _require 実装。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント（news_nlp.score_news）
    - raw_news / news_symbols を集約し、銘柄ごとに最大記事数・最大文字数でトリムして OpenAI（gpt-4o-mini）の JSON Mode で一括評価。
    - バッチサイズ、トークン膨張対策、最大記事/文字数制約を組み込み。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライ実装。
    - レスポンスの厳密なバリデーション（JSON パース、results 配列、code/score の検証、スコアの有限値チェック）。
    - スコアは ±1.0 にクリップし、取得済み銘柄のみ ai_scores テーブルに置換（DELETE → INSERT）することで冪等性と部分失敗耐性を確保。
    - テスト容易性のため OpenAI 呼び出し点は差し替え可能（関数をモジュール内で明示的に定義）。
    - calc_news_window により JST ベースのニュース集計ウィンドウを計算（ルックアヘッド防止で UTC naive datetime を返す）。
  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news からマクロキーワードでフィルタし、OpenAI で -1.0〜1.0 の macro_sentiment を取得。
    - レスポンスの JSON パースや API エラー時はフェイルセーフとして macro_sentiment=0.0 を利用（例外を上げず継続）。
    - レジーム計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI クライアント生成や API 呼び出しは分離されており、テスト時にモック可能。

- Data モジュール（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar テーブルを用いた JPX カレンダーの運用ロジックを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティを実装。
    - DB にデータがない場合は曜日ベースのフォールバック（週末は非営業日）を採用し、DB とフォールバックの挙動を一貫させる設計。
    - calendar_update_job により J-Quants API から差分取得 → 保存（バックフィル、健全性チェック含む）する夜間バッチを実装。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを導入（取得/保存件数、品質問題、エラー一覧などを集約）。
    - 差分取得、バックフィル、品質チェックのためのユーティリティを含む（jquants_client と quality モジュールを利用）。
    - DuckDB のテーブル存在確認や最大日付取得などのユーティリティを実装。
  - etl モジュールは ETLResult を再エクスポート。

- Research モジュール（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M）、ma200_dev（200日MA乖離）、ATR（20日）、平均売買代金、出来高比率、PER/ROE（raw_financials 参照）等を計算する関数を実装:
      - calc_momentum, calc_volatility, calc_value
    - DuckDB の SQL ウィンドウ関数を活用し、営業日数ベースのホライズンを扱う設計。
    - データ不足や条件不成立時は None を返す挙動で安全に動作。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンのリターンを一括クエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関（ランク化関数 rank を含む）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
    - 外部ライブラリに依存しない、標準ライブラリのみの実装。
  - データ正規化ユーティリティ zscore_normalize を data.stats から再エクスポート。

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Security
- 環境変数の取り扱いに注意:
  - 必須キーは Settings で明示的にチェックし、未設定で ValueError を発生させる。
  - .env/.env.local をロードする際に OS 環境変数を保護する仕組みを導入（protected set）。
  - OpenAI API キーが未設定の場合は明確なエラーメッセージを出力して処理を停止する。

Notes / Implementation details
- ルックアヘッドバイアス対策:
  - date.today() / datetime.today() を主要ロジックで参照せず、呼び出し側が target_date を与える設計を採用。
  - DB クエリでは date < target_date / date BETWEEN ... のように排他条件を使用して未来データ参照を防止。
- 冪等性:
  - market_regime, ai_scores, 各種 save_* は既存データを置換・更新する方式を想定し、部分失敗で他データを消さない実装（DELETE → INSERT の制御）。
- フェイルセーフ:
  - 外部 API（OpenAI, J-Quants）失敗時は可能な限りフォールバック値（例: macro_sentiment=0.0）で継続し、致命的エラーは上位に伝搬。
- テスト性:
  - OpenAI 呼び出し箇所はモジュール内部関数として分離されており unittest.mock.patch による差し替えが可能。
- DuckDB 互換性メモ:
  - DuckDB 0.10 の executemany に空リストを渡せない制約を考慮して空チェックを入れている箇所あり。

Deprecated
- なし

Removed
- なし

Acknowledgements
- 初期設計ではデータ取得・品質・分析・AI 評価・市場レジーム判定を分離しており、実運用での安全性（冪等性、フォールバック、ロギング）を重視しています。