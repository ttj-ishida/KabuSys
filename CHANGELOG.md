# Changelog

すべての変更は「Keep a Changelog」フォーマットに従って記載しています。  
主な方針：後方不変性を意識した設計、ルックアヘッドバイアス回避、外部API呼び出しの堅牢化（リトライ/フォールバック）、DuckDBとの互換性考慮。

## [0.1.0] - 2026-03-31

### 追加 (Added)
- 基本パッケージ初期実装
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
  - パッケージ公開 API: `data`, `strategy`, `execution`, `monitoring` を __all__ としてエクスポート。

- 環境設定・自動.env読み込み (`kabusys.config`)
  - プロジェクトルート検出：`.git` または `pyproject.toml` を起点に探索して自動で .env を読み込む仕組みを追加（カレントワーキングディレクトリに依存しない）。
  - 読み込み優先順位：OS環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサ実装：`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
  - 安全な上書き管理：`.env.local` は上書き（override）されるが、起動時の OS 環境変数は保護（protected set）する挙動。
  - Settings クラスでプロパティ化された設定項目を提供（J-Quants, kabuステーション, Slack, DBパス, 監視閾値, 環境/ログレベル判定など）。
  - env/log 値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）および is_live/is_paper/is_dev ヘルパー。

- AI モジュール（ニュースNLP / レジーム判定）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを取得して ai_scores テーブルへ書き込み。
    - バッチ処理・チャンク単位（最大20銘柄）でAPI呼び出し。1銘柄あたりの記事数・文字数の上限を設定してトークン肥大化を抑制。
    - リトライ/バックオフ：429/ネットワーク断/タイムアウト/5xx を指数関数的バックオフでリトライ。
    - レスポンス検証：JSONパース、`results` フォーマット検証、未知コードの無視、スコアの数値化と ±1.0 でのクリップ。
    - DuckDB の executemany の空リスト制約に配慮（空の場合は呼ばない）。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない（target_date 指定方式）。
    - テスト容易性：内部の OpenAI 呼び出し関数を patch 可能に設計。

  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定、`market_regime` テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - マクロニュース抽出はマクロキーワードリストでフィルタ。記事がない場合は LLM を呼ばず macro_sentiment=0.0 として継続。
    - OpenAI API 呼び出しでのリトライ、HTTP 5xx の場合にリトライ、その他はフェイルセーフで macro_sentiment=0.0 を採用。
    - lookahead バイアス対策（prices_daily クエリは target_date 未満のデータのみを使用）。

- データプラットフォーム / ETL (`kabusys.data`)
  - calendar_management
    - JPX カレンダーを管理する `market_calendar` テーブルに基づく営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - カレンダー未取得時は曜日ベース（土日非営業）でフォールバックする一貫した挙動。
    - 夜間バッチ `calendar_update_job`：J-Quants API から差分取得→冪等保存、バックフィルや健全性チェック（未来日異常検出）を組み込み。
  - pipeline / ETLResult
    - ETLResult データクラスを公開（data.etl から再エクスポート）。
    - ETL パイプライン設計に関するユーティリティ（差分取得、backfill、品質チェックの集約、エラー集積方針）。
    - DuckDB テーブル存在チェック、最大日付取得などのユーティリティを整備。

- 研究用モジュール（kabusys.research）
  - factor_research
    - 定量ファクター計算関数を実装：calc_momentum（1M/3M/6M リターン、200日MA乖離）、calc_volatility（20日ATR、相対ATR、20日平均売買代金、出来高比）、calc_value（PER, ROE）。
    - DuckDB + SQL ウィンドウ関数を活用した実装。データ不足時は None を返す仕様。
  - feature_exploration
    - calc_forward_returns（複数ホライズンの将来リターンを一度のクエリで取得）、calc_ic（スピアマンのランク相関によるIC計算）、factor_summary（基本統計量算出）、rank（平均ランクの実装）を追加。
    - 外部ライブラリ非依存（標準ライブラリのみ）での実装。入力値のバリデーションを実施。

- ロギングと設計注釈
  - 多数の関数で debug/info/warning ログを追加し、異常系での説明的ログ出力を実装。
  - データベース操作は明示的なトランザクション制御（BEGIN/COMMIT/ROLLBACK）を使用して冪等性と安全性を確保。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- 環境ファイル読み込みエラー時に警告を出して処理継続（OSの読み込み失敗で例外を投げない）。
- OpenAI レスポンスの JSON パース耐性を向上（前後に余計なテキストが混ざるケースで最外の {} を抽出してパースを試みる）。
- OpenAI 系呼び出しでの例外ハンドリングを強化：
  - RateLimitError / APIConnectionError / APITimeoutError は再試行（指数バックオフ）。
  - APIError（ステータスコードによる）に応じて再試行/即時フォールバックを判断。
  - 全リトライ消費時は警告ログとフェイルセーフ値（0.0）にフォールバック。
- DuckDB との互換性：`executemany` に空リストを渡さないガードを追加（DuckDB 0.10 の制約回避）。
- 日付取り扱いの堅牢化：DuckDBからの値を date に安全に変換するユーティリティを追加。

### セキュリティ (Security)
- 環境変数の取り扱いに注意：Settings の必須項目に未設定時は明示的な ValueError を送出して誤動作を防止。
- 自動 .env ロード時に OS 環境変数を保護する仕組み（protected set）を導入。  

### 既知の注意点 / 設計上のトレードオフ
- OpenAI 依存部分は API キーが必要（引数経由または環境変数 OPENAI_API_KEY）。API 失敗時は大抵フェイルセーフで継続する設計（例：macro_sentiment=0.0、スコア未取得の銘柄はスキップ）。
- 日付処理は全て明示的に target_date を受け取り、date.today()/datetime.today() を直接参照しないことでルックアヘッドバイアスを防止しているため、呼び出し側で正しい target_date を渡す必要がある。
- news_nlp の出力期待形式は厳密な JSON（JSON Mode）だが、現実の LLM レスポンスを考慮して復元ロジックを備えている。ただし完全な安全性は保証しない。

---

今後のリリース候補（例）
- Unreleased: OpenAI クライアント差し替え対応、単体テスト・統合テストの追加、kabuステーション API 実装（execution 周り）、モニタリング/アラート連携強化。