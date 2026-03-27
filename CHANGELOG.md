# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
過去の互換性に関する方針はセマンティックバージョニングに従います。

即時日付: 2026-03-27

## [Unreleased]
- （未リリースの変更はここに記載）

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

### Added
- パッケージ基底
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。サブモジュールを公開: data, strategy, execution, monitoring。
  - パッケージのバージョンを `0.1.0` に設定。

- 環境設定
  - 環境変数/設定管理モジュールを実装（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env/.env.local を自動読み込み（テスト等で `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - .env パーサ実装（export 形式、引用符内のエスケープ、行内コメント対応）。
    - .env と .env.local の優先順位（OS 環境変数 > .env.local > .env）、既存 OS 環境変数を保護する仕組みを実装。
    - 必須変数取得ヘルパー `_require` と設定ラッパー `Settings` を提供（J-Quants / kabu API / Slack / DB パス / ログレベル / 環境種別等）。
    - `KABUSYS_ENV` と `LOG_LEVEL` に対する値検証（許容値チェック）を実装。
    - `duckdb_path` / `sqlite_path` の Path 型での取得および展開（~ 展開）。

- データプラットフォーム（Data）
  - ETL インターフェース（src/kabusys/data/etl.py）を追加。ETL 結果型 `ETLResult` を公開。
  - ETL パイプラインの結果クラス実装（src/kabusys/data/pipeline.py）。
    - ETL 実行結果を表す dataclass `ETLResult`（品質チェック結果やエラー集計、辞書変換ユーティリティを含む）。
    - DB テーブル存在チェックや最大日付取得等のユーティリティ実装。
    - 差分更新・バックフィル・品質チェックを想定した設計（コメントに仕様記載）。
  - 市場カレンダー管理モジュールを実装（src/kabusys/data/calendar_management.py）。
    - カレンダーデータの存在チェック、曜日ベースのフォールバック（カレンダー未取得時）を実装。
    - 営業日判定 API: is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - 夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants API から差分取得し保存、バックフィル・健全性チェックを実装）。
    - DuckDB から返る日付型処理や NULL 値の取り扱いに注意した実装。

- 研究用モジュール（Research）
  - ファクター計算ライブラリを実装（src/kabusys/research/factor_research.py）。
    - Momentum ファクター（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）、Value（PER、ROE）を計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - DuckDB SQL を用いた効率的な集計処理とデータ不足時の None ハンドリング。
  - 特徴量探索ユーティリティを実装（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）に対応、入力検証あり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関での評価、データ不足時に None を返す。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク、丸めによる ties 対応。
    - 統計サマリ（factor_summary）: count/mean/std/min/max/median を計算。
  - research パッケージの __init__ で主要 API を再公開（zscore_normalize は data.stats から参照）。

- AI / NLP
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）。
    - 指定ニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を計算する `calc_news_window`。
    - 記事の銘柄別集約（raw_news と news_symbols を結合して最新 N 記事を集約）。
    - OpenAI（gpt-4o-mini）へのバッチ送信（最大 20 銘柄/コール）、JSON Mode を使った厳格なレスポンス期待。
    - リトライ方針（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）を実装。
    - レスポンスのバリデーションと解析（JSON 抽出、results 配列検証、コード照合、数値チェック、±1.0 クリップ）。
    - ai_scores テーブルへの冪等的書き込み（対象コードを限定して DELETE → INSERT のトランザクション処理）。
    - フェイルセーフ: API 失敗時はそのチャンクをスキップして他チャンクを継続。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み合成（70% / 30%）して日次レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（target_date 未満のデータのみ使用でルックアヘッド回避）、データ不足時の中立フォールバック。
    - マクロニュース抽出（キーワードフィルタ）、LLM 呼び出し（gpt-4o-mini）と JSON パース、リトライ/バックオフ、フェイルセーフ（API失敗時 macro_sentiment=0.0）。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）とエラーハンドリング（ROLLBACK 保護）。
    - LLM 呼び出し関数は別モジュールと共有しない形で独立実装（テスト時に差し替え可能）。

- 汎用/ユーティリティ
  - OpenAI クライアント呼び出しラッパーを各 AI モジュール内に実装し、テストで patch 可能に設計（_call_openai_api）。
  - DuckDB 接続を前提にした SQL ベースの集計・算出処理の多用。部分失敗時に既存データを守るためのトランザクションと限定 DELETE/INSERT ロジックを採用。
  - エラーロギングと詳細な logger メッセージを各モジュールに追加（運用時の可観測性を強化）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 現時点で公開すべきセキュリティ修正はありません。
- 注意: OpenAI API キーや各種シークレットは環境変数で管理する想定。.env 自動読み込みの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。

---

注記:
- 本リリースはソースコードから仕様を推測して作成した changelog です。実際のリリースノートとして用いる場合は、実装意図や運用方針に応じて日付・内容を調整してください。