# Changelog

すべての注目すべき変更点をここに記載します。本ファイルは Keep a Changelog の形式に準拠します。  
リリース日付はソースコードの最終更新（本ファイル作成時点）を基にしています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed / Security: 必要に応じて記載

## [Unreleased]
- 開発中の追加/改善点や今後の作業候補をここに記載します（現時点ではなし）。

---

## [0.1.0] - 2026-04-01

初回公開リリース。本リポジトリは日本株のデータ取得・ETL・研究用ファクター計算・AIベースのニュースセンチメント評価・市場レジーム判定など、データプラットフォームと簡易自動売買補助を目的としたユーティリティ群を提供します。

### Added
- パッケージ基盤
  - パッケージのメタ情報 (src/kabusys/__init__.py) を追加。エクスポート対象モジュール: data, strategy, execution, monitoring。バージョンは `0.1.0`。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - ロード優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルート検出: 現在ファイル位置から .git または pyproject.toml を探索（CWD 非依存）。
    - 自動ロードの無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で可能。
  - .env パーサーは export 文・クォート・エスケープ・インラインコメント等に対応。
  - Settings クラスを提供し、アプリ用の主要設定値をプロパティ経由で取得（必須キーは未設定時に ValueError を送出）。
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境判定・ログレベル検証等をサポート。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値チェック）。

- AI 関連 (src/kabusys/ai/)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）、1 銘柄あたり最大記事数 10、本文字数上限 3000 文字でトリム。
    - JSON Mode を利用した厳密な JSON 出力を想定。レスポンスのバリデーション機能を実装（results 配列 / code, score 等）。
    - エラー耐性: レート制限・ネットワーク断・タイムアウト・5xx をエクスポネンシャルバックオフでリトライ。非再試行エラーはスキップして継続。
    - スコアは ±1.0 にクリップして保存。
    - テスト容易化のため API 呼び出しラッパー（_call_openai_api）の差し替えを想定。
    - calc_news_window(target_date) により JST ベースのニュース収集ウィンドウを計算（前日15:00〜当日08:30 JST 相当）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news からキーワードフィルタで抽出（最大 20 件）し、OpenAI で -1.0〜1.0 の JSON スコアを取得。
    - LLM 呼び出しは retry/backoff を持ち、最終的に失敗した場合は macro_sentiment=0.0 として安全に続行。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。

- データプラットフォーム (src/kabusys/data/)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの夜間更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し market_calendar テーブルへ冪等保存。
    - 営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB データがない場合は曜日（週末）ベースのフォールバックを行う設計。
    - 探索範囲上限・バックフィル・健全性チェックを備える。
  - ETL / パイプライン用ユーティリティ (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を公開（ETL 実行結果の構造化）。
    - 差分取得・保存（jquants_client 経由の idempotent 保存）・品質チェック（quality モジュール）を行うパイプライン設計（実装の骨子）。
    - バックフィル・最小データ日・品質エラーの扱い方針を明文化。

- リサーチ（ファクター計算・特徴量探索） (src/kabusys/research/)
  - factor_research.py
    - Momentum, Value, Volatility, Liquidity 等の定量ファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、ma200 の乖離（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - calc_value: raw_financials から最新財務データを取り出し PER / ROE を計算。
    - すべて DuckDB の SQL を活用して計算（外部 API へは接続しない）。
  - feature_exploration.py
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）での将来リターン計算。
    - calc_ic: スピアマンランク相関（IC）を実装（重複/None を排除、十分サンプルがなければ None を返す）。
    - rank: 同順位を平均ランクで扱うランク化ユーティリティ。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算する集約関数。
  - research パッケージ初期エクスポートを整備。

### Changed
- 設計方針の明文化（コード内 docstring に記載）
  - ルックアヘッドバイアス防止のため、各種処理は datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
  - DB 書き込みは可能な限り冪等に（DELETE→INSERT 等）し、部分失敗時に既存データを保護する意図を反映。

### Fixed
- エラー耐性強化
  - OpenAI / ネットワーク系のエラーに対してリトライ/フォールバック（macro_sentiment=0.0 やスキップ）を実装し、全体処理の停止を避ける設計に調整。

### Notes / Known issues
- src/kabusys/data/pipeline.py の末尾に実装途上の箇所があり、関数 _get_max_date の最後の return に "date.fro" のような不完全なコード断片が含まれています（ファイルの末尾が切れている/タイプミス）。運用前に該当箇所の修正が必要です。
- strategy / execution / monitoring モジュールはパッケージ __all__ に含まれますが、今回提供されたスナップショットでは具体的な実装ファイルが含まれていません（外部で別途実装予定の可能性）。本 CHANGELOG の対象は提供されたコードベースに基づき作成しています。
- OpenAI API 利用部分は実行時に有効な OPENAI_API_KEY が必要。テスト時は _call_openai_api をモックすることを想定。

---

著者: ソースコードの docstring と実装から推測して作成しました。追加の履歴や過去バージョンの差分があれば、それに合わせて本 CHANGELOG を更新してください。