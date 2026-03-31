# Keep a Changelog
すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
このファイルはコードベースの現状（ソースから推測）を元に作成しています。

## [Unreleased]
- 現時点で未リリースの変更はありません（このCHANGELOGはリポジトリのスナップショットに基づき生成されています）。

## [0.1.0] - 2026-03-31
最初の公開リリース（初期実装）。以下はこのバージョンで導入された主な機能・改善点・既知の挙動に関する要約です。

### Added
- パッケージ基盤
  - kabusys パッケージの基本エントリポイントを追加（src/kabusys/__init__.py）。公開 API として data, strategy, execution, monitoring を想定。

- 設定管理
  - 環境変数/.env ロード機能を提供する設定モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパースは export プレフィックス、クォート／エスケープ、インラインコメント（スペース前の #）に対応。
    - OS 環境変数を保護する protected 機構（.env.local による上書きや OS 変数の保護を考慮）。
    - 設定アクセス用の Settings クラスを提供（J-Quants・kabu API・Slack・DB パス・監視閾値・環境判定・ログレベル等のプロパティ）。
    - 値のバリデーション（KABUSYS_ENV、LOG_LEVEL 等）と必須環境変数の明示的エラー（_require）を実装。

- データプラットフォーム（DuckDB ベース）
  - データ ETL 用の成果物クラス（ETLResult）と pipeline/etl インターフェースを追加（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）。
    - ETLResult により取得件数・保存件数・品質チェック結果・エラーを構造化して報告可能。
    - ETL モジュールは差分取得、バックフィル、品質チェック、id_token 注入を考慮した設計。
  - マーケットカレンダー管理モジュールを追加（src/kabusys/data/calendar_management.py）。
    - market_calendar テーブルを用いた営業日判定（is_trading_day）、前後営業日計算（next_trading_day / prev_trading_day）、期間内営業日一覧取得（get_trading_days）、SQ判定（is_sq_day）を実装。
    - J-Quants API 経由での夜間バッチ更新 job（calendar_update_job）を実装。バックフィル、健全性チェック、差分フェッチをサポート。
    - DB データが不十分な場合は曜日ベースのフォールバック（週末は非営業日扱い）を一貫して使用。

- 研究（Research）モジュール
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M リターン、200 日移動平均乖離）、Volatility（20 日 ATR / ATR% / 20 日平均売買代金 / 出来高比率）、Value（PER / ROE）を DuckDB クエリで計算する関数を実装。
    - データ不足時に None を返すなど安全な挙動。
  - 特徴量探索・統計モジュールを追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（calc_forward_returns、任意 horizon 対応／入力検証）。
    - IC（Information Coefficient）計算（スピアマンランク相関を実装）。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を提供。
  - research パッケージの公開 API を整備（__init__.py）して主要関数を再エクスポート。

- AI モジュール（OpenAI 統合）
  - ニュース NLP（ニュースセンチメント）スコアリングモジュールを追加（src/kabusys/ai/news_nlp.py）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode にバッチ送信して銘柄ごとの sentiment / ai_score を ai_scores テーブルに保存。
    - バッチサイズ、最大記事数、文字トリム、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスの堅牢なバリデーション（JSON 抽出・results 構造検証・スコア型チェック）を実装。
    - DuckDB の executemany の制約を考慮した挙動（空リストは実行しない）と部分書き換え戦略（対象コードのみ DELETE → INSERT）。
    - テスト用に _call_openai_api を patch できるように設計。
  - 市場レジーム判定モジュールを追加（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース（news_nlp の窓集約から取得するマクロ記事）に対する LLM 評価（重み 30%）を合成して日次の market_regime テーブルへ冪等的に書き込み。
    - LLM 呼び出しは専用関数を持ち、失敗時は macro_sentiment=0.0 でフォールバックするなどフェイルセーフを実装。
    - OpenAI クライアント生成時に api_key を引数で注入可能（環境変数 OPENAI_API_KEY も利用可）。
  - ai パッケージ公開 API を整理（src/kabusys/ai/__init__.py）。

### Changed
- 初期リリースのため該当なし（新規追加が中心）。

### Fixed
- .env パーサの堅牢化（src/kabusys/config.py）
  - export プレフィックス対応、クォート内エスケープ処理、インラインコメントの適切な扱い、無効行スキップなど。
  - .env 読み込み失敗時は warnings.warn を出して処理を継続。

- OpenAI 統合の堅牢化（src/kabusys/ai/news_nlp.py / regime_detector.py）
  - レート制限・接続エラー・タイムアウト・5xx に対するリトライとログ出力。
  - JSON モードでも余計な前後テキストが混ざる場合に最外側の {} を抽出して復元するフェールトーチを実装。
  - レスポンスのスキーマバリデーションにより不正な出力はスキップして他コードに影響を与えないようにした。

### Security
- 環境変数取り扱いにおいて OS 環境変数を保護する設計を導入（.env の上書きを制御）。
- OpenAI API キー・Slack トークン等機密情報は Settings を通じて環境変数経由で取得する設計。必須の場合は未設定で ValueError を送出して早期検出。

### Notes / Known limitations
- OpenAI API を利用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）の設定が必須。未設定時は ValueError が発生する。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）が前提となる。初期起動前にスキーマ/テーブル準備が必要。
- 日付取り扱いにおいてルックアヘッドバイアス回避方針を採用（date.today() を直接参照せず、target_date を明示的に指定する API を採用）。
- 一部 SQL バインドや DuckDB のバージョン挙動に依存する箇所があり（例: executemany の空リスト扱い）、互換性のある呼び出し方を想定。
- news_nlp のレスポンスは厳密な JSON を期待しているが、LLM の出力バリエーションを考慮した復元処理を入れている。完全には全ケースを保証しない。

---

（注）この CHANGELOG は与えられたソースコードの内容から機能・設計方針を推測して作成しています。実際のリリース履歴や過去の変更履歴が別途存在する場合、本ファイルはそれらを反映していません。必要であれば、さらに過去のコミット履歴やリリースノートを参照して詳細化できます。