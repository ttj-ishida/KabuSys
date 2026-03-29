# Changelog

すべての変更は「Keep a Changelog」仕様に従って記載しています。  
セマンティックバージョニングに従います（MAJOR.MINOR.PATCH）。

なお本ファイルはコードベースの内容から実装・設計意図を推測して作成しています。

## [Unreleased]

- ドキュメントおよびリファクタ段階のメモ（現時点で未リリースの変更点はありません）。

---

## [0.1.0] - 2026-03-29

初回公開リリース。

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - 公開 API: kabusys.__init__ にて __version__ = "0.1.0"、__all__ = ["data", "strategy", "execution", "monitoring"]

- 設定 / 環境変数管理モジュールを追加（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）を基準に自動で .env / .env.local を読み込む仕組みを実装
  - .env パーサーの実装（コメント扱い、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ対応）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - settings オブジェクトを提供し、必須値取得時は未設定で ValueError を送出
  - 利用可能な設定例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG..CRITICAL の検証）

- AI 関連モジュールを追加（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）でセンチメントを評価
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 表現）
    - バッチ処理（最大 20 銘柄 / コール）、1 銘柄あたりの記事数・文字数の制限
    - レスポンスのバリデーションとスコアの ±1.0 クリッピング
    - 429/ネットワーク/タイムアウト/5xx に対する指数的バックオフとリトライ
    - DuckDB に対する冪等的な書き込み（DELETE → INSERT）実装
    - テスト容易性のため _call_openai_api の差し替え（patch）を想定

  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定
    - マクロニュース抽出はキーワードベース（複数キーワードリスト）でタイトルを取得
    - OpenAI 呼び出し（gpt-4o-mini）に対するリトライ・フェイルセーフ（API 失敗時 macro_sentiment=0.0）
    - レジームスコアのクリップと閾値判定
    - 判定結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT を利用）
    - ルックアヘッドバイアス対策（datetime.today()/date.today() を参照しない、SQL 側で date < target_date 等を採用）

- データプラットフォーム関連モジュールを追加（kabusys.data）
  - calendar_management モジュール
    - JPX カレンダー管理（market_calendar テーブル）
    - 営業日判定・前後営業日取得・期間内営業日取得（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
    - SQ 日判定（is_sq_day）
    - DB にデータが無い場合の曜日ベースのフォールバック実装
    - 夜間の calendar_update_job（J-Quants API からの差分取得と保存）実装、バックフィルと健全性チェックを行う

  - pipeline モジュール（kabusys.data.pipeline）
    - ETL パイプラインの骨格（差分取得、保存、品質チェックの組み込み方針）
    - ETLResult データクラスを実装（取得数/保存数、品質問題、エラーの集約）
    - テーブル存在確認や最大日付取得ユーティリティを実装
    - market calendar／prices／financials の差分取得と backfill を想定した設計

  - etl モジュールは ETLResult を再エクスポート（kabusys.data.etl）

- リサーチ関連モジュールを追加（kabusys.research）
  - factor_research モジュール
    - Momentum（1M/3M/6M リターン・200日移動平均乖離）、Volatility（20日 ATR）、
      Value（PER・ROE）等のファクター計算を DuckDB 上で SQL と Python の組合せで実装
    - 入力は prices_daily / raw_financials に限定（外部 API 呼び出しなし）
    - データ不足時の None 扱い、ログ出力

  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）
    - IC（Information Coefficient）計算（calc_ic：スピアマンのランク相関）
    - ランク付け（rank：平均ランクを計算、同順位処理対応）
    - ファクター統計サマリー（factor_summary：count/mean/std/min/max/median）
    - 外部ライブラリに依存せず標準ライブラリのみで実装

### Changed
- 設計上の方針・実装上の注意点を明示
  - 主要な分析処理でルックアヘッドバイアスを避けるため datetime.today()/date.today() を直接参照しない実装方針を採用
  - DuckDB のバージョン差異（executemany の空リスト扱い等）に配慮した実装
  - OpenAI 呼び出しの共通点はあるがモジュール間でプライベート関数を共有しない設計（結合低減）

### Fixed
- （初期リリースにつき、既知のバグ修正履歴はなし。実装内に疑似的なフェイルセーフや入力バリデーションを多用し運用時の障害を小さくする設計を適用）

### Security
- API キーは引数経由または環境変数 OPENAI_API_KEY を使用する実装。未設定時は ValueError を発生させ明示的に失敗させることで秘密情報漏洩リスクを低減。

---

開発者向け補足（実装から推測）
- テスト容易性が考慮されており、OpenAI 呼び出し部分は unittest.mock.patch で差し替えられるように設計されている。
- DuckDB を主たるローカルデータ層として利用する予定で、テーブル名（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等）に依存する実装になっている。
- ロギングと例外ハンドリングを適度に行い、API障害時はフェイルセーフ（スコア 0.0 や処理スキップ等）で継続可能。

もし特定ファイルや変更点（例: リリース日、リリースノートの粒度、追加の履歴バージョン分割など）を反映したい場合は、その要望を教えてください。