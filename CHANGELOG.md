# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

なお、このCHANGELOGは与えられたコードベースから実装内容を推測して作成した初版のリリースノートです。

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定・読み込み (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を読み込む Settings クラスを追加。
  - .env 自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - export KEY=val 形式、シングル/ダブルクォートのエスケープ、インラインコメントの取り扱いなどを考慮した .env パーサを実装。
  - 設定で必須項目を取り扱う _require 関数を導入。
  - Settings で取得する主要な環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルトあり)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）, LOG_LEVEL（検証）

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してセンチメントスコアを算出。
    - JST ベースの時間ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST、UTC 変換して DB と照合）。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの最大記事数・文字数制限、レスポンスバリデーション、スコア ±1.0 のクリップ。
    - API の429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライとフォールバック（失敗時は該当チャンクをスキップ）。
    - DuckDB の executemany 空リスト制約を考慮して安全に DELETE/INSERT を実行。
    - テスト容易性のため OpenAI 呼び出しは差し替え可能（_call_openai_api のモック化が可能）。

  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる raw_news フィルタ、OpenAI を使ったマクロセンチメント算出、スコア合成ロジックを実装。
    - API エラー時は macro_sentiment を 0.0 にフォールバックして継続（フェイルセーフ）。
    - DB への書込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。
    - OpenAI 呼び出しに対するリトライ/バックオフ処理を実装。

- データプラットフォーム - カレンダー管理 (src/kabusys/data/calendar_management.py)
  - JPX 市場カレンダー管理機能を実装。
  - is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day 等の営業日判定ユーティリティを提供。
  - market_calendar テーブルの存在有無に応じた DB優先/曜日フォールバック戦略を採用。
  - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得 → save）。
  - 安全対策: 最大探索日数、バックフィル日数、健全性チェック（過剰な未来日付はスキップ）。

- ETL パイプライン (src/kabusys/data/pipeline.py, etl.py re-export)
  - ETLResult データクラスを追加（ETL 実行結果の集約: 取得件数・保存件数・品質問題・エラー等）。
  - 差分更新、backfill、品質チェックの取り扱い方針を実装方針として導入。
  - _table_exists や _get_max_date 等のヘルパー実装。

- Research（因子・特徴量探索） (src/kabusys/research)
  - ファクター計算 (factor_research.py)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER・ROE）等の定量ファクターを DuckDB SQL ベースで実装。
    - 欠損やデータ不足時の None 扱いを明示。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（Spearman）calc_ic、ランク付け rank、統計サマリー factor_summary を実装。
    - pandas 等外部依存を避け、標準ライブラリで実装。
  - zscore_normalize を data.stats から再利用し公開。

- 研究向け API の公開 (src/kabusys/research/__init__.py)
  - 主要関数群を再エクスポートして研究ワークフローで利用しやすくした。

### 変更 (Changed)
- 初回リリースのため変更履歴なし。

### 修正 (Fixed)
- 初回リリースのため修正履歴なし。

### 破壊的変更 (Removed)
- 初回リリースのためなし。

### 注意事項 / 既知の制約 (Notes / Known limitations)
- OpenAI 関連
  - news_nlp / regime_detector は OpenAI API（gpt-4o-mini）に依存。api_key 引数または環境変数 OPENAI_API_KEY の設定が必要。未設定時は ValueError を送出。
  - レスポンスの JSON パースに失敗した場合や API が不安定な場合はフォールバック・スキップする設計になっている（例: スコアを 0.0 にする、チャンクをスキップ）。

- .env 読み込み
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行う。パッケージ配布後でも __file__ 基準で探索するため CWD に依存しない。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- DuckDB 互換性
  - DuckDB の executemany が空リストを受け付けないバージョン（0.10 系）への配慮がコード中にある。埋め込み SQL のバインド方法に互換性配慮あり。

- ルックアヘッドバイアス防止
  - AI モジュール・研究モジュールともに datetime.today()/date.today() を直接参照せず、明示的な target_date を受け取る設計。データ取得クエリも target_date 未満/以前の条件を明記している。

- フォールバック動作
  - データが不足する場合（例: MA を計算するための行数が不足）は中立値（ma_ratio=1.0やスコア None/0.0）を返すなどフェイルセーフ設計。

### テスト支援
- OpenAI 呼び出し部分はモジュール内の _call_openai_api をテスト時にモック化可能な形で実装しているため、単体テストで外部呼び出しを差し替えやすい。

---

もしリリースノートの粒度（変更点の詳細化、ファイル別の改行／差分記載など）をさらに細かくしたい場合や、特定の変更点（例: news_nlp のプロンプトや retry ロジック、calendar_update_job の挙動）をより技術的に詳述したい場合は指示ください。