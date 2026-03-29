# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
<https://keepachangelog.com/ja/1.0.0/>

なお、このCHANGELOGはソースコードの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初期リリース。日本株自動売買 / データ基盤 / 研究用ユーティリティ群をパッケージ化。

### Added
- パッケージ基盤
  - パッケージ名 `kabusys` を導入。バージョン `0.1.0` を `src/kabusys/__init__.py` に定義。
  - public サブパッケージとして data, research, ai, execution, monitoring, strategy 等を想定（__all__ に列挙）。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env 自動読み込み機構を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化。
  - .env のパース器能を実装（`export KEY=...`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などを考慮）。
  - OS 環境変数を保護する protected 機構を実装（.env で OS 環境変数を誤って上書きしない）。
  - Settings クラスを提供（`settings` をモジュールレベルで公開）。
    - J-Quants / kabu ステーション / Slack / DB パス（DuckDB / SQLite）等のプロパティを実装。
    - `KABUSYS_ENV`（development/paper_trading/live）や `LOG_LEVEL` の検証ロジックを実装。
    - `is_live`, `is_paper`, `is_dev` のヘルパーを提供。
    - 必須項目未設定時は ValueError を送出する安全設計。

- AI モジュール（src/kabusys/ai）
  - ニュースNLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価し ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST の UTC 変換）を実装（`calc_news_window`）。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたり記事数/文字数制限、レスポンスバリデーション、スコアクリッピング（±1.0）。
    - API 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）、ロバストなエラーハンドリング。部分成功時に既存スコアを保護する idempotent な DB 書き換え（DELETE → INSERT）を実装。
    - 公開関数 `score_news(conn, target_date, api_key=None)` を提供。API キーが未設定の場合は ValueError を送出。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 225 連動型）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し `market_regime` テーブルへ記録する `score_regime(conn, target_date, api_key=None)` を提供。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini, JSON mode）、レスポンスパースとリトライ処理、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアスを避けるため、内部で datetime.today() を参照しない設計（外部から target_date を与える方式）。
    - DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT と ROLLBACK ハンドリング）を実装。

- 研究用モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対ATR、出来高系指標）、Value（PER, ROE）などのファクター計算関数を実装。
    - DuckDB を用いた SQL ベースの計算。結果は (date, code) をキーにした dict リストを返す。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（`calc_forward_returns`）、IC（Spearman rank）計算（`calc_ic`）、ファクターの統計サマリー（`factor_summary`）やランク関数（`rank`）を実装。
    - pandas に依存せず標準ライブラリのみで実装。

- データ基盤モジュール（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理用ユーティリティを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar テーブルが未登録の場合の曜日ベースフォールバック、DB 登録値優先の一貫した挙動、最大探索日数による無限ループ防止等の設計。
    - 夜間バッチ更新ジョブ `calendar_update_job(conn, lookahead_days=90)` を実装（jquants_client を通じた差分取得・保存、バックフィルと健全性チェック）。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETL の差分取得・保存、品質チェック（quality モジュールとの連携）を想定したユーティリティを実装。
    - ETL 実行結果を表すデータクラス `ETLResult` を定義（品質問題やエラー情報を集約、辞書変換メソッドを提供）。
  - ETL 公開（src/kabusys/data/etl.py）
    - `ETLResult` の再エクスポートを実装。

- その他
  - モジュール間でのプライベート関数共有を避ける設計（AI モジュール内の OpenAI 呼び出しはモジュール単位で独自に実装されている）。
  - DuckDB を前提とした SQL 実装、トランザクションと executemany の空リスト回避等、互換性・堅牢性のための考慮が多数含まれる。
  - ロギングを広範に導入し、実行時の診断を容易にする。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーや各種トークンは必須設定項目として明示され、未設定時は ValueError を送出することで誤動作を防止。
- .env 自動ロード時に既存の OS 環境変数を保護する仕組みを導入（.env による上書きを防止）。

### Notes / 設計上の重要なポイント
- ルックアヘッドバイアス防止：AI 評価・ファクター計算のすべてで内部的に datetime.today()/date.today() を参照せず、外部から明示的に target_date を渡す設計を採用。
- API 呼び出しは冪等性・フォールバック重視：LLM や外部 API の失敗時は例外で停止させず、安全側のデフォルト値（例: 0.0）で継続する実装が多く見られる（監査・再処理は上位で対応）。
- DB 書き込みは冪等（既存行の削除→挿入、トランザクション管理）を意識しているため、部分失敗時でも既存データの保護を図る設計。

--- 

開発・運用にあたって、各モジュールの公開 API（引数や返り値、期待する DB スキーマ）に沿って利用してください。追加のリリースノートや既知の問題を反映させたい場合はお知らせください。