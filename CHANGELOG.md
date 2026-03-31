# Changelog

すべての重大な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-31

### Added
- パッケージ基盤
  - パッケージのエントリポイントを追加（kabusys.__init__）。公開サブパッケージ: data, research, ai, execution, monitoring, strategy（__all__ に "data", "strategy", "execution", "monitoring" が明示）。
  - バージョン情報: __version__ = "0.1.0" を設定。

- 環境変数 / 設定管理
  - robust な .env ローダーを実装（kabusys.config）。
    - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（CWD 非依存、配布後も動作）。
    - .env / .env.local の自動読み込み（優先度: OS 環境 > .env.local > .env）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 行パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを考慮。
    - override と protected（OS 環境変数保護）オプションをサポート。
  - Settings クラスを提供（kabusys.config.settings）。
    - J-Quants / kabu API / Slack / DB パス / 監視閾値 / システム設定等のプロパティ（必須環境変数は取得時に ValueError を送出）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、is_live / is_paper / is_dev の補助プロパティ。

- データプラットフォーム（DuckDB ベース）
  - ETL 用インターフェースとして ETLResult を公開（kabusys.data.pipeline / kabusys.data.etl）。
    - ETL 実行結果の構造を dataclass で定義し、品質問題やエラーの集約をサポート。
  - カレンダー管理モジュール（kabusys.data.calendar_management）
    - market_calendar を基にした営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データ優先、未登録日は曜日ベースでフォールバック（週末判定）。
    - 夜間バッチ calendar_update_job により J-Quants から差分取得して idempotent に保存（バックフィル、健全性チェックを含む）。
    - 最大探索日数やバックフィル日数等の安全パラメータを設定し無限ループを防止。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新・保存（jquants_client 呼び出し）・品質チェック（quality モジュール連携）を行う設計。
  - 最終取得日の backfill、デフォルトのバックフィル日数定義、エラーや品質問題を集めて返す方針を採用（Fail-Fast しない）。
  - DuckDB 存在チェックや最大日付取得ユーティリティを実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を読み、銘柄ごとにニュースを集約し OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得して ai_scores に保存する処理を実装。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して対象記事を選定（calc_news_window）。
  - バッチ処理: 最大 20 銘柄毎にチャンク送信（_BATCH_SIZE=20）、1銘柄あたりの記事は最新 10 件・最大文字数 3000 文字にトリム。
  - OpenAI 呼び出しで 429 / ネットワーク / タイムアウト / 5xx を指数バックオフでリトライ。非再試行のエラーはスキップして継続（フェイルセーフ）。
  - レスポンスの厳格な検証（JSON パースの復元ロジック、"results" リスト、code の照合、スコアの数値化・有限性チェック）。
  - スコアは ±1.0 にクリップし、取得した銘柄のみを DELETE → INSERT の冪等書き換えで ai_scores に保存（部分失敗時に既存スコアを保護）。
  - テスト容易性: _call_openai_api をモック可能に実装。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定（score_regime）。
  - マクロニュースは news_nlp の calc_news_window で算出されるウィンドウからマクロキーワードでフィルタしたタイトルを抽出して評価。
  - OpenAI 呼び出しのリトライ/フォールバック実装（API 失敗時は macro_sentiment = 0.0 のフェイルセーフ）。
  - レジームスコアはクリップされ、しきい値によりラベル判定。結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - テスト容易性: OpenAI 呼び出しを差し替え可能に設計。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。
    - Momentum: 1M/3M/6M リターン、ma200 乖離（データ不足時は None を返す）。
    - Volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率等（必要行数未満は None）。
    - Value: raw_financials から最新財務データと株価を組合せて PER / ROE を算出（EPS=0 や欠損時は None）。
  - feature_exploration: calc_forward_returns（任意の horizon 対応、入力チェックあり）、calc_ic（Spearman ランク相関）、factor_summary（基本統計量）、rank（同順位は平均ランク）。
  - zscore_normalize を data.stats から再エクスポート（kabusys.research.__init__ にて公開）。

### Behavior / Design decisions
- ルックアヘッドバイアス防止
  - 日付基準の処理は内部で datetime.today() / date.today() に依存しない実装。target_date パラメータを明示的に受け取ることでルックアヘッドを防止。
  - DB クエリは target_date 未満／等で明確に境界を扱う。

- フォールバック / フェイルセーフ
  - 外部 API（OpenAI / J-Quants）呼び出しが失敗した場合でもシステムは継続するように設計（スコアは 0.0 にフォールバック、該当チャンクはスキップ等）。
  - DB 書き込みはトランザクションで保護し、失敗時は ROLLBACK を行う。ROLLBACK 自体の失敗は警告ログに記録。

- DuckDB 互換性配慮
  - executemany に空リストを与えないガード（DuckDB 0.10 の制約回避）。
  - テーブル存在チェックや情報スキーマクエリを適用。

- テスト容易性
  - OpenAI 呼び出し箇所（_kabusys.ai.news_nlp._call_openai_api, kabusys.ai.regime_detector._call_openai_api）をモック可能に切り出し。
  - .env 自動ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Fixed
- 初期リリースのため該当なし。

### Removed
- 初期リリースのため該当なし。

### Migration notes
- 既存の環境変数 / .env の取り扱いに変更はありませんが、自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI を使用する機能（news scoring / regime scoring）は OPENAI_API_KEY の設定が必須です（引数で注入することも可）。

--- 
（注）本 CHANGELOG は現在のコードベースの実装内容から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース差分を参照して調整してください。