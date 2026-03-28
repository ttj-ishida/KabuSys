# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
本プロジェクトの初回リリース (0.1.0) の内容をコードベースから推測して日本語でまとめています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28

### Added
- パッケージ基盤
  - パッケージ基本情報を追加（kabusys.__init__、バージョン = 0.1.0）。
  - パッケージの公開 API に `data`, `strategy`, `execution`, `monitoring` を定義。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local ファイルと OS 環境変数から設定を自動ロードする仕組みを実装。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - プロジェクトルート探索は __file__ を基点に `.git` または `pyproject.toml` を探索して決定（CWD に依存しない）。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - 環境変数取得ユーティリティ `Settings` を追加。
    - J-Quants / kabu API / Slack / DB パス等の専用プロパティを提供（必須項目は未設定時に ValueError を送出）。
    - `KABUSYS_ENV`（development / paper_trading / live）と `LOG_LEVEL` のバリデーションを実装。
    - DB パスは Path オブジェクトで展開（デフォルトは data/ 以下）。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダー管理ロジックを実装（market_calendar テーブル参照）。
    - 営業日判定ユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB データが不完全な場合の曜日ベースのフォールバック、最大探索日数制限、バックフィル・サニティチェック、日付の安全な扱い（date オブジェクト）を実装。
    - 夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得・冪等保存（バックフィル・健全性チェック対応）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL 実行結果を表す dataclass `ETLResult` を実装（取得件数・保存件数・品質チェック結果・エラー集約等）。
    - 差分取得・バックフィル・品質チェックの方針を反映したユーティリティを実装（テーブル存在確認、最大日付取得など）。
    - `ETLResult` を外部公開（kabusys.data.etl で再エクスポート）。
  - jquants_client との連携場所を確保（fetch/save 呼び出しを期待）。

- ニュース NLP / LLM インテグレーション（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へ送信、センチメント（-1.0〜1.0）を算出して ai_scores テーブルへ保存するワークフローを実装。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供する calc_news_window を実装（UTC 変換済み）。
    - バッチ処理：1 回の API コールで最大 20 銘柄を処理、1 銘柄あたり記事数／文字数の上限でトリム。
    - OpenAI の JSON Mode を利用し、レスポンスの厳密なバリデーションとスコアのクリップ（±1.0）を実装。
    - 再試行（429 / ネットワーク / タイムアウト / 5xx）に対する指数バックオフを実装。致命的でない失敗はスキップして継続するフェイルセーフ設計。
    - DuckDB の executemany の制約を考慮した安全な DELETE→INSERT による置換ロジック（部分失敗時に既存スコアを保護）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、ニュース NLP によるマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する機能を実装。
    - MA200 の計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロニュース抽出（キーワードフィルタ）→ OpenAI での JSON パース→ 合成スコアのクリップ→ regime_label 決定を行う。
    - OpenAI 呼び出しは専用の内部実装（news_nlp と共有しない）でモジュール分離を実施。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。API エラーやパース失敗時はフェイルセーフ（macro_sentiment=0.0）で継続。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER・ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金・出来高比率）を計算する関数を実装。
    - DuckDB の SQL ウィンドウ関数を活用し、営業日ベースでのラグ/移動平均を安全に計算。
    - データ不足時に None を返すなど堅牢な挙動。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）に対する将来終値リターンを計算。
    - IC（Information Coefficient）計算（calc_ic）：ファクターと将来リターンのスピアマンランク相関を算出（十分なレコードがない場合は None を返す）。
    - ランキング関数（rank）：同順位は平均ランクで扱う（丸めで ties を扱う実装）。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を標準ライブラリのみで計算。
  - zscore 正規化ユーティリティを data.stats から再エクスポート。

- 共通設計方針・品質
  - ルックアヘッドバイアス防止のため、どのモジュールも datetime.today()/date.today() を直接スコア計算に用いない設計を明記・実装。
  - OpenAI API キーの注入に対応（引数優先、環境変数 OPENAI_API_KEY をフォールバック）。未設定時は明確な ValueError を送出。
  - DuckDB をデータ層に採用し、SQL と Python の組合せで集計/ETL/解析を実装。
  - ロギングを多用し、警告・情報・デバッグメッセージで処理状況・失敗時の理由を記録。

### Changed
- 初回リリースのため変更履歴はありません。

### Fixed
- 初回リリースのため修正履歴はありません。

### Deprecated
- 初回リリースのため非推奨項目はありません。

### Removed
- 初回リリースのため削除項目はありません。

### Security
- 特記なし（ただし環境変数や API キーの取り扱いは Settings を通じて明示的に管理）。

---

注記:
- 上記はソースコードからの推測に基づく CHANGELOG です。実際のリリースノートや既知の変更点がある場合は、それに合わせて更新してください。