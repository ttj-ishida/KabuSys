# CHANGELOG

すべての変更は「Keep a Changelog」の形式に従って記載しています。
リリース日付はコードベースの現在時点（このドキュメント作成日）を使用しています。

## [Unreleased]

---

## [0.1.0] - 2026-04-04

初回リリース — 日本株自動売買 / データ基盤 / リサーチ / ニュースNLP を含む基本機能を実装。

### 追加 (Added)
- パッケージのメタ情報
  - kabusys パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
  - パッケージ公開 API に data, strategy, execution, monitoring をエクスポート。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数からの設定読み込み機能を実装。
  - 自動 .env 読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env/.env.local の優先度制御（OS 環境変数を保護する protected 機能）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - 複雑な .env 行のパース対応（export プレフィックス、クォート／エスケープ、インラインコメントの扱い）。
  - Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須・既定値・型変換。
    - 環境 (development / paper_trading / live) と log level 検証。
    - DB/監視用パスや閾値の取得ユーティリティ（duckdb/sqlite/pid/killflag 等）。
    - is_live / is_paper / is_dev ヘルパー。

- ニュースNLP（AI） (src/kabusys/ai/news_nlp.py, src/kabusys/ai/__init__.py)
  - raw_news と news_symbols を用いた銘柄毎のニュース集約・OpenAI でのセンチメント評価機能を実装（score_news）。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象にする明示的計算（calc_news_window）。
  - バッチ処理（最大 20 銘柄／API 呼び出し）、1 銘柄あたり記事数・文字数制限（トリム）を実装。
  - OpenAI JSON Mode を使用し厳密な JSON 出力を期待。
  - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。その他エラーはスキップしてフェイルセーフに継続。
  - レスポンスのバリデーション（JSON 抽出、results リスト、code/score の整合性、数値チェック、±1.0 クリップ）。
  - DuckDB への冪等書き込み（該当 date/code の DELETE → INSERT）。部分失敗時に既存データを保護する実装。

- 市場レジーム判定（AI 組合せ） (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（score_regime）。
  - OpenAI 呼び出しは gpt-4o-mini を想定。API エラー時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
  - レジームスコアを -1〜1 にクリップし閾値で bull/neutral/bear を決定。
  - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。エラー時は ROLLBACK を試行。

- データ基盤: カレンダー管理 (src/kabusys/data/calendar_management.py)
  - JPX 市場カレンダー管理と営業日判定機能を実装:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
  - market_calendar が未取得のときは曜日 (土日) ベースでフォールバックするロジック。
  - 最大探索範囲の安全化 (_MAX_SEARCH_DAYS) とバックフィル／先読み設定。
  - 夜間バッチジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得・保存・健全性チェックを行う）。

- データ基盤: ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult データクラスを導入（ETL 実行結果の集約・シリアライズ用）。
  - ETL の差分更新・バックフィル方針を明確化する設計。品質チェック結果の収集を想定。
  - etl モジュールから ETLResult を再エクスポート。

- リサーチ / ファクター計算 (src/kabusys/research/*)
  - ファクター計算モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比などを計算。
    - calc_value: latest raw_financials（report_date <= target_date）と株価を使った PER / ROE を計算。
  - 特徴量探索モジュールを実装:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターン算出（LEAD を使用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクにするランク関数（丸め処理で ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- データユーティリティ
  - DuckDB 接続前提の SQL 実装を多用し、外部依存を極力排した設計。
  - 日付の取り扱いはすべて date / naive datetime（タイムゾーン混入を防止）。
  - 重要箇所でのログ出力と警告出力を充実化。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 機能制限 / 設計上の注意 (Notable design notes)
- LLM 呼び出しは外部 API（OpenAI）に依存。OPENAI_API_KEY は score_news / score_regime の引数で注入可能（テスト容易性）。
- LLM/API の不安定性に対してはフェイルセーフ戦略（0.0 で続行、部分的に書き込み）を採用。
- ルックアヘッドバイアス防止: 各スコアリング/計算関数は datetime.today() / date.today() を直接参照しない（引数 target_date に依存）。
- DuckDB のバージョン差異（executemany の空リスト取り扱いなど）を考慮した実装。
- .env パースは一般的なケースに対応するが、完全なシェル互換性を保証するものではない。

### セキュリティ (Security)
- 環境変数からAPIキーやパスワードを取得する設計。自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- .env 読み込み時に OS 環境変数を保護する protected 機能を実装。

---

今後の予定（例）
- strategy / execution / monitoring パッケージの実装拡充（注文ロジック・実行監視など）。
- テストカバレッジの追加（ユニットテスト・統合テスト）。
- ドキュメント（API リファレンス・デプロイ手順）の拡充。