# Changelog

すべての変更は Keep a Changelog の仕様に従って記載しています。  
安定版リリースの履歴を日付付きで管理します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- （プレースホルダ）次回リリースに向けた変更点をここに記載します。

---

## [0.1.0] - 2026-03-31

初期リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（src/kabusys/__init__.py）。バージョン 0.1.0。
  - パッケージ公開モジュール: data, strategy, execution, monitoring（__all__ にて宣言）。

- 設定管理
  - 環境変数・設定読み込みユーティリティ（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml に基づく）。
    - .env / .env.local の自動読み込み（OS 環境変数の保護、.env.local は上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テストサポート）。
    - 強力な .env パーサ：export 形式対応、シングル/ダブルクォート内エスケープ処理、インラインコメント処理。
    - Settings クラスで主要設定をプロパティとして提供（J-Quants, kabu API, Slack, DB パス, 環境判定, ログレベル等）。
    - 標準値（例: KABUS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）とバリデーション（KABUSYS_ENV, LOG_LEVEL）を備える。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプラインの骨格（src/kabusys/data/pipeline.py）。
    - ETLResult データクラスを公開（保存件数、品質問題、エラー情報を格納）。
    - 差分取得、バックフィル、品質チェックの設計を反映。
  - ETL の公開再エクスポート（src/kabusys/data/etl.py: ETLResult）。
  - 市場カレンダー管理（src/kabusys/data/calendar_management.py）。
    - JPX カレンダーの夜間更新ジョブ（calendar_update_job）。
    - 営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データ優先の判定ロジックと曜日ベースのフォールバック、最大探索範囲（_MAX_SEARCH_DAYS）などの安全対策。
    - バックフィルや健全性チェック（未来日付の異常検出）を実装。

- リサーチ/ファクター解析
  - research モジュール初期実装（src/kabusys/research/*）。
    - ファクター計算（src/kabusys/research/factor_research.py）
      - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
      - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、平均売買代金、出来高比率を計算。
      - calc_value: PER（EPS を使用）、ROE を raw_financials と prices_daily から計算。
      - 設計におけるデータ不足時の None 返却や DuckDB を利用した窓関数実装。
    - feature_exploration（src/kabusys/research/feature_exploration.py）
      - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを計算。
      - calc_ic: スピアマンのランク相関（IC）を計算し、サンプル不足時は None を返す。
      - rank: 同順位は平均ランクを採る実装（丸め対策あり）。
      - factor_summary: カラムごとの count/mean/std/min/max/median を計算。
    - research パッケージの再エクスポート（__init__.py）で主要関数を公開。

- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメント自動スコアリング（src/kabusys/ai/news_nlp.py）。
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）にバッチ送信してスコアを生成。
    - JSON Mode を期待するプロンプト設計とレスポンスバリデーション（結果フォーマット検証、未知コードの無視、スコア数値型検査）。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事制限（件数・文字数）とトリム処理。
    - リトライ/バックオフ戦略（429・ネットワーク・タイムアウト・5xx に対して指数バックオフ）、失敗時はスキップして継続（フェイルセーフ）。
    - ai_scores テーブルへの冪等書き込み（DELETE → INSERT、トランザクション、部分書き換えで他データを保護）。
    - 時間ウィンドウの計算（JST ベースを UTC naive に変換）とルックアヘッドバイアス排除（datetime.today() を参照しない設計）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）の合成で日次レジーム判定（'bull'/'neutral'/'bear'）。
    - prices_daily / raw_news からのデータ取得、OpenAI（gpt-4o-mini）によるマクロセンチメント評価（JSON 出力期待）。
    - API の再試行・バックオフ、API 失敗時は macro_sentiment=0.0（フェイルセーフ）で継続。
    - market_regime テーブルへの冪等的な書き込み（BEGIN/DELETE/INSERT/COMMIT）、失敗時の ROLLBACK 対応。
    - ルックアヘッドバイアス対策を徹底（DB クエリにて date < target_date 等）。

- OpenAI クライアントの扱い
  - OpenAI API 呼び出しのラッパー実装（各モジュール内の _call_openai_api）。
  - JSON mode を活用し厳密な JSON パースを行うが、余分な前後テキストが混入した場合の保険処理（最外の {} を抽出して再パース）を実装。
  - テスト用に各モジュールで _call_openai_api を patch して差し替え可能。

- ログ / エラーハンドリング
  - 各主要処理での情報ログ / 警告ログを追加（logger 経由）。
  - DB 書き込み時のトランザクション制御とロールバック処理、ロールバック失敗時の警告ログ。
  - 入力バリデーション（環境変数必須チェック、horizons のバリデーション等）。

- DuckDB 互換性考慮
  - executemany の空リスト問題やリスト型バインドの不安定さを回避する実装（空チェック、個別 DELETE 実行など）。

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Security
- 初回リリースのため該当なし

---

Notes
- 本バージョンは「初期実装（プロトタイプ）」。今後のリリースで以下を予定:
  - strategy / execution / monitoring の実装拡充（実取引ロジック・オーダー送信・稼働監視）。
  - 単体テスト・統合テストの追加、CI の整備。
  - ドキュメント（API リファレンス、運用手順）の拡充。
  - 安全性監査（API キー管理、機密情報の取り扱い）とより詳細なエラー分類。

デベロッパーメモ:
- 主要な設計方針として「ルックアヘッドバイアスの排除」「外部 API 失敗時のフェイルセーフ」「DB 書き込みの冪等性」「テスト容易性」を優先しています。