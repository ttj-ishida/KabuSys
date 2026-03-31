Keep a Changelog 準拠の CHANGELOG.md（日本語）

すべての重要な変更は「Keep a Changelog」ガイドラインに従って記録しています。
https://keepachangelog.com/ja/1.0.0/

現在のバージョン: 0.1.0

## [Unreleased]
（次のリリースに向けた未確定の変更をここに記載します）

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買・データ基盤・リサーチ・AI 支援機能を含むコアライブラリを公開。

### 追加 (Added)
- パッケージ基礎
  - パッケージエントリポイントを提供（kabusys.__init__、バージョン 0.1.0）。
  - モジュール群を公開: data, research, ai, monitoring（監視系は __all__ に含むが個別実装は一部）。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local ファイル自動読み込み機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
  - .env パーサは export 付き行、クォートされた値（バックスラッシュエスケープ対応）、インラインコメントの扱いなどに対応。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルト path）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
  - 未設定の必須環境変数は ValueError を送出する明示的な挙動。

- データ（kabusys.data）
  - カレンダー管理（calendar_management.py）
    - JPX カレンダー用の market_calendar テーブル操作と営業日判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - カレンダーデータ未登録時は曜日ベース（土日非営業）でフォールバック。
    - calendar_update_job を実装。J-Quants API から差分取得し冪等的に保存（バックフィル・健全性チェック有り）。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを公開（kabusys.data.ETLResult を再エクスポート）。
    - 差分更新・バックフィル・品質チェックを想定した設計。DB の最終取得日管理、_idempotent_ な保存フローを前提に実装。
    - 内部ユーティリティ: テーブル存在確認、最大日付取得など。

- リサーチ（kabusys.research）
  - ファクター計算モジュール（factor_research.py）:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）等の算出。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等の算出。
    - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE の算出（PBR 等は未実装）。
    - 設計上、prices_daily / raw_financials のみを参照し、外部APIや発注系にはアクセスしないことを保証。
  - 特徴量探索（feature_exploration.py）:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン算出。
    - calc_ic: スピアマンランク（Information Coefficient）計算。
    - rank: 同順位は平均ランクを返す安定的なランク関数。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。
    - 依存を標準ライブラリのみで実装（pandas 等に依存しない）。

- AI（kabusys.ai）
  - ニュース NLP スコアリング（news_nlp.py）:
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとの ai_score を算出・ai_scores テーブルへ保存。
    - JST 時間ウィンドウ（前日 15:00 ～ 当日 08:30）を UTC に変換して記事を選定する calc_news_window を提供。
    - 最大銘柄バッチサイズ、1銘柄の最大記事数・最大文字数などトークン肥大化対策を実装。
    - JSON Mode を使った出力バリデーションと堅牢なパースロジック（前後テキスト混入時の {} 抽出対応）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ（ログ出力、最終失敗はスキップ）。
    - スコアは ±1.0 にクリップ。部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT で置換。
    - API キーが未設定の場合は ValueError を送出。
  - レジーム判定（regime_detector.py）:
    - ETF 1321 の 200日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定。
    - マクロセンチメントはニュースタイトル（マクロキーワードでフィルタ）を OpenAI（gpt-4o-mini）で評価して取得（JSON パース、リトライ・フォールバック実装）。
    - ルックアヘッドバイアス防止のため target_date 未満のデータのみ利用し、datetime.today() を直接参照しない。
    - API 失敗時は macro_sentiment = 0.0 としてフォールバック。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）し、DB書き込み失敗時は ROLLBACK を試みて例外を上位に伝播。

### 変更 (Changed)
- （初回リリースのため過去からの変更はなし）

### 修正 (Fixed)
- （初回リリースのため過去からの修正はなし）

### 既知の注意点 / 設計上の挙動
- OpenAI を使う機能（score_news, score_regime）は API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError。
- AI モジュールは gpt-4o-mini を想定してプロンプトと JSON Mode を利用する設計。API レスポンスのバリデーションやパース失敗時にはスキップまたは中立値での継続動作を行い、例外を上げにくい設計（フェイルセーフ）。
- DuckDB を前提に SQL クエリと executemany の制約（空リストを不可とするバージョン互換）に配慮した実装を行っている。
- ETL / カレンダー更新処理は J-Quants クライアント（kabusys.data.jquants_client）に依存。外部 API 呼び出し失敗時はログを残して処理を中断またはスキップする実装。
- カレンダー未取得時は土日ベースのフォールバックを行うため、一部の祝日情報が未取得であっても最小限の機能は動作するが正確な祝日判定のためには market_calendar の取得が必要。
- データ不足（移動平均計算用の行数不足など）は None や 1.0（中立）等の安全側の既定値で処理される箇所がある（ログ出力あり）。

### 破壊的変更 (Breaking Changes)
- 初回リリースのため該当なし。ただし今後 Settings のプロパティ名・環境変数名の変更は互換性に影響します。

### セキュリティ (Security)
- API キーやパスワード等の秘匿情報は環境変数で扱うことを推奨。.env 自動読み込みはテスト用途やローカル開発で便利だが、本番環境では OS 環境変数管理（例: Vault, CI シークレット）を推奨。

---

注: 上記はソースコードの実装内容から推測して作成した CHANGELOG です。実際のリリースノートではユーザー向けの手順、既知のバグ、互換性に関するより詳細な情報を追記してください。