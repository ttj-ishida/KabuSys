CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

フォーマットのルール:
- 主要な公開リリースは日付とバージョンで記載しています。
- 各項目は Added / Changed / Fixed / Security / Internal 等で分類しています。

最新
----

### 未リリース

- 現在の開発中の変更点はここに記載されます。

[0.1.0] - 2026-03-29
-------------------

初回公開リリース。日本株自動売買システム "KabuSys" の最小実装を提供します。主要な機能と設計上の注意点を以下に列挙します。

### Added
- パッケージ化
  - パッケージルート: src/kabusys/__init__.py にて __version__="0.1.0" を設定。
  - モジュール公開一覧を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local ファイルと OS 環境変数の自動読み込み機能を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env ロード。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - export KEY=val 形式やクォート／エスケープ、インラインコメントを考慮した .env パーサー実装。
  - 必須環境変数チェック（_require）と Settings クラスを提供。
  - デフォルト値: KABUSYS_ENV (development), KABUS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等。
  - 有効値バリデーション: KABUSYS_ENV は {development, paper_trading, live}、LOG_LEVEL は標準ログレベル集合。

- AI 関連（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を銘柄別に集約して OpenAI（gpt-4o-mini）でセンチメントを算出し、ai_scores に書き込む。
    - 時間窓: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
    - バッチ処理（最大 20 銘柄／バッチ）、1 銘柄あたり記事数・文字数制限あり。
    - JSON Mode を利用した厳格なレスポンス期待、レスポンス検証ロジック実装。
    - エラー耐性: 429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ、失敗チャンクはスキップし他は継続。
    - DuckDB への冪等書込み（DELETE→INSERT）で部分失敗時に既存データを保護。
    - テスト容易性: _call_openai_api をユニットテストで差し替え可能。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定・保存。
    - マクロキーワードで raw_news をフィルタし OpenAI（gpt-4o-mini）により macro_sentiment を取得。
    - LLM 呼び出しのリトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 日次判定でルックアヘッドバイアスを防ぐ設計（date 未満のデータのみ参照、datetime.today() を参照しない）。
    - テスト容易性: _call_openai_api を差し替え可能。

- Data（src/kabusys/data）
  - ETL インターフェース（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラーを含む）。
    - 差分取得・バックフィル・品質チェック・冪等保存を想定した ETL 設計。
    - DuckDB を前提とした最大日付取得／テーブル存在チェック等のユーティリティを実装。

  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定 API を提供。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job により J-Quants API から差分取得→冪等保存（バックフィル、安全性チェックあり）。
    - 最大探索日数等で無限ループ防止。

  - jquants_client や quality など外部クライアントとの連携を想定（実装は別モジュール）。

- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20 日 ATR, 相対 ATR）、Value（PER/ROE）等を DuckDB の SQL と Python で計算。
    - 各関数は prices_daily / raw_financials のみ参照し、外部 API にはアクセスしない設計。
    - データ不足時の扱い（None を返す）やログ出力・結果フォーマットを定義。

  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: スピアマン ρ）、ランク変換、統計サマリー（factor_summary）を実装。
    - pandas 等を使わず標準ライブラリのみで実装。欠損や有限性を考慮した堅牢な実装。

### Changed
- 初回リリースのため特になし（初期追加のみ）。

### Fixed
- 初回リリースのため特になし。

### Security
- 環境変数に重要なトークンを要求:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を利用する機能（news_nlp, regime_detector）は OPENAI_API_KEY を参照（関数引数で注入可）。
- .env ロード時に OS 環境変数を保護する実装（既存 OS 環境変数はデフォルトで上書きされない）。

### Notes / Design Decisions
- ルックアヘッドバイアス対策: 日付判定処理は datetime.today()/date.today() に依存しない実装を心掛け、target_date を明示的に渡す設計に統一。
- API 呼び出しは失敗時に安全側へフォールバック（例: macro_sentiment=0.0、失敗チャンクはスキップ）し、サービス全体の停止を防ぐフェイルセーフを採用。
- DuckDB を中心にデータ操作を行い、書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT 等）して部分失敗時の被害を軽減。
- テストしやすさを重視し、外部 API 呼び出し箇所（_call_openai_api 等）はユニットテストで差し替え可能に実装。

互換性 / マイグレーション
- 0.1.0 は初期公開版のため互換性ポリシーは今後のリリースで定義予定。
- 環境変数名やテーブルスキーマに依存する部分は、将来変更する際に明示的なマイグレーション手順を提供する予定。

開発者向けメモ（内部）
- OpenAI SDK のエラー型（status_code 等）に依存する処理は getattr を使い将来の SDK 変化に耐性をもたせている。
- DuckDB の executemany に空リストを渡せない制約を考慮して、空チェックを行ってから executemany を呼ぶ実装とした。

問い合わせ / 参照
- リポジトリ内の各モジュールの docstring に設計方針と使用例を記載しています。追加の仕様・バグ報告・機能要望は issue を作成してください。