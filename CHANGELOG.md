# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

なお、ここに記載した内容はソースコードからの推測に基づく要約です。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース。主要機能群（設定管理 / データ ETL・カレンダー管理 / 研究用ファクター計算 / ニュース NLP と市場レジーム判定 / ユーティリティ）を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
  - パッケージのエクスポート対象モジュールを定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイル自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーを実装:
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート中のバックスラッシュエスケープ処理対応。
    - クォートなし行のインラインコメント（`#`）の扱いをきめ細かく処理。
  - .env 読み込み時に既存 OS 環境変数を保護するための protected キー群を導入。
  - Settings クラスを実装し、アプリで使用する主要設定プロパティを提供:
    - J-Quants / kabuAPI / LINE トークン等の取得、DB ファイルパス（DuckDB/SQLite）、監視用ファイルパスと閾値（CPU/MEM/DISK）、環境種別・ログレベル検証（許容値チェック）、利便判定プロパティ（is_live / is_paper / is_dev）。
  - 必須環境変数未設定時に `ValueError` を発生させる `_require` ヘルパーを実装。

- AI（ニュース NLP / レジーム判定）
  - ニュース NLP (`kabusys.ai.news_nlp`)
    - raw_news と news_symbols を集約し、銘柄ごとに LLM（gpt-4o-mini）へバッチ送信してセンチメントを算出し ai_scores テーブルへ書き込む処理を実装。
    - ウィンドウ定義（JST 前日 15:00 〜 当日 08:30、UTC に変換して DB 比較に使用）を提供（calc_news_window）。
    - バッチサイズ、最大記事数、最大文字数などの肥大化対策を実装（_BATCH_SIZE=20、_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）。
    - JSON Mode を利用し厳密な JSON レスポンスを期待。レスポンスの冗長テキスト混入に備えたパース回復ロジックを実装。
    - レスポンス検証（results キー/型/コード整合性/スコア数値/±1.0 クリップ）を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。部分失敗時にも既存スコアを不必要に削らないよう、書き込みは対象コードのみ DELETE → INSERT を行う（冪等性配慮）。
    - テストしやすいように OpenAI 呼び出しを差し替え可能（_call_openai_api を patch で置換）。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321 の 200日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - MA 比率計算、マクロキーワードで raw_news のタイトルを抽出、LLM でマクロセンチメントを評価（gpt-4o-mini、JSON mode）、合成スコアをクリップして閾値判定。
    - マクロ記事がない場合や API失敗時はフェイルセーフで macro_sentiment=0.0 として処理継続。
    - market_regime テーブルへの書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理を行い、DB 書き込み失敗時に ROLLBACK を試行。

- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算群を実装（factor_research.py）:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）を DuckDB 上で SQL + Python により計算する関数を提供（calc_momentum / calc_volatility / calc_value）。
    - 各関数は prices_daily / raw_financials テーブルのみを参照し、本番発注 API へはアクセスしない設計。
  - 特徴量探索（feature_exploration.py）:
    - 将来リターン計算（calc_forward_returns）、IC（情報係数：スピアマンρ）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - 外部依存を持たず標準ライブラリのみで実装。
  - 既存ユーティリティとの再エクスポート（zscore_normalize 等）。

- データプラットフォーム（Data）モジュール
  - マーケットカレンダー管理（data.calendar_management）:
    - market_calendar の存在チェック、営業日判定（is_trading_day）、次/前営業日検索（next_trading_day / prev_trading_day）、期間内営業日リスト取得（get_trading_days）、SQ 日判定（is_sq_day）等の API を実装。
    - DB にカレンダーが無い場合は曜日ベース（土日）でフォールバックする一貫した挙動を採用。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を冪等更新。バックフィルや健全性チェック（未来日の過度な存在を検出してスキップ）を実装。
  - ETL パイプライン（data.pipeline）
    - ETL 実行結果を表す dataclass `ETLResult` を実装（取得件数 / 保存件数 / 品質チェック結果 / エラー集約など）。
    - 差分取得、品質チェック、idempotent 保存（jquants_client の save_* を想定）という設計方針を文書化。
  - ETL インターフェースの再エクスポート（data.etl: ETLResult）。

- DuckDB 関連の運用上の配慮
  - executemany に空リストを渡すと問題となる DuckDB バージョンを考慮して空チェックを導入（score_news 等）。
  - DuckDB から返る日付値を安全に date オブジェクトに変換するユーティリティを実装。

### 変更 (Changed)
- 実装方針・設計上の重要な決定をコード内ドキュメント化:
  - AI モジュール・研究モジュールで datetime.today()/date.today() を直接参照せず、明示的な target_date を用いることでルックアヘッドバイアスを回避。
  - API 呼び出し失敗時は例外で停止させずフォールバック（安全側）で継続する方針を採用（可用性優先）。
  - モジュール間の内部関数共有を避けるため、OpenAI 呼び出し用のプライベート関数を各モジュールで別実装。

### 修正 (Fixed)
- エラー処理とロギングの強化:
  - API 呼び出し・DB 書き込み失敗時のログ出力を充実させ、リトライ状況やパース失敗、ROLLBACK の失敗などを警告/例外で明確化。
  - raw_news / market_calendar などの NULL 値や未登録状態に対するフォールバック処理を明示し、運用時の不整合に耐性を持たせた。

### 注意 (Notes)
- OpenAI API 連携部分は gpt-4o-mini と JSON mode を前提にしているため、API 仕様の変更やモデル変更に伴う調整が必要になる可能性があります。
- .env パース実装は多くの典型ケースに対応するが、特殊ケースの構文差（例: 複雑なエスケープやシェル固有の展開）には対応していない可能性があります。
- DuckDB のバージョン差異（特に executemany のリストバインド挙動）に配慮した実装を行っていますが、実環境での互換性確認を推奨します。
- J-Quants / kabu / LINE 等の外部 API キー・エンドポイントは環境変数で設定する必要があります。未設定時は明確に例外を投げます。

---

（以降のリリースでは Unreleased セクションに変更を記録し、リリース時にバージョンエントリへ移動してください。）