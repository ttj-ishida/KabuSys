# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

なお、本CHANGELOGは現在のコードベースから機能・振る舞いを推定して作成しています（コミット履歴ではなくソースコードの実装内容に基づく記載）。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-03

初回リリース。本パッケージは日本株自動売買プラットフォームの基盤機能群を提供します。主な追加点は以下の通りです。

### Added

- パッケージ基本情報
  - kabusys パッケージの初期バージョン（__version__ = "0.1.0"）。公開インターフェースとして data, strategy, execution, monitoring をエクスポート。

- 環境設定・.env 管理（kabusys.config）
  - .env ファイルや環境変数から設定を読み込む Settings クラスを追加。
  - 自動ロードの探索はパッケージファイル位置を基準に .git または pyproject.toml を探索してプロジェクトルートを検出（CWD 非依存）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パースの改善:
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメント判定の細かなルール（クォートあり/なしで挙動を分離）。
  - 環境変数要求時に未設定で ValueError を投げる _require を提供。
  - 各種設定プロパティ（J-Quants トークン、Kabu API 設定、LINE トークン、DBパス、監視閾値、環境/ログレベル判定等）を実装。無効値については ValueError で検出。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを構成し、OpenAI（gpt-4o-mini）のJSON Modeでセンチメントを取得。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST に対応する UTC 範囲を計算する calc_news_window を実装。
    - バッチ（最大20銘柄）処理・1銘柄あたり記事・文字数上限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - 429・ネットワーク断・タイムアウト・5xx を対象とした指数バックオフによるリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results キー検査、コード照合、数値検査）と ±1.0 のクリップ。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）により部分失敗時の既存データ保護。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の200日MA乖離（重み70%）とマクロニュースのLLMセンチメント（重み30%）を合成して日次で regime_score/label を算出し market_regime テーブルへ冪等書き込み。
    - マクロニュースは news_nlp.calc_news_window を利用してウィンドウ内のタイトルを抽出。LLM（gpt-4o-mini）で JSON を返すようにプロンプト指定。
    - API 呼び出し失敗やパース失敗時には macro_sentiment=0.0 としてフェイルセーフに継続。
    - LLM 呼び出し用の内部関数を news_nlp から分離して実装（モジュール結合低減）。
    - DuckDB トランザクションで BEGIN / DELETE / INSERT / COMMIT を行い、失敗時は ROLLBACK を試行して上位へ例外を伝播。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar テーブルの有無に依存しつつ、DB データ優先・未登録日は曜日フォールバックという一貫した営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - 最大探索日数制限、先読み・バックフィル・健全性チェックの実装。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する calendar_update_job を追加（バックフィル/_BACKFILL_DAYS、健全性チェックあり）。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスで ETL の取得数・保存数・品質問題・エラーを構造化して返却。
    - 差分更新・バックフィル方針、品質チェックの設計（重大度を収集して呼び出し元が判断できる形）を実装。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティを実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対ATR、20日平均売買代金、出来高比率）、Value（PER、ROE）を実装。
    - DuckDB のウィンドウ関数を活用して効率的に計算。データ不足時は None を返す設計。
    - 外部 API には依存せず prices_daily / raw_financials のみを参照。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）で LEAD を使ってまとめて計算。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関を直接実装（同順位は平均ランク）。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を計算。
    - ランク変換ユーティリティ（rank）。
  - 研究用APIを __all__ でエクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize 等）。

### Changed

- 設計方針・安全策の明示的実装
  - ルックアヘッドバイアス防止: 全てのモジュールで datetime.today()/date.today() を直接参照しない設計を採用（target_date を明示的に引数で受ける）。
  - DuckDB への書き込みは冪等性・部分置換を意識（DELETE → INSERT の順で対象コードのみ更新）し、DuckDB の executemany に関する互換性考慮を含めた実装。
  - OpenAI 呼び出しに対する堅牢なリトライ戦略（429/ネットワーク断/タイムアウト/5xx の扱い差分）を各モジュールで採用。
  - テスト容易性のため、内部API呼び出し（_call_openai_api）をパッチ差し替え可能に実装。

### Fixed

- （初回リリースのため特定の問題修正履歴はなし。設計上のフェイルセーフ・健全性チェックで実運用時の障害耐性を向上。）

### Security

- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は明示的な ValueError を投げることで誤用を防止。
- .env の自動上書き時、OS 環境変数（プロセス既存の環境）は protected として保護（override フラグ利用時も保護対象除外）。

---

この CHANGELOG はソースコードの振る舞いと docstring、ログメッセージに基づいて作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、さらに細かいモジュール別の変更点や既知の制約（DuckDB バージョン互換性、OpenAI SDK バージョン依存など）を追加できます。どのレベルの詳細が必要か教えてください。