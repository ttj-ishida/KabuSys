# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース。日本株自動売買システム "KabuSys" のコア機能群を実装しました。主に以下の領域を含みます。

### Added
- パッケージ基礎
  - パッケージ初期化: kabusys パッケージの __version__ を "0.1.0" に設定し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で公開。

- 環境設定管理（kabusys.config）
  - .env ファイル自動読み込み機能を導入（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 高度な .env パース:
    - コメント、export 形式の対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理などをサポート。
  - Settings クラスを提供し、アプリケーション設定（J-Quants トークン、kabu API、LINE 設定、DB パス、監視閾値、実行環境・ログレベル判定等）をプロパティで取得可能。
  - 必須環境変数のチェック（_require）により未設定時に明確な ValueError を送出。

- AI (自然言語処理) 機能（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに記事をまとめて OpenAI（gpt-4o-mini）に投げ、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄／コール）、1 銘柄あたり記事数・文字数の上限を設けトークン肥大化対策を実施。
    - JSON Mode 出力のバリデーションとフォールバック（JSON 抽出ロジック）、スコアの ±1.0 クリップ。
    - エラー処理: 429／ネットワーク断／タイムアウト／5xx は指数バックオフでリトライ。その他はスキップしてフェイルセーフ動作。
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
    - score_news(conn, target_date, api_key=None) を公開し、取得した銘柄数を返す。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルに日次判定を書き込む。
    - OpenAI 呼び出しは独立実装（news_nlp とプライベート関数を共有しない設計）。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。リトライは同様に指数バックオフ。
    - ルックアヘッドバイアス対策: date 比較は常に target_date 未満・排他にし、datetime.today()/date.today() を参照しない。
    - score_regime(conn, target_date, api_key=None) を公開し、DB に冪等的に（BEGIN / DELETE / INSERT / COMMIT）書き込む。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを追加し、ETL の各種メトリクス（取得件数／保存件数／品質問題／エラー等）を保持。
    - 差分取得・バックフィル・品質チェックの設計方針に従ったユーティリティを実装（詳細は docstring）。
    - ETLResult.to_dict() により品質問題を辞書化して監査ログ等に利用可能。
  - ETL インターフェース再エクスポート（kabusys.data.etl: ETLResult）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを使った営業日判定ロジックを提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB 登録がない場合の曜日ベースフォールバック（週末は非営業日）。
    - カレンダー更新ジョブ（calendar_update_job）を実装。J-Quants API から差分取得して冪等保存（save_market_calendar を利用）。
    - 健全性チェック、バックフィル設定、最大探索日数制限などの安全装置を実装。
  - 各種内部ユーティリティ（テーブル存在チェック、DuckDB の日付変換等）を提供。

- リサーチ機能（kabusys.research）
  - factor_research モジュール
    - calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials を参照）。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - Value: PER・ROE（raw_financials からの最新財務データを利用）。
    - DuckDB SQL を利用した計算で、データ不十分時は None を返す設計。
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（IC）を計算。レコード数不足時は None を返す。
    - rank: 同順位は平均ランクで扱う実装（丸めによる tie 対応）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
  - zscore_normalize は kabusys.data.stats から再エクスポート。

### Changed
- 初版リリースのため過去の変更履歴はなし。

### Fixed
- 初版リリースのため修正履歴はなし。

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY から解決され、未設定時は ValueError で明示的に通知する設計。API キーの直接ログ出力は行わない想定（実装内での出力はなし）。
- .env のロードでは既存 OS 環境変数を保護する保護セット（protected）を導入。

### Notes / 設計上の重要点
- ルックアヘッドバイアス対策: 主要な関数（score_news, score_regime, factor 計算等）は date.today()/datetime.today() に依存せず target_date ベースで動作します。
- フェイルセーフ原則: 外部 API（OpenAI, J-Quants）失敗時は処理を中断せず、可能な限り安全なデフォルト（ゼロ相当、スキップ）で継続する実装方針を採用しています。
- DuckDB を主要なローカルデータ基盤として利用。DB 操作は冪等性（DELETE→INSERT 等）を考慮。
- テスト容易性: OpenAI 呼び出し部分はモック差し替えを想定した実装になっています（関数単位で patch が可能）。

もし特定の変更点をさらに詳しく記載したい箇所（例: 各関数の入出力例、例外ケース、既知の制限など）があればお知らせください。追加で CHANGELOG の詳細化や英語版作成も対応します。