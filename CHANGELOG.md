# CHANGELOG

すべての注目すべき変更履歴をここに記載します。本ファイルは Keep a Changelog のフォーマットに準拠します。

フォーマット方針:
- 重要な機能追加・変更・修正のみを記載しています。実装上の設計方針やフォールバック挙動など、運用上重要な実装ディテールも注記しています。
- 日付は本コードベースのスナップショット作成日を使用しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システム「KabuSys」の基礎モジュール群を実装。

### Added
- パッケージ基礎
  - kabusys パッケージの公開バージョンを 0.1.0 として設定。
  - __all__ に "data", "strategy", "execution", "monitoring" を設定（パッケージ公開 API の意図を明示）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル（.env, .env.local）や OS 環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を探索）。
  - .env パーサを実装し、export プレフィックス・シングル／ダブルクォート・エスケープ・インラインコメント等に対応。
  - 自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 環境モード / ログレベル等をプロパティで取得可能に。
  - 必須環境変数未設定時に ValueError を投げる _require を実装。
  - 有効な KABUSYS_ENV（development, paper_trading, live）や LOG_LEVEL の検証を実装。
  - デフォルトのデータベースパス（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）を設定。

- Data モジュール (kabusys.data)
  - ETL パイプライン用の型 ETLResult を定義し、kabusys.data.pipeline から再エクスポート。
  - calendar_management モジュール:
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が存在しない場合の曜日ベース（週末除外）フォールバックを採用。
    - calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索範囲やバックフィル・先読み等の定数を設定して安全性を確保。
  - pipeline モジュール:
    - ETL の設計に沿ったユーティリティ群を実装（差分取得、保存、品質チェックの取り込み方針）。
    - ETLResult データクラス（取得数・保存数・品質問題・エラー一覧・ヘルパー）を実装。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）:
    - raw_news と news_symbols を用いたニュース集約 → OpenAI（gpt-4o-mini）へのバッチ送信 → JSON レスポンスのバリデーション → ai_scores への書き込みフローを実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチサイズ、1 銘柄あたりの最大記事件数・文字数（肥大化対策）、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの堅牢なパース・バリデーション等を実装。
    - API キー（OPENAI_API_KEY）を引数で注入可能にしてテスト容易性を確保。
    - スコアは ±1.0 にクリップ、部分成功時に既存データを保護するため削除→挿入を銘柄単位で行う（トランザクション & executemany 対応）。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する score_regime を実装。
    - マクロキーワードに基づく raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）による JSON スコア取得、リトライ・フォールバック（API 失敗時 macro_sentiment=0.0）等を実装。
    - lookahead バイアス回避のため target_date 未満のデータのみを使用する設計方針を明確化。
    - DB へは冪等に BEGIN / DELETE / INSERT / COMMIT を用いて書き込み、失敗時に ROLLBACK を試行。

- Research モジュール (kabusys.research)
  - factor_research:
    - Momentum（1M/3M/6M リターン・200 日 MA 乖離）、Value（PER・ROE）、Volatility（20 日 ATR）等のファクター計算関数（calc_momentum, calc_value, calc_volatility）を実装。
    - DuckDB SQL を用いて高速に計算し、データ不足時の None 扱いを明確化。
    - 計算範囲バッファやウィンドウサイズ等の定数を設定。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、検証付き）、IC（スピアマンランク相関）計算 calc_ic、rank ユーティリティ、統計サマリー factor_summary を実装。
    - 外部依存を持たず標準ライブラリのみで実装。
  - research パッケージの __all__ に主要関数を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security / Operational notes
- OpenAI API キーは環境変数 OPENAI_API_KEY を利用。ニュース/レジーム機能は API キーが未設定の場合 ValueError を送出するようになっているため、運用時はキー設定を忘れないこと。
- .env 自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後にテスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すること。
- DB 書き込みはトランザクションを使用しており、例外発生時には ROLLBACK を試行する設計。ただし ROLLBACK 自体が失敗した場合は WARN ログに記録される。

### Design decisions / 注意点
- ルックアヘッドバイアス防止: 多くの分析 / AI 処理関数は datetime.today() や date.today() を直接参照せず、明示的に target_date を受け取る設計。
- フォールバックポリシー: カレンダーデータ未取得時は曜日ベースのフォールバック（土曜・日曜を非営業日）で動作し、DB に一部しか登録がない場合でも next_trading_day / prev_trading_day と整合する結果を返すよう実装。
- AI 呼び出し: JSON mode を使った厳密な JSON 出力を期待しているが、万が一余計な前後テキストが混入した場合に備えて復元ロジック（最外の {} を抽出）を実装。
- 部分失敗の保護: AI スコア書き込みは、失敗した銘柄で既存スコアを消さないよう、書き込み対象の code を限定して DELETE → INSERT を行う。

### Known issues / TODO
- PBR・配当利回りなどの一部バリューファクターは未実装（calc_value で注記あり）。
- news_nlp / regime_detector ともに OpenAI への依存があり、API コストやレート制限に注意が必要。
- DuckDB executemany はバージョン依存の挙動があるため、空リストを渡さない等のガードを実装しているが、環境差異のテストが必要。

---

（注）この CHANGELOG は提供されたソースコードから機能・設計意図を推測して作成したものです。実際のリリースノート作成時はコミット履歴や変更差分、リリース当時の決定事項に基づいて調整してください。