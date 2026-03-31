# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

最新: Unreleased

## [Unreleased]
- 今後のリリース向けに小さな改善（テストカバレッジ拡充、ドキュメント補完、エラーメッセージ改善）を予定。

---

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買プラットフォームの核となるモジュール群を提供します。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開 API の定義）。
- 設定・環境変数管理（kabusys.config）
  - .env ファイル（.env / .env.local）自動ロード機能を実装。プロジェクトルート（.git または pyproject.toml）を基準として探索。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - .env パーサ実装（コメント、export プレフィックス、クォート・エスケープ対応、インラインコメント処理）。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / データベース / ログ設定等の環境変数取得をラップ。必須キー未設定時は ValueError を発生。
  - 環境値のバリデーション（KABUSYS_ENV、LOG_LEVEL の許容値チェック）。
- データ基盤ユーティリティ（kabusys.data）
  - ETL の結果表現 ETLResult（pipeline モジュールの再エクスポート）。
  - calendar_management:
    - JPX マーケットカレンダー管理：営業日判定、翌営業日/前営業日探索、期間内営業日取得、SQ 日判定。
    - calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィル・健全性チェック付き）。
    - market_calendar がない場合の曜日ベースフォールバック実装。
  - pipeline / etl:
    - ETL パイプライン用のユーティリティ（差分取得、バックフィルの考慮、品質チェック統合のための ETLResult 等）。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティ。
- 研究（research）モジュール
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）計算関数を実装。
    - DuckDB SQL ベースでの効率的な集計を採用。データ不足時は None を返す設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランキング（rank）を実装。
    - 外部ライブラリ非依存で純粋に標準ライブラリ + DuckDB で実装。
  - research パッケージは主要関数を __all__ で公開。
- AI（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントスコアを生成して ai_scores テーブルへ保存。
    - バッチ（最大 20 銘柄/回）処理、記事トリム（最大記事数、最大文字数）によるトークン肥大化対策。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code/score の検証）とスコアの ±1.0 クリップ。
    - DuckDB の executemany の制約（空リスト不可）に配慮した安全な書き込み（DELETE → INSERT）実装。
    - API キー未設定時は ValueError を送出。
  - regime_detector.score_regime:
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（キーワードフィルタ）、OpenAI 呼び出し（retry/フェイルセーフで macro_sentiment=0.0 にフォールバック）を実装。
    - ルックアヘッドバイアスを避ける設計（date.today()/datetime.today() を参照しない、DB クエリに date < target_date 条件を使用）。
    - API 呼び出しはモジュール内で独立実装（news_nlp とプライベート関数を共有しない設計）。
- 全体設計上の注意点（実装ドキュメントに明記）
  - ルックアヘッドバイアス対策（日時参照を排除、DB クエリ条件で過去データのみ使用）。
  - DB 書き込みは冪等性を重視（BEGIN / DELETE / INSERT / COMMIT、例外時は ROLLBACK）。
  - 外部 API 失敗はフェイルセーフで継続（可能な限り例外を上位へ伝播させない設計）し、ログ出力で通知。
  - テスト容易性を考慮し、OpenAI 呼び出し部分はモック差し替えを想定（_call_openai_api の差替えでテスト可能）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI / API キーなどの取り扱いは環境変数ベース。必須キーが未設定の場合は明示的なエラーにより早期検出。

### Notes / Limitations
- 動作に必須な環境変数:
  - OPENAI_API_KEY（AI 関連機能）
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（各種機能）
- DuckDB を用いる設計のため、DuckDB のバージョン固有の挙動（executemany の空リスト挙動等）を考慮している。
- News / Regime の OpenAI 呼び出しは gpt-4o-mini を想定した JSON Mode を使用。API の挙動変更に対してはログとフェイルセーフで対応。
- 本リリースでは PBR・配当利回りなど一部のバリューファクターは未実装。

---

（以降リリースでは Added / Changed / Fixed / Deprecated / Removed / Security を追記してください）