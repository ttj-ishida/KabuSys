# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

なお、本リポジトリの初期バージョンは 0.1.0 です。

## [Unreleased]

（未リリースの変更はここに記載）

---

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買／データプラットフォーム向けの基盤機能を提供します。主な追加点は以下の通りです。

### 追加
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - モジュール公開インターフェースを整備（__all__）。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に検出。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 高度な .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 環境変数必須チェック関数（_require）と Settings クラスを提供。
  - 設定項目（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live 検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL 検証）

- AI（自然言語処理 / レジーム検出）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）でセンチメントを取得。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数と文字数上限でトリム。
    - JSON Mode による厳密な JSON 応答想定とレスポンスの堅牢なバリデーション。
    - 429/ネットワーク断/タイムアウト/5xx などは指数的バックオフでリトライし、失敗時は個別チャンクをスキップ（フェイルセーフ）。
    - スコアは ±1.0 にクリップ。成功した銘柄のみ ai_scores テーブルへ（DELETE → INSERT の冪等書き込み）。
    - 公開 API: score_news(conn, target_date, api_key=None)
    - ニュース集計ウィンドウ（JST基準）:
      - 前日 15:00 JST ～ 当日 08:30 JST（DB比較は UTC naive datetime で計算）
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定。
    - マクロニュースは raw_news からキーワードフィルタで抽出（キーワードリストあり）。
    - OpenAI 呼び出し（gpt-4o-mini、JSON mode）とリトライ/フェイルセーフ実装。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）。APIキーは引数 or 環境変数 OPENAI_API_KEY。
    - 公開 API: score_regime(conn, target_date, api_key=None)

- データ（ETL / カレンダー / パイプライン）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分取得、バックフィル、品質チェックのインフラを実装。
    - ETL 実行結果を表すデータクラス ETLResult を提供（kabusys.data.etl で再エクスポート）。
    - ETLResult は品質問題とエラー情報の集約、辞書化ユーティリティを提供。
  - 市場カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定・探索ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にデータがない場合は曜日（土日判定）をフォールバックとして使用。
    - カレンダー夜間更新ジョブ calendar_update_job(conn, lookahead_days=...) を実装（J-Quants API 経由の差分取得 + 保存）。
    - 最大探索日数やバックフィル日数、健全性チェック（将来日付異常の検出）など安全策を実装。
  - データ保存クライアントの利用に関するユーティリティ（jquants_client 経由の fetch/save 呼び出しを想定）。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算群を提供（prices_daily / raw_financials を参照、外部 API 不使用）:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）
    - calc_volatility: 20日 ATR、相対ATR、平均売買代金、出来高比率（データ不足は None）
    - calc_value: PER / ROE（raw_financials から最新財務を取得）
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括取得
    - calc_ic: スピアマン-ランク相関（IC）計算（3件未満は None）
    - factor_summary / rank: ファクター統計サマリーとランク付けユーティリティ
  - zscore_normalize を含むユーティリティ類はデータ層から利用可能に。

- DB / トランザクション設計
  - DuckDB を主要な分析用 DB として想定（型変換、日付パースユーティリティ含む）。
  - 各所で冪等書き込み（DELETE→INSERT や ON CONFLICT 想定）やトランザクション管理（BEGIN/COMMIT/ROLLBACK）を採用。
  - DuckDB の executemany の制約（空リスト不可）を考慮した実装。

### セキュリティ / 設計上の注意点
- 外部 API キーは引数優先、その次に環境変数（OPENAI_API_KEY）を参照する設計。未設定時は ValueError を発生させる保護。
- 自動 .env ロードはプロジェクトルート検出に基づいており、配布後の動作を考慮。
- 外部 API 呼び出しでの過剰な例外伝播を避けるため、LLM 失敗時はスコアにフォールバック値を使用して処理継続するフェイルセーフを実装（サービス継続性重視）。
- ルックアヘッドバイアス防止: 各処理は内部で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る仕様。

### 変更（設計/実装上のハイライト）
- 各モジュールで堅牢性を優先:
  - API 呼び出しはリトライ / バックオフを実装。
  - レスポンスのバリデーションとサニティチェックを多層で実行。
  - DB がまばらな状況でも一貫した振る舞いを保つ（カレンダーのフォールバック等）。
- JSON Mode（OpenAI の JSON 応答）を前提にした厳密なパース処理を導入し、余分なテキスト混入への復元ロジックも実装。

### 既知の制限 / 今後の作業候補
- PBR や配当利回りなどのバリューファクターは未実装（calc_value の注記参照）。
- News / Regime の LLM 呼び出しは gpt-4o-mini に依存しているためモデル選択の拡張や抽象化を検討。
- テスト用フック（_call_openai_api の差し替えポイント等）はあるが、ユニットテスト・統合テストの整備が必要。
- DuckDB バージョン依存の振る舞い（list バインド、executemany の制約）により将来の互換性対応が必要になる場合がある。

---

## バージョニング方針
- セマンティックバージョニングに従います（MAJOR.MINOR.PATCH）。
- 破壊的変更がある場合は MAJOR を、後方互換性のある機能追加は MINOR を、バグ修正は PATCH を更新します。

---

（終）