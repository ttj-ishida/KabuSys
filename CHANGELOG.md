CHANGELOG
=========
すべての重要な変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。

フォーマット:
- 変更はセマンティックバージョニングに基づいたリリースごとに整理しています。
- カテゴリ: Added / Changed / Fixed / Deprecated / Removed / Security

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-03-27
-------------------
初回リリース。以下の主要機能・モジュールを実装しています。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動ロードする仕組みを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - .env パーサーは export プレフィックス・クォート・エスケープ・インラインコメント等に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベース / システム設定をプロパティ経由で取得可能。
  - 設定値の検証:
    - KABUSYS_ENV は development / paper_trading / live のみ許容。
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容。
  - デフォルト値: KABUSYS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等を用意。

- AI/NLP モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントを算出。
    - バッチ処理（最大 20 銘柄/リクエスト）・記事数/文字数トリム（最大 10 記事／3000 文字）対応。
    - Exponential backoff によるリトライ（429/ネットワーク断/タイムアウト/5xx）。
    - レスポンスの堅牢なバリデーションと数値クリップ（±1.0）。
    - 成功分のみ ai_scores テーブルへ冪等的に置換（DELETE→INSERT）、部分失敗時に既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api の patch）。
    - lookahead バイアス回避のため datetime.today()/date.today() を直接参照しない設計。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - prices_daily/raw_news を参照、結果を market_regime テーブルへ冪等書き込み。
    - マクロ記事が無ければ LLM 呼び出しをスキップ、API エラー時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - OpenAI クライアントを引数経由または環境変数で解決。テスト用に API 呼び出しを差し替え可能。

- データ基盤（kabusys.data）
  - calendar_management:
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar 未取得時は曜日ベースでフォールバック（土日を非営業日扱い）。
    - calendar_update_job: J-Quants から差分取得し market_calendar を冪等保存。バックフィル・健全性チェックを実装。
  - pipeline / ETL:
    - ETLResult データクラス（ターゲット日・取得/保存件数・品質問題・エラー集約）を公開。
    - ETL 設計における差分取得・バックフィル・品質チェックの方針をコード化（参照実装）。
  - jquants_client との連携点を想定した実装（fetch/save 呼び出しを想定）。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0/欠損なら None）。
    - 全関数は prices_daily / raw_financials のみを参照し、発注系へのアクセスは行わない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（日数）後の将来リターンを計算（デフォルト [1,5,21]）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコード < 3 の場合は None）。
    - rank: 同順位は平均ランクを返すランク変換ユーティリティ（丸めにより ties の誤差を抑制）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - pandas 等の外部依存を避け、標準ライブラリ + duckdb で実装。

- 汎用性・堅牢性
  - DuckDB を前提とした SQL ベースの集計・ウィンドウ関数利用による高効率な集計処理。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
  - API 呼び出し部分はリトライ・バックオフ・エラーハンドリングが徹底されており、フェイルセーフ（例: 中立値フォールバック）を採用。
  - ロギングを各モジュールで使用し、操作状況・警告・例外を記録。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- OpenAI API キーは引数で注入可能／環境変数 OPENAI_API_KEY からも解決するが、キーの管理は利用者側で行うこと（コード内にハードコードはなし）。
- .env の読み込みは OS 環境変数を保護する仕組み（protected set）を持ち、既存の環境変数を不用意に上書きしないデフォルト動作。

使用上の注意（実装上の重要ポイント）
- 時刻・ウィンドウの扱い:
  - news_nlp と regime_detector のニュース時間窓は UTC naive datetime を使い、JST→UTC の変換ロジックを明示。
  - ルックアヘッドバイアス回避のため、内部で date.today()/datetime.today() を直接参照しない設計。
- テスト容易性:
  - OpenAI 呼び出しポイントは内部関数で分離しており、unittest.mock.patch 等で差し替えてユニットテストが可能。
- DuckDB executemany の制約に留意（空リストの場合に注意している実装）。

今後の予定（想定）
- ETL の実行フローを統合する pipeline の公開 API 実装（ETLResult を返す処理）。
- strategy / execution / monitoring モジュールの実装拡充（現状はパッケージエントリのみを提供）。
- 追加の品質チェック・監視アラート機能の強化。

---
この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートや運用手順はリポジトリの README・ドキュメントやリリース管理ポリシーに従って調整してください。