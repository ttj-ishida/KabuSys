# Changelog

すべての重要な変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

- ドキュメント方針: 変更は Added / Changed / Fixed / Security のカテゴリで整理しています。
- バージョン番号はパッケージの src/kabusys/__init__.py の __version__ と同期しています。

---

## [Unreleased]
（未リリースの変更はここに記載）

---

## [0.1.0] - 2026-03-31

最初の公開リリース。本リリースは日本株自動売買システムのコア機能群を提供します。主な機能は環境設定管理、データ ETL / カレンダー管理、リサーチ用ファクター計算、およびニュース/マクロセンチメントの AI スコアリングです。

### Added
- パッケージ初期公開
  - パッケージ名: kabusys、トップレベルで data, strategy, execution, monitoring モジュールを公開。
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git / pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
  - .env パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント判定（クォートあり/なしで挙動を分離）
  - 環境変数保護ロジック（OS 環境変数は protected として上書き防止）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB / 監視 / システム設定をプロパティ経由で取得。
    - バリデーション: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の許容値チェック。
    - パス系設定は Path に変換（expanduser 実行）。
    - リードオンリーなユーティリティ: is_live / is_paper / is_dev

- AI ニュース / レジーム判定 (kabusys.ai)
  - news_nlp.score_news:
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を生成。
    - バッチサイズ、記事数/文字数トリム、最大リトライ（429/ネットワーク/5xx）と指数バックオフを実装。
    - JSON Mode のレスポンス検証と堅牢なパースロジック（余分な前後テキストを切り出すフォールバック含む）。
    - スコアは ±1.0 にクリップ。部分成功を考慮した安全な DB 書き換え（DELETE→INSERT を対象コードのみで実行）。
    - テスト容易性: _call_openai_api をモック差し替え可能。
    - 日時ウィンドウ (JST ベース) を calc_news_window で計算し、ルックアヘッドバイアスを防止。

  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（70% ウェイト）とマクロニュースの LLM センチメント（30% ウェイト）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - DuckDB 経由で prices_daily/raw_news を参照。レジーム結果を market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出し時の再試行・5xx 判定・フォールバック（失敗時 macro_sentiment=0.0）。
    - テスト容易性: _call_openai_api を差し替え可能。
    - ルックアヘッドバイアス対策（関数に target_date を与え、date.today() を参照しない設計）。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: PER/ROE を raw_financials と prices_daily から算出（EPS が 0/欠損時は None）。
    - DuckDB SQL を多用し、営業日ベースの窓幅・データ不足判定を組み込み。

  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する効率的クエリ。
    - calc_ic: Spearman ランク相関（IC）計算（同順位は平均ランクで処理）。
    - rank: 値のランク化ユーティリティ（丸めによる ties 対応）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - 外部ライブラリ不使用（標準ライブラリ + DuckDB のみ）。

- データ基盤 (kabusys.data)
  - calendar_management:
    - 市場カレンダー操作ユーティリティ: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - market_calendar が未登録の場合の曜日ベースフォールバック実装（土日非営業日扱い）。
    - カレンダーの夜間更新ジョブ calendar_update_job を提供（J-Quants API 経由の差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数 / バックフィル / 先読み日数等の定数化。

  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題/エラーの保持、to_dict）。
    - ETL パイプライン設計方針とユーティリティ関数（テーブル存在チェック、最大日付取得など。ファイルは ETL のインターフェースを含む）。
    - 差分取得・バックフィル・品質チェックの方針と実装サポート（jquants_client との組合せを想定）。

- DuckDB を主要なオンディスク分析 DB として採用（各種関数は DuckDB の接続を引数に受け取る）。

### Changed
- なし（初回リリースのため該当なし）。

### Fixed
- なし（初回リリースのため該当なし）。

### Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を発生させて明示的に扱う。

### Notes / 設計方針（重要な決定）
- ルックアヘッドバイアス防止: コア処理は date.today() / datetime.today() を内部で参照せず、必ず target_date を明示的に受け取る設計。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）に依存する処理は失敗時に処理継続できるようフォールバックや部分書き込み保護を実装（例: macro_sentiment=0.0、部分成功時に既存データを消さない等）。
- テスト容易性: OpenAI 呼び出し (_call_openai_api) 等の差し替えポイントを用意。
- DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT などを想定）。DuckDB の executemany の挙動に配慮し、空リストバインドを避けるガードを実装。

---

もし特定ファイルや機能の説明をもっと詳しく追記してほしい箇所があれば教えてください（例: 各関数の例、期待される DB スキーマ、J-Quants / kabu API の依存関係など）。