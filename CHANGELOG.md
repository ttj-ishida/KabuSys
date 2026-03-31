CHANGELOG
=========

すべての注記は Keep a Changelog の形式に準拠しています。  
重要な設計上の決定やフォールバック挙動はコードの実装から推測して記載しています。

Unreleased
----------
（現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- 初回リリース v0.1.0 を公開。
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - サブパッケージ公開リストを定義（data, strategy, execution, monitoring）。
- 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export 付き行、シングル/ダブルクォート、エスケープ、インラインコメント等を考慮した .env パーサを実装。
  - 環境変数の保護（OS 環境変数を protected として上書き防止）と .env.local による上書きサポート。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを追加し、必要な環境変数をプロパティ経由で取得（必須項目は _require により ValueError を送出）。
  - 許容される実行環境（development/paper_trading/live）とログレベルのバリデーションを実装。
  - DB パス（DUCKDB_PATH / SQLITE_PATH）、Slack / kabu API / J-Quants トークン等の設定をプロパティ化。
- AI / ニュースNLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols から記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄毎のセンチメントを算出する score_news を実装。
  - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数上限・文字数トリムなどトークン肥大化対策を実装。
  - API の再試行（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフと最大リトライ回数を実装。
  - レスポンスの厳格なバリデーション（JSON 抽出、results 配列の検証、コード照合、数値変換、クリップ）を実装。無効レスポンスはスキップして部分失敗に耐える設計。
  - DuckDB への書き込みは冪等に行い、部分失敗時に既存データを保護（該当コードのみ DELETE → INSERT）。
  - テスト用フック: _call_openai_api を patch して置き換え可能。
- AI / レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - マクロニュースの抽出は kabusys.ai.news_nlp.calc_news_window を利用。OpenAI コールは内部で専用の実装を使いモジュール結合を低減。
  - API エラー時のフェイルセーフ（macro_sentiment=0.0）と retry/backoff ロジックを実装。
  - 判定結果は market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
- Data / カレンダー管理 (kabusys.data.calendar_management)
  - JPX カレンダー管理用ユーティリティを実装。
  - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。DB の market_calendar が存在する場合は DB 値を優先、未登録日は曜日（週末）ベースでフォールバック。
  - calendar_update_job により J-Quants から差分取得 → market_calendar へ冪等保存する仕組みを実装。バックフィル・健全性チェックを実装。
- Data / ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
  - ETLResult データクラスを実装し、ETL 実行結果の集約・シリアライズ機能を提供。
  - データ取得の差分更新（最終取得日に基づく）、バックフィル、品質チェックフック（quality モジュール連携）を想定した設計。
  - DuckDB のテーブル存在確認、最大日付取得などのユーティリティを実装。
- Research（kabusys.research）
  - ファクター計算（calc_momentum, calc_value, calc_volatility）を実装。prices_daily / raw_financials を元に各種ファクターを算出。
  - 特徴量探索機能（calc_forward_returns, calc_ic, factor_summary, rank）を実装。Spearman（ランク相関）の IC 計算や統計サマリーを提供。
  - すべて DuckDB を直接参照する SQL ベースの実装で、外部 API や発注ロジックにはアクセスしない安全設計。

Changed
- N/A（初回リリースのため既存からの変更はありません）。

Fixed
- N/A（初回リリースのためバグフィックス履歴はありません）。

Security
- 環境変数の必須項目に対して明示的なチェックを実装（OpenAI / SLACK / KABU API 等）。未設定時は ValueError を返すことで誤動作を抑止。
- .env 読み込み時に OS 環境変数を保護する仕組みを導入（意図しない上書きを防止）。

Notes / 設計上の重要点（実装からの推測）
- ルックアヘッドバイアス対策として、日付計算で datetime.today()/date.today() を直接参照しない設計（関数は target_date 引数を明示的に受け取る）。
- API 呼び出しに対しては堅牢なフェイルセーフを採用（LLM/API エラー時は例外を上位へ伝播させずフォールバック値を使う場面がある）。
- DuckDB を中心に SQL ウェイトで大量データ処理を行い、データ保存は冪等性（DELETE→INSERT／ON CONFLICT想定）を重視。
- OpenAI へは gpt-4o-mini を JSON Mode で利用することを前提としている（レスポンスの厳密な JSON 構造を期待）。
- テスト容易性のため API 呼び出し部分（_call_openai_api 等）をパッチ差替え可能にしている。

問い合わせ・追加情報
- 具体的な API キー名や必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等がコード内で参照されます。
- DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials）はコード中のクエリから期待されるカラムが推測できます。必要であればスキーマ草案を生成します。

--- 
（以上）