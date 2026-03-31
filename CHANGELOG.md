# Changelog

すべての変更は Keep a Changelog の慣例に従い記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-31

初期リリース。本パッケージは日本株自動売買・データ基盤・リサーチ・AI支援のユーティリティ群を含みます。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ初期構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルと OS 環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーは以下の挙動に対応：
    - コメント行/空行の無視、`export KEY=val` 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなし値の行内コメント（直前が空白/タブの `#`）を扱う。
  - 認証情報や設定用プロパティを持つ Settings クラスを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - ログレベル・環境（development / paper_trading / live）向けのバリデーションを実装。
  - データベースパスの既定値（DuckDB / SQLite）を用意。

- AI モジュール（src/kabusys/ai）
  - ニュースNLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini、JSON mode）で銘柄ごとのセンチメントスコアを算出して ai_scores テーブルへ保存する機能 score_news を実装。
    - タイムウィンドウ計算（JST ベース）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄 / チャンク）、記事数/文字数トリミング、レスポンス検証、スコア ±1.0 クリップなどのロジックを含む。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフでのリトライを実装。フェイルセーフ設計により API 失敗時は個別チャンクをスキップして継続。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - raw_news からマクロキーワードでフィルタリングし、OpenAI に JSON 出力を要求して macro_sentiment を取得。
    - API 呼び出しに対するリトライ・エラーハンドリング、LLM 失敗時のマクロセンチメント 0.0 フォールバック、結果のクリップとテーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - ルックアヘッドバイアスを避ける設計（date 引数ベース、DB クエリは target_date 未満限定）。

- Data（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーを管理する市場カレンダーヘルパーを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB の market_calendar を優先し、未登録日は曜日ベースでフォールバック（週末は非営業日）。
    - カレンダー夜間更新 job（calendar_update_job）を実装し、J-Quants クライアントから差分取得 → 保存（ON CONFLICT 相当）を行う。バックフィルと健全性チェックを含む。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult dataclass を公開（取得件数、保存件数、品質問題、エラー概況を保持）。
    - 差分取得、保存（idempotent）、品質チェックの設計方針と内部ユーティリティを実装（テーブル存在チェック、最大日付取得、安全な日付調整等）。
    - デフォルトのバックフィル日数やカレンダー先読み等の定数を定義。

- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER/ROE）などの計算関数 calc_momentum, calc_volatility, calc_value を実装。
    - DuckDB 上で SQL/ウィンドウ関数を用いて計算、データ不足時の None ハンドリング。
    - 設計上、本番注文 API へはアクセスしない（読み取り専用・再現可能）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、統計サマリー（factor_summary）、ランク変換（rank）を提供。
    - 外部依存を用いず標準ライブラリのみで実装。ランクは同順位を平均ランクで処理。

- その他ユーティリティ
  - data/etl.py は pipeline.ETLResult を再エクスポート。
  - research パッケージは data.stats の zscore_normalize を再エクスポート。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入でき、未設定時は明示的な ValueError を発生させる。  
- 環境変数自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

注記・設計上の重要ポイント
- DuckDB を主要なローカルデータストアとして利用。クエリは日付の取り扱いに注意してルックアヘッドを防止する設計。
- OpenAI 呼び出しは JSON mode（response_format={"type": "json_object"}）を利用し、レスポンスの厳密な検証とフォールバック（0.0 やスキップ）を行うことでパイプラインのロバスト性を確保。
- DB 書き込みは冪等性を重視（DELETE → INSERT のパターン、トランザクション + ROLLBACK 対応）。
- テスト容易性のため外部 API 呼び出しを差し替え可能（内部 _call_openai_api を unittest.mock.patch でモック可能）。
- 日付はすべて datetime.date / naive datetime で扱い、タイムゾーン混入を避ける方針。

もしCHANGELOGに追加したいより詳細な項目（例えば各モジュール内の定数や閾値、API の具体的なパラメータ、期待する DB スキーマ等）があれば、その情報を元に項目を細分化して更新します。