# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
各バージョンは安定的に動作する単位で想定したリリース内容をコードベースから推測してまとめています。

## Unreleased
- 今後想定される作業（コードからの推測）
  - monitoring パッケージの実装（パッケージ公開インターフェースに含まれているが実装ファイルは今回のスナップショットに含まれていません）。
  - ETL / データ取得に関する追加の品質チェックやエンドツーエンドテストの整備。
  - ドキュメント（API 仕様・DB スキーマ）やサンプル設定ファイルの拡充。

---

## [0.1.0] - 2026-04-01

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開。
  - パッケージ __init__ にて主要サブパッケージ（data, research, ai, ...）をエクスポート。

- 環境設定 / config
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env の行パース機能を強化（export KEY=... 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの扱い等に対応）。
  - 環境設定アクセス用 Settings クラスを実装。J-Quants / kabu / Slack / DB パス / 監視閾値 / ログレベル等をプロパティで提供。
  - 設定のバリデーションを導入（KABUSYS_ENV の有効値制限、LOG_LEVEL 検証、必須項目は _require により未設定時に ValueError を発生）。

- AI（自然言語処理）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄/コール）、記事数・文字数でトリムする上限を実装。
    - API 呼び出しのリトライ（429 / ネットワーク / タイムアウト / 5xx）と指数バックオフを実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score の検査、数値の有限性チェック）を実装。
    - ai_scores テーブルへの冪等的な書き込み（該当 date・code の DELETE → INSERT）を実装。部分失敗時に既存スコアを保護する戦略を採用。
    - テスト容易性のため OpenAI 呼び出し部分は内部関数に切り出し、 unittest.mock.patch で差し替え可能。

  - kabusys.ai.regime_detector
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - prices_daily / raw_news からデータを取得し、calc_news_window を利用したウィンドウでニュースを抽出。
    - OpenAI を利用したマクロセンチメント評価（JSON レスポンスを期待）。API の失敗やパース失敗時はフェイルセーフで 0.0 を採用。
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。書き込み失敗時はロールバックを試行し、エラーを伝播。

- Data（データ基盤）
  - kabusys.data.calendar_management
    - JPX マーケットカレンダーを扱うユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が存在しない場合は曜日ベース（土日非営業）でのフォールバックを行い、一貫した挙動を保証。
    - calendar_update_job により J-Quants API から差分取得 → 保存（バックフィルや健全性チェック含む）する夜間バッチ処理を実装。
  - kabusys.data.pipeline / etl
    - ETLResult データクラスを公開（prices/financials/calendar の取得・保存件数、品質問題、エラー要約を含む）。
    - ETL の差分取得、バックフィル、品質チェック（quality モジュールとの連携）を想定したパイプライン基盤を実装。
    - DB テーブル存在確認や最大日付取得のユーティリティを実装。

- Research（要因分析）
  - kabusys.research.factor_research
    - モメンタム（1M/3M/6M）、200 日移動平均乖離、ATR（20 日）、平均売買代金 / 出来高比率、PER / ROE（raw_financials 連携）などのファクター計算を実装。
    - DuckDB SQL を用いた効率的な集計クエリを実装。データ不足時は None を返す設計。
  - kabusys.research.feature_exploration
    - 将来リターン計算（任意ホライゾン）、IC（Spearman のランク相関）、ランク変換、ファクター統計サマリ（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。ランクでは同順位を平均ランクで扱う。

### Changed
- （初期リリースのため該当なし。コード内に設計方針として「ルックアヘッドバイアス防止」などのベストプラクティスを明示的に取り入れた実装が含まれます。）

### Fixed
- .env 読み込みにおけるエラー時の警告出力を追加（ファイル読み込み失敗時に warnings.warn）。
- OpenAI 呼び出しでの様々な例外（429/タイムアウト/APIError/ネットワーク）に対してログで状況を記録し、安全にフォールバックするように修正（例外を上位へ投げず継続できる設計）。

### Security
- API キーの取り扱い
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を発生させ明示的に扱うことで誤った公開を防止。
  - 環境変数自動ロード時に OS 環境変数を保護するため protected set を使用し、.env.local の override 時も OS 環境変数を上書きしない仕組みを提供。

### Notes / Migration
- DB スキーマ（期待されるテーブル）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などが前提になっています。初回利用前にこれらのスキーマが整備されている必要があります。
- OpenAI の利用
  - gpt-4o-mini（JSON Mode）を前提とした実装。レスポンス形式や API バージョンの変更はパース処理の見直しが必要です。
- ルックアヘッドバイアス対策
  - 各処理（news のウィンドウ、ma200 計算、ファクター計算等）は target_date 未満 / target_date を明確に扱う設計になっています。運用時に date の扱いに注意してください。

---

著者: kabusys コードベースからの推測（自動生成）  
注: 本 CHANGELOG は提供されたソースコードの内容に基づいて推測・要約したものであり、実際のリリースノートには追加の変更履歴や運用情報が含まれる可能性があります。必要であれば、特定モジュールごとにさらに詳細な変更点や使用例、注意事項を追記します。