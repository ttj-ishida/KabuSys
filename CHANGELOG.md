# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

(当面の更新予定や未リリースの変更点をここに記載します)

---

## [0.1.0] - 2026-04-04

初回公開リリース。

### 追加 (Added)
- 基本パッケージ初期構成
  - パッケージメタ情報: kabusys v0.1.0 を導入（src/kabusys/__init__.py）。
  - パブリックサブパッケージエクスポート: data, strategy, execution, monitoring を公開。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - ファイル読み込みの優先順位を OS 環境変数 > .env.local > .env として実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env 解析器を実装（export プレフィックス、クォート／エスケープ、インラインコメント処理に対応）。
  - Settings クラスを提供し、J-Quants / kabu / LINE / DB / 監視 / システム関連設定をプロパティで取得。
  - 環境値の検証を実装（KABUSYS_ENV, LOG_LEVEL の許容値検査）。
  - 必須値が欠如した場合に分かりやすい例外メッセージを返す _require を実装。

- ニュース NLP（AI）モジュール（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ格納する処理を実装。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
  - バッチ処理（最大 20 銘柄／コール）、記事数と文字数のトリム制限を実装（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - JSON Mode を利用した出力のバリデーション（results 配列、code/score 検証）を実装。
  - API 呼び出しでの 429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフと再試行ロジックを実装。
  - レスポンスパース失敗や API エラーはフェイルセーフでスキップし、処理継続する設計。
  - DuckDB に対する冪等書き込み（DELETE → INSERT）で部分失敗時の既存データ保護を考慮。
  - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可）。

- 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、ニュース NLP により算出したマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定するロジックを実装。
  - prices_daily / raw_news を参照して ma200_ratio を独自計算し、ニュースはマクロキーワードでフィルタして最大件数を制限。
  - OpenAI 呼び出しは独立実装。API 再試行（リトライ）・フェイルセーフ（失敗時は macro_sentiment=0.0）を備える。
  - 判定結果を market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）する処理を提供。
  - ルックアヘッドバイアス防止の設計（target_date 未満のみ参照、datetime.today() を直接参照しない）。

- データプラットフォーム（src/kabusys/data）
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを提供（取得数／保存数／品質問題／エラー等の集約）。
    - 差分取得・バックフィル・品質チェックを想定した設計。jquants_client と quality モジュールを利用する想定。
  - calendar_management モジュール（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先しつつ、未登録日は曜日ベースでフォールバックする一貫した挙動を提供。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する夜間バッチ job を実装（calendar_update_job）。
    - バックフィル、先読み、健全性チェック（過度に将来の日付を検出した場合のスキップ）を実装。
  - ETL エクスポート（src/kabusys/data/etl.py）: pipeline.ETLResult を再エクスポート。

- 研究（research）モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER、ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用し、営業日バッファやデータ不足時の None 返却等を適切に扱う実装。
    - 設計上、prices_daily / raw_financials のみ参照し外部 API にアクセスしないことを明示。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、Information Coefficient（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存しない純 Python / DuckDB 実装。
  - research パッケージから主要関数群を再エクスポート。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- OpenAI API キーは引数で注入可能とし、環境変数 OPENAI_API_KEY のみを暗黙に参照しない設計（明示的入力を推奨）。
- .env 自動ロード時に OS 環境変数を保護（上書き不可）する仕組みを実装。
- 自動ロードを無効化する環境フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意し、テスト環境でのキー漏洩リスクを低減。

### 実装上の注意点 / 既知の制約 (Notes)
- DuckDB のバージョン互換性に関する留意点:
  - executemany が空リストを受け付けない点（DuckDB 0.10 系）を考慮して条件分岐を入れている。
  - SQL 内での配列バインド（ANY 等）はバージョンによって挙動が異なる可能性があるため、個別 DELETE を採用している箇所がある。
- AI 呼び出し関連:
  - レスポンスの JSON 解析は堅牢化しているが、LLM 出力の多様性により一部ケースでパース失敗する可能性がある（その場合はフェイルセーフでスキップ）。
  - API 呼び出し関数はテストで差し替え可能（ユニットテスト向け）。
- 日付の扱い:
  - すべての日付処理は lookahead バイアスを避ける目的で target_date ベースで設計され、datetime.today()/date.today() の直接参照を避ける実装方針を採用（一部 job は実行日を参照する）。
- 期待される DB スキーマ:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などのテーブルが存在する前提のロジックが含まれる。導入時はスキーマ整備が必要。

### テスト / 開発
- 実運用 API 呼び出しを含む箇所（OpenAI、J-Quants クライアント）はテストで差し替え可能な設計（モック化）としている。
- ログ出力（logger）を適切に配置し、失敗時の挙動を追跡しやすくしている。

---

(将来のリリースでは Unreleased → リリース日付きのセクションに移動し、ここを更新してください)
