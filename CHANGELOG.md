# Changelog

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。

### Added
- パッケージ基盤
  - パッケージ名 kabusys とバージョン情報を追加（__version__ = 0.1.0）。
  - パッケージAPIの公開モジュール一覧を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定
  - 環境変数管理モジュールを追加（kabusys.config）。
    - プロジェクトルート検出機能: .git または pyproject.toml を起点に自動検出し、カレントワーキングディレクトリに依存しない読み込みを実現。
    - .env/.env.local 自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パーサ実装: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応。
    - _require ユーティリティで必須環境変数未設定時に分かりやすいエラーメッセージを送出。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル等の設定プロパティを個別に取得可能に（既定値やバリデーションあり）。
    - KABUSYS_ENV の許容値検証（development / paper_trading / live）および LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - デフォルトのデータベースパス: duckdb -> data/kabusys.duckdb、sqlite -> data/monitoring.db。

- AI（NLP）モジュール
  - ニュースセンチメント分析（kabusys.ai.news_nlp）を実装。
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを統合して OpenAI（gpt-4o-mini）へバッチ送信してスコアを算出。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供（UTC naive datetime を返す）。
    - バッチサイズ、トークン肥大対策、最大記事数、最大文字数などの制限を設定（_BATCH_SIZE=20, _MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - JSON Mode レスポンスのバリデーション（results 配列、code/score の整合性、スコアの数値変換、既知コードのみ採用）。
    - レート制限・ネットワーク断・タイムアウト・5xx の際の指数バックオフによるリトライ実装（最大リトライ回数・ログ出力・フェイルセーフでのスキップ）。
    - DuckDB 互換性考慮: executemany に空リストを渡さない安全処理、DELETE→INSERT の置換方式により部分失敗時に他コードの既存スコアを保護。
    - パブリック関数 score_news(conn, target_date, api_key=None) を提供（OpenAI APIキーは引数または環境変数 OPENAI_API_KEY で解決）。

  - 市場レジーム判定（kabusys.ai.regime_detector）を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime テーブルへ冪等書き込み。
    - マクロキーワードに基づく raw_news タイトル抽出（最大 _MAX_MACRO_ARTICLES=20）。
    - OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント評価。API エラー時は macro_sentiment=0.0 とするフェイルセーフ。
    - レジームスコアの閾値により 'bull' / 'neutral' / 'bear' を判定。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT による冪等実装とエラー時の ROLLBACK を伴う。

- データプラットフォーム（DuckDB 側ユーティリティ）
  - カレンダー管理モジュール（kabusys.data.calendar_management）を追加。
    - market_calendar テーブルを基に営業日判定・前後営業日取得・期間内営業日列挙・SQ日判定等のユーティリティを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未取得時は曜日ベース（週末除外）のフォールバックを提供。
    - カレンダー夜間バッチ更新ジョブ calendar_update_job(conn, lookahead_days=90) を実装。J-Quants クライアントから差分取得後に冪等保存を行う。バックフィル、健全性チェックを備える。
    - market_calendar の存在チェック等の内部ユーティリティを実装。

  - ETL パイプライン基盤（kabusys.data.pipeline）を追加。
    - ETLResult dataclass を提供し、取得件数・保存件数・品質問題・エラー概要を一元管理。
    - 差分取得、バックフィル、品質チェックとの統合を想定した設計（品質問題は収集して呼び出し元で対処）。
    - _get_max_date 等の DB ヘルパーを実装。

  - etl モジュールで ETLResult を再エクスポート（kabusys.data.etl）。

- リサーチ機能
  - ファクター計算モジュール（kabusys.research.factor_research）を追加。
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR/相対ATR、出来高/売買代金関連などを DuckDB クエリで計算する関数を提供（calc_momentum / calc_volatility / calc_value）。
    - 仕様に合わせた窓サイズ・スキャン範囲・欠損ハンドリング（行数不足時は None）を実装。

  - 特徴量探索モジュール（kabusys.research.feature_exploration）を追加。
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンに対応、入力検証あり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマン（ランク相関）実装、データ不足時の None 返却。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク、丸めで ties の誤差を防止。
    - 統計サマリー（factor_summary）: count / mean / std / min / max / median を標準ライブラリのみで計算。
    - research パッケージの __all__ に主要 API を公開。

- 内部設計方針（全体）
  - ルックアヘッドバイアス防止のため、関数内部で datetime.today() / date.today() を参照せず target_date を明示的に受け取る設計を採用。
  - 外部発注 API へのアクセスはリサーチ関連コードで行わない（分析系は完全に読み取り専用）。
  - OpenAI 呼び出しはテストで差し替え可能な小関数化（_call_openai_api）を行い、モジュール間でプライベート関数を共有しない設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env 自動読み込み時、既存の OS 環境変数を保護するため protected セットを利用して .env.local/.env による上書きを制御。
- 必須トークン系（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）は Settings のプロパティ経由で取得し、未設定時は明示的な例外を投げて早期検出。

### Notes / Implementation details
- OpenAI 関連
  - 使用モデル: gpt-4o-mini（両モジュールで統一）。
  - JSON Mode を使用した厳密な JSON 出力期待（パース失敗時は復元処理を試みるが、失敗時はフェイルセーフでスコア 0 / スキップ）。
  - リトライ方針: RateLimit / 接続エラー / タイムアウト / 5xx に対して指数バックオフでリトライ。その他のエラーは基本的にスキップして継続する（サービスのロバスト性重視）。

- DuckDB 関連
  - 一部 DuckDB のバージョン差異（executemany の空リストバインド等）を回避するための防御的実装あり。
  - DB への書き込みは可能な限り冪等操作（DELETE → INSERT / ON CONFLICT 相当）で実施。

- 時刻・タイムゾーン
  - ニュースウィンドウなどは JST を基準に定義し、DB 内は UTC naive datetime を扱う前提で変換して比較する実装。

- テスト支援
  - OpenAI 呼び出しやスリープ関数を差し替え可能なように設計されており、ユニットテストでのモックが容易。

---
今後のリリースでは、strategy / execution / monitoring などの取引実行周りや、より詳細な品質チェック・メトリクス収集、API クライアントの改善などを順次追加する予定です。