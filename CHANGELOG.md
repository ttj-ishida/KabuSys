# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルは、コードベースのスナップショット（初期リリース相当）から推測して記載した変更履歴です。

## [0.1.0] - 2026-03-27

### 追加 (Added)
- 初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装。
- パッケージ公開メタ情報
  - パッケージトップでのバージョン管理を追加（kabusys.__version__ = "0.1.0"）。
  - パブリック API として data / strategy / execution / monitoring をエクスポート準備。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み（無効化用に KABUSYS_DISABLE_AUTO_ENV_LOAD を用意）。
  - .env パーサを実装：
    - export KEY=val 形式対応、クォート（' "）内のエスケープ処理、インラインコメント処理を考慮。
  - .env 読み込み時の保護（OS 環境変数を protected として上書き防止）と override 制御。
  - Settings クラスを実装し、アプリケーション設定をプロパティで提供。
    - 必須設定の検証（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）。
    - デフォルト値や型変換（KABUSYS_ENV, LOG_LEVEL の検証、DuckDB/SQLite のパス設定）を提供。
    - 環境（is_live / is_paper / is_dev）ユーティリティ。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を用いた銘柄ごとのニュース集約ロジック。
    - タイムウィンドウ計算（JST 基準で前日 15:00 ～ 当日 08:30 に対応）と calc_news_window を提供。
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチ解析（チャンクサイズ _BATCH_SIZE=20）。
    - 1 銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトークン肥大化を防止。
    - API 呼び出しのリトライ・バックオフ（429, ネットワーク断, タイムアウト, 5xx を対象）と失敗時フォールバック（スコア取得失敗はスキップ）。
    - レスポンスのバリデーションとスコアの ±1.0 クリップ。結果を ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出。
    - マクロ記事抽出、LLM 呼び出し（gpt-4o-mini）、レスポンス JSON パース、スコア合成、market_regime への冪等書き込みを実装。
    - API 失敗時は macro_sentiment=0.0 としてフェイルセーフに継続。
    - OpenAI クライアント生成時は api_key を引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理ロジック（market_calendar）を提供。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。DB 登録値優先、未登録日は曜日ベースでフォールバック。
    - calendar_update_job を提供し、J-Quants API から差分取得→market_calendar へ冪等保存（fetch/save は jquants_client 経由）。バックフィルと健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー情報の集約）。
    - 差分更新、バックフィル、品質チェック統合、idempotent な保存フロー（ON CONFLICT/DELETE→INSERT 戦略）に基づく設計方針を実装。
    - DuckDB 互換性（executemany の空リスト禁止等）への注意点をコード中に明記。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER / ROE 取得）を DuckDB SQL で計算して返す。
    - データ不足時は None を返す等の堅牢な扱い。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic：Spearman のランク相関）、rank、factor_summary（基本統計量）を実装。
    - 外部ライブラリに依存せず、純粋に SQL と標準ライブラリで実装。

- 共通設計方針／運用上の配慮
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を内部処理で直接参照しない（target_date を引数で受け取る）。
  - DB 書き込みは冪等性を意識（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK の利用）。
  - OpenAI 呼び出しのリトライ/バックオフやレスポンスパース失敗のフェイルセーフ処理を充実。
  - テスト容易性（内部 _call_openai_api の差し替えポイント等）。

### 変更 (Changed)
- （初回リリースのため履歴なし）

### 修正 (Fixed)
- （初回リリースのため履歴なし）

### 削除 (Removed)
- （初回リリースのため履歴なし）

### セキュリティ (Security)
- （初回リリースのため該当なし）

### 備考 / 注意事項
- 必要な外部依存:
  - openai（OpenAI SDK）、duckdb が必要。jquants_client 等外部クライアントモジュールを利用する箇所がある（実装ファイルに依存）。
- 環境変数の例（必須）:
  - OPENAI_API_KEY（AI 機能利用時）、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 未実装／将来的拡張の余地:
  - Value ファクターの PBR・配当利回りは未実装（コード内に注記あり）。
  - jquants_client の具現化（外部 API クライアント実装）や strategy / execution / monitoring モジュールの機能追加は今後の課題。

(この CHANGELOG はコードの内容から推測して作成しています。実際のコミット履歴やリリースノートがある場合は、それに合わせて更新してください。)