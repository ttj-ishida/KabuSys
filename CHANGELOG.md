# Changelog

すべての重要な変更点をここに記載します。本ファイルは「Keep a Changelog」仕様に準拠します。

履歴はリリース日順（新しいものが上）で並べています。

## [Unreleased]
- 今後の予定や未リリースの変更点をここに記載します。

---

## [0.1.0] - 2026-03-28
初回リリース。日本株向けのデータプラットフォーム、リサーチ、AI スコアリング、カレンダー管理、ETL 等をまとめたライブラリの初版。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - モジュール公開: data, strategy, execution, monitoring（__all__）。

- 設定管理
  - 環境変数/.env ローダー実装（kabusys.config）。
    - プロジェクトルートを __file__ から探索して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export KEY=val 形式やクォート・コメント処理に対応したパーサ。
    - 環境変数の上書き制御（override, protected）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB / システム設定をプロパティ経由で取得。
    - 必須変数に対して未設定時は ValueError を送出。
    - 環境値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。
    - デフォルトの DB パス（duckdb/sqlite）を設定。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントスコアを取得。
    - バッチ処理（最大 20 銘柄／コール）、記事数・文字数のトリム制御、レスポンスバリデーション、スコアを ±1.0 にクリップ。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフのリトライ。
    - DuckDB へ冪等的に書き込み（DELETE → INSERT、部分失敗時に既存レコードを保護）。
    - calc_news_window で JST ベースのウィンドウ計算を提供（ルックアヘッドバイアス回避のため date 引数依存）。
    - テスト容易性のため内部の OpenAI 呼び出しを差し替え可能に設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して daily レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しは独立実装（news_nlp と共有せずモジュール結合を低減）。
    - LLM 呼び出しのリトライ／フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - 結果を market_regime テーブルに冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書込み失敗時は ROLLBACK を試みて例外を上位へ伝播。

- Data モジュール（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を基にした営業日判定ユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - データがない場合は曜日ベース（平日）をフォールバックとして使用。
    - calendar_update_job により J-Quants API から差分取得・バックフィル・健全性チェックを行い、market_calendar を更新。
    - 最大探索日数等の安全策（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）。

  - ETL / パイプライン（pipeline, etl）
    - ETLResult dataclass を公開（ETL の実行結果を構造化して返す）。
    - 差分取得、backfill、品質チェック（quality モジュール経由）を想定した設計。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。

- Research モジュール（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER, ROE）計算関数を提供。
    - SQL（DuckDB）主体の実装で外部 API にはアクセスしない。
    - データ不足時の None ハンドリング。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク/統計ユーティリティ（rank, factor_summary）。
    - pandas 等の外部依存を使わず標準ライブラリのみで実装。
  - zscore_normalize を kabusys.data.stats から再エクスポート。

### Changed
- 初期リリースのため "Changed" はなし（新規導入）。

### Fixed
- 初期リリースのため "Fixed" はなし。

### Security
- 初期リリースのため既知のセキュリティ更新はなし。
- 注意: OpenAI API キー等の機密情報は環境変数で管理する設計（.env 自動読み込みあり）。.env を誤ってコミットしないこと。

### Notes / 備考
- DuckDB を主要なローカル DB として利用する設計。DuckDB のバージョンに起因する挙動（executemany の空リスト制約など）を考慮した実装が含まれます。
- AI 関連処理は gpt-4o-mini を前提に JSON mode を使用するため、OpenAI SDK のバージョン差異に対して一部互換性の考慮（status_code の存在確認、JSON パースの復元ロジック等）を実装しています。
- 時刻/ウィンドウ計算は JST/UTC の注意を明記し、ルックアヘッドバイアス防止のため内部で date.today()/datetime.today() を直接参照しない設計になっています（caller が target_date を与える）。
- テスト容易性のため OpenAI 呼び出し関数はモジュール内部でラップしてあり、unittest.mock.patch により差し替え可能です。
- 必須の環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）を設定しないと ValueError が発生します。README/.env.example の作成を推奨。

---

今後のリリースでは以下のような項目が想定されます（実装予定・改善案）:
- strategy / execution / monitoring の具体実装（現状はパッケージ公開のみ）。
- ai モデル・プロンプト改善や並列化対応。
- ETL の品質チェック（quality モジュール）の詳細実装とアラート連携（Slack 通知等）。
- テストカバレッジ向上・CI ワークフローの整備。

--- 

（注）本 CHANGELOG は提供されたソースコードの内容から推測して作成した初期リリース向けの記述です。実際のコミット履歴や運用に基づく差分がある場合は適宜更新してください。