# Changelog

すべての変更は「Keep a Changelog」フォーマットに準拠しています。  
このファイルはコードベース（初回公開相当）の状態から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース（推定）。主に日本株のデータプラットフォーム・リサーチ・AI解析・運用ユーティリティを含むモジュール群を導入。

### Added
- パッケージ基盤
  - パッケージメタ情報（kabusys.__init__）を導入し、バージョンを 0.1.0 に設定。
  - __all__ に主要サブパッケージ（data, research, ai, etc.）を公開。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを実装。
  - export KEY=val 形式・クォート・インラインコメントなどに対応する行パーサを実装。
  - OS 環境変数を保護する protected 機能、上書きフラグ（override）をサポート。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定（env, log_level）などのプロパティを環境変数から取得。入力検証（有効な env/log level）やパス→Path 変換を含む。

- AI（自然言語処理）関連（kabusys.ai）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードで銘柄別のセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（1回あたり最大20銘柄）、1銘柄あたりの最大記事数・文字数トリム、レスポンス検証、スコアの ±1.0 クリップを実装。
    - 429・ネットワーク断・タイムアウト・5xx を対象とした指数バックオフによるリトライ実装。API エラー時はフェイルセーフ（該当チャンクはスキップ）。
    - DuckDB に対する冪等書き込み（DELETE → INSERT）を採用し、部分失敗時に既存データを保護。DuckDB executemany の空リスト問題に対処。
    - calc_news_window ユーティリティ（JSTベースのウィンドウ計算：前日15:00〜当日08:30）を提供。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等保存。
    - news_nlp と同様に OpenAI（gpt-4o-mini）を使用。API 呼び出しは独立実装でモジュール間の結合を避ける設計。
    - データ不足や API 失敗時はフェイルセーフ（ma200_ratio=1.0, macro_sentiment=0.0）で処理を継続。
    - OpenAI 呼び出しに対するリトライ、JSON パース保護、ロギングを実装。

- データプラットフォーム（kabusys.data）
  - ETL 基盤（kabusys.data.pipeline）
    - ETLResult dataclass による ETL 結果管理（取得件数・保存件数・品質問題・エラーリストなど）。
    - 差分更新・バックフィル概念・品質チェックフローの実装方針を反映。
    - DuckDB を前提としたテーブル存在チェック、最大日付取得等のユーティリティを提供（pipeline 内）。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダーを扱うユーティリティを実装（market_calendar を想定）。
    - 営業日判定（is_trading_day）、SQ日判定（is_sq_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）を提供。
    - DB 登録値を優先しつつ未登録日は曜日ベースのフォールバック（週末除外）で一貫性を確保。
    - calendar_update_job により J-Quants API から差分取得→冪等保存（fetch/save は jquants_client に委譲）、バックフィル・健全性チェックを実装。
  - jquants_client を介した外部 API 連携を想定（fetch/save 関数の呼び出し箇所あり）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（calc_momentum）：1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - ボラティリティ/流動性（calc_volatility）：20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - バリュー（calc_value）：raw_financials から EPS/ROE を取得し PER / ROE を計算。
    - DuckDB + SQL ウィンドウ関数を活用した実装。データ不足時は None を返す設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン（calc_forward_returns）：LEAD を用いて複数ホライズンのリターンを一括取得。horizons の入力検証あり。
    - IC（calc_ic）：Spearman（ランク相関）による Information Coefficient 計算。必要件数が不足すると None を返す。
    - ランク変換ユーティリティ（rank）：同順位は平均ランクを返す（丸め対策あり）。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median の計算を提供。
  - これらは prices_daily / raw_financials 等のテーブルのみ参照し、発注系 API へはアクセスしない設計。

### Changed
- （初回リリースのため該当なし）ただし設計方針として以下が明記されている：
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない実装方針を採用。
  - DuckDB のバージョン差異（executemany の空リスト等）を考慮した保護実装。

### Fixed
- （初回リリースのため該当なし）ただし堅牢性に関する多くの保護（例外捕捉、ROLLBACK の安全確保、フェイルセーフデフォルト等）を組み込んでいる。

### Security
- API キー（OPENAI_API_KEY 等）は環境変数から取得する設計。欠如時は明示的に例外を送出する箇所あり（利用者が鍵を管理することを前提）。
- .env 自動読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により明示的に無効化可能（テストやCI用途を想定）。

### Known limitations / Notes
- OpenAI 呼び出しは gpt-4o-mini（JSON Mode）を前提としているため、API 仕様変更やモデル利用可否に依存する。
- DuckDB のバージョン差異に影響を受ける箇所（list バインドや executemany の挙動）に考慮した実装をしているが、実運用時はターゲット環境での検証が推奨される。
- news_nlp / regime_detector は LLM レスポンスの冗長テキストや不正JSONに対する復元ロジックを含むが、誤解析/スコアのばらつきは想定される。
- calendar_update_job は jquants_client.fetch_market_calendar / save_market_calendar の実装に依存する。

---

（注）この CHANGELOG は提供されたソースコードからの推定に基づいて作成しています。実際のリリースノートには開発履歴・コミットログ・変更日付を反映してください。