# Changelog

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]
- 今後の変更予定や作業中の変更をここに記載します。

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システムのコア機能群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" に設定。主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で公開。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env 読み込みロジック: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理（クォートあり/なしで振る舞いを分岐）。
  - .env 読み込みで既存 OS 環境変数を保護するための protected キーセットと override オプションを実装。
  - Settings クラスを提供。J-Quants / kabuステーション / Slack / DB パス等のプロパティを環境変数から取得し、必須項目未設定時は明確なエラーメッセージを送出。KABUSYS_ENV と LOG_LEVEL のバリデーションを実装。
  - DuckDB / SQLite のパスはデフォルト設定を提供（expanduser を考慮）。

- AI モジュール (`kabusys.ai`)
  - news_nlp: ニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを評価し、ai_scores テーブルへ書き込む `score_news` を実装。
    - ニュース収集ウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を行う `calc_news_window` を提供。
    - 銘柄ごとに記事を集約し（最大記事数・最大文字数でトリム）、最大バッチサイズで API 呼び出し。
    - JSON Mode による厳密な JSON 出力期待、レスポンスの頑健なバリデーション（JSON 抽出、results キー検査、コード存在チェック、数値検証）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフによるリトライ。失敗時はスキップして処理継続（フェイルセーフ）。
    - スコアを ±1.0 にクリップし、取得済みコードのみを DELETE → INSERT で idempotent に更新（部分失敗時の保護）。
    - テスト用フック: `_call_openai_api` を patch 可能に設計。
  - regime_detector: ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定する `score_regime` を実装。
    - ma200_ratio 計算（target_date 未満のデータのみ使用しルックアヘッドを防止）、マクロ記事抽出用キーワードリスト、LLM 呼び出しと合成ロジックを実装。
    - API 失敗時は macro_sentiment を 0.0 にフォールバックし処理を継続。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）、失敗時の ROLLBACK とログ。

- データ関連 (`kabusys.data`)
  - calendar_management:
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar 未取得時の曜日ベースのフォールバック、最大探索範囲制限、バックフィル・健全性チェックを実装。
    - calendar_update_job により J-Quants クライアント（jquants_client）からの差分取得、バックフィル日数の再取得、保存処理（ON CONFLICT 相当）を提供。
  - pipeline / etl:
    - ETL パイプライン用ユーティリティと `ETLResult` データクラスを実装。
    - `_get_max_date` 等のヘルパー、差分更新・バックフィル・品質チェックを想定した設計（quality モジュールとの連携を想定）。
    - `kabusys.data.etl` で ETLResult を再エクスポート。

- リサーチ関連 (`kabusys.research`)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比）およびバリュー（PER, ROE）を計算する関数群を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの集計を実装し、データ不足時は None を返す等の堅牢性を確保。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、rank / factor_summary 等の統計ユーティリティを実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で完結する設計。
  - `kabusys.research.__init__` で主要関数を公開（zscore_normalize は data.stats から再利用）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- JSON レスポンスの取り扱いにおいて、JSON mode でも前後に余計なテキストが混ざるケースを想定して最外の {} を抽出して復元する処理を追加（news_nlp のレスポンスパース耐性向上）。
- DuckDB の executemany の制約（空リスト不可）を考慮して、実行前に空チェックを入れる等の互換性対応を実装。

### 内部 (Internal)
- OpenAI 呼び出し部分はモジュール間の結合を避けるため、news_nlp と regime_detector で各モジュール内に独立した `_call_openai_api` を実装。テスト時に差し替え可能。
- ロギングを各モジュールで充実させ、警告や例外時に詳細ログを出すよう設計。
- ルックアヘッドバイアス防止の観点から、いずれの処理も datetime.today()/date.today() を直接参照しない（target_date を明示的に渡す設計）。

### セキュリティ (Security)
- API キー未設定時に明示的な ValueError を投げることで誤った運用を防止。
- 環境変数の自動上書きを防ぐ保護機構（protected set）を導入。

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）

---

注:
- 本 CHANGELOG はリポジトリ内のソースコードから実装意図・機能を推測して作成しています。実際のリリースノートに使う場合は、実際のリリース手順やリリース日、関連ドキュメントへのリンク等を追記してください。