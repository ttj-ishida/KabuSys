# Changelog

すべての注目すべき変更をこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣例に従います。

## [Unreleased]

（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-04-01

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。
主にデータ取得・ETL・カレンダー管理・ファクター計算・AI ベースのニュース解析と市場レジーム判定を含みます。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加 (`src/kabusys/__init__.py`, version = 0.1.0)。
  - モジュールエクスポート: data, strategy, execution, monitoring。

- 環境設定管理 (`src/kabusys/config.py`)
  - .env ファイルまたは OS 環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に自動でプロジェクトルートを探索して .env を読み込む。
  - 自動ロードの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサーの実装: `export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを考慮した堅牢なパース処理。
  - 必須変数取得ヘルパ `_require` と環境値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。
  - 各種設定プロパティ（J-Quants / kabu API / Slack / DB パス / 監視閾値 等）を提供。

- AI モジュール
  - ニュース NLP (`src/kabusys/ai/news_nlp.py`)
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメントスコアを算出する `score_news` を実装。
    - JST ベースのニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する `calc_news_window` を実装。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄当たりの記事数・文字数制限（上限あり）、レスポンス検証、スコアの ±1.0 クリップ。
    - 再試行・指数バックオフ（429 / ネットワーク断 / タイムアウト / 5xx を対象）、エラーはフェイルセーフでスキップし処理継続。
    - テスト容易化のため OpenAI 呼び出し箇所を差し替え可能（unit test 用に _call_openai_api をモック可）。

  - 市場レジーム判定 (`src/kabusys/ai/regime_detector.py`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成し日次で市場レジームを判定する `score_regime` を実装。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini、JSON Mode）、API 再試行・フェイルセーフ（失敗時 macro_sentiment=0.0）、およびレジームスコアのクリップとラベリング（bull/neutral/bear）。
    - DuckDB への冪等書込み（BEGIN / DELETE / INSERT / COMMIT）とエラー時の ROLLBACK ロギング。

- リサーチ / ファクター計算 (`src/kabusys/research/`)
  - ファクター計算モジュール `factor_research.py` を追加:
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（`calc_momentum`）。
    - ボラティリティ / 流動性: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率（`calc_volatility`）。
    - バリュー: 最新の raw_financials と価格から PER / ROE を算出（`calc_value`）。
    - DuckDB の prices_daily / raw_financials を参照する SQL ベースの実装。
  - 特徴量探索モジュール `feature_exploration.py` を追加:
    - 将来リターン計算 (`calc_forward_returns`)、IC（スピアマン ρ）計算 (`calc_ic`)、ランク変換 (`rank`)、統計要約 (`factor_summary`) を実装。
    - 外部依存なし（標準ライブラリのみ）、遅延ルックアヘッドを防ぐ設計。
  - 研究ユーティリティの再エクスポート（`__init__.py`）: zscore_normalize の再エクスポート等。

- データプラットフォーム (`src/kabusys/data/`)
  - マーケットカレンダー管理 (`calendar_management.py`)
    - JPX カレンダー同期バッチ (`calendar_update_job`) とカレンダーに基づく営業日判定ユーティリティ（`is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`）を実装。
    - DB 未取得時は曜日ベースのフォールバック（週末は非営業日）を提供し、DB 登録値を優先するロジック。
    - 探索上限 (_MAX_SEARCH_DAYS) 等による安全策、バックフィル・健全性チェックを実装。
  - ETL パイプライン (`pipeline.py`, `etl.py`)
    - ETL 実行結果を表す dataclass `ETLResult` を実装し、公開インターフェースとして再エクスポート（`etl.py`）。
    - 差分取得・保存・品質チェックの設計に対応するユーティリティ関数群（詳細実装は jquants_client / quality モジュールと連携する想定）。
    - ETLResult に品質問題とエラーの集約、has_errors / has_quality_errors / to_dict を提供。

### Changed
- 設計/実装方針の明記（コード内ドキュメント）
  - 各モジュールで「ルックアヘッドバイアス防止」のため date.today()/datetime.today() を直接参照しない旨を明記し、対象日引数ベースの計算を徹底。
  - AI 呼び出しとレスポンス検証の設計で、外部 API 失敗時に処理を継続するフェイルセーフ方針を統一。

### Fixed
- トランザクション安全性とロールバック
  - DuckDB への書き込み (market_regime / ai_scores 等) で BEGIN / DELETE / INSERT / COMMIT を用い、例外時に ROLLBACK を試行して失敗ログを出力する実装により部分失敗時のデータ保護を強化。

### Internal / Implementation notes
- OpenAI SDK の利用
  - gpt-4o-mini を使用し、JSON Mode（response_format={"type":"json_object"}）での応答を前提としたパース処理を実装。
  - SDK 例外型（RateLimitError, APIConnectionError, APITimeoutError, APIError 等）を考慮したリトライロジックを実装。
  - レスポンスパース失敗や想定外のキー欠落はログ警告し、安全にフォールバック。

- テストのしやすさ
  - AI 呼び出し箇所（_call_openai_api）をモジュール内で明示的に分離し、ユニットテスト時にモックで置換しやすい設計。

- SQL / DuckDB 互換性配慮
  - executemany に空リストを渡さないチェック（DuckDB 0.10 の制約）や、ROW_NUMBER / WINDOW 関数の使用で互換性を保つ実装。

### Removed
- （該当なし）

### Security
- 外部 API キーは引数で注入可能（api_key 引数）か環境変数（OPENAI_API_KEY）から取得する方式で、API キー未設定時は ValueError を送出して明示的に失敗させる実装。

---

注: 本 CHANGELOG はコードベースの内容から機能・振る舞いを推測して作成しています。実際の変更履歴・リリースノートはリポジトリのコミット履歴やリリース管理情報に基づいて正式に作成してください。