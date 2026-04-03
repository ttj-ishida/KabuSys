# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」規約に準拠しています。

- リリース日付形式: YYYY-MM-DD
- 初期リリース: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-03

### Added
- 初回リリース。パッケージ名: `kabusys`（__version__ = 0.1.0）。
  - パブリック API（パッケージエクスポート）: data, strategy, execution, monitoring。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env / .env.local 自動読み込み機能を実装。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索して決定。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサは `export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメント処理をサポート。
  - .env 読み込み時の `override` / `protected`（OS環境変数保護）ロジックを実装。
  - `Settings` クラスを提供し、主な設定をプロパティ経由で取得可能:
    - J-Quants / kabu ステーション用トークン・パス等（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL）。
    - LINE Messaging API 設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）と監視用ファイルパス（PID_FILE_PATH, KILL_FLAG_PATH）および kill-flag の初期クリアフラグ。
    - システム監視閾値のデフォルト（CPU/MEM/DISK）。
    - 環境種別検証（development / paper_trading / live）と LOG_LEVEL 検証。
    - 環境判定補助（is_live / is_paper / is_dev）。
  - 必須環境変数未設定時は明確な ValueError を送出する `_require` 実装。

- データ関連モジュール (`kabusys.data`)
  - ETL の公開インターフェース (`kabusys.data.etl`) と `ETLResult` のデータクラス定義（pipeline.ETLResult を再エクスポート）。
  - ETL パイプライン基盤 (`kabusys.data.pipeline`):
    - 差分取得、バックフィル、品質チェック統合を想定した ETLResult データ構造。
    - DuckDB を用いた最大日付取得等のユーティリティを実装。
    - デフォルトのバックフィル日数／カレンダー先読み等を定義。
    - 品質チェック（quality モジュール利用）の問題を収集し、呼び出し側で判断する方針。
  - マーケットカレンダー管理 (`kabusys.data.calendar_management`):
    - market_calendar テーブルを基に営業日判定・前後営業日探索・期間内営業日列挙を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB 登録データがない場合は「土日を非営業日」とするフォールバックを採用。
    - calendar_update_job を実装し J-Quants から差分取得 → 冪等保存（ON CONFLICT / upsert を想定）：
      - バックフィル、健全性チェック（将来日付が過大な場合のスキップ）を実装。

- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`):
    - モメンタム: calc_momentum（1M/3M/6M リターン、200日 MA 乖離）
    - ボラティリティ/流動性: calc_volatility（20日 ATR、相対 ATR、平均売買代金、出来高比）
    - バリュー: calc_value（PER, ROE、raw_financials からの財務取得）
    - 全関数は DuckDB の prices_daily / raw_financials のみ参照し、外部 API に依存しない設計。
  - 特徴量探索 (`kabusys.research.feature_exploration`):
    - 将来リターン計算: calc_forward_returns（任意ホライズン対応、入力検証あり）
    - IC（Information Coefficient）計算: calc_ic（Spearman 相当のランク相関）
    - ランク化ユーティリティ: rank（同順位は平均ランク対応、丸め処理あり）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
    - pandas 等の外部依存を持たない実装。

- AI / NLP モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`kabusys.ai.news_nlp`):
    - score_news を実装し raw_news + news_symbols から銘柄毎に記事を集約、OpenAI (gpt-4o-mini) にバッチ送信してセンチメントを取得。
    - JSTベースのニュースウィンドウ（前日15:00 JST ～ 当日08:30 JST）を UTC 変換して DB クエリに使用。
    - 1銘柄あたり最大記事数・文字数制限、チャンク単位（最大20銘柄）での API 呼び出し、JSON Mode レスポンス検証、スコアの ±1.0 クリップ。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）と指数バックオフ、失敗時は個別チャンクをスキップして継続するフェイルセーフ設計。
    - OpenAI 呼び出し箇所はテストのために差し替え可能（内部関数を patch 可能）。
    - DuckDB の executemany 空リスト制約への対応（空時は呼ばない）。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`):
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム判定（bull/neutral/bear）。
    - マクロニュースは raw_news からマクロキーワードで抽出し、OpenAI（gpt-4o-mini）で JSON 出力を要求して macro_sentiment を取得。
    - API 失敗時は macro_sentiment=0.0 とするフォールバック、リトライ/バックオフ実装あり。
    - 帳票的に market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - ルックアヘッドバイアス回避のため内部で datetime.today()/date.today() を参照しない実装方針を採用。
  - ai パッケージは `score_news` をエクスポート。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- 環境変数が必須な項目は明示的に ValueError を送出し、欠落に対して失敗を早期に検出。
- .env の読み込みはデフォルトで行うが、テスト等のため環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションを用意。

### Notes / 実装上の重要な設計決定（ドキュメント的メモ）
- DuckDB を中心にデータ操作を行う前提（全テーブル操作は DuckDB 接続を受け取る）。
- ルックアヘッドバイアス回避: AI スコアリングやレジーム判定など時間依存処理はいずれも target_date を明示的に受け取り、内部で date.today() を使わない。
- OpenAI 呼び出しに関する堅牢化:
  - レスポンスパースエラーや API 障害に対しては基本的に例外を全面伝播させず、フェイルセーフ（0.0等）で継続する設計。
  - テスト容易性を確保するため内部呼び出し関数の差し替えを想定。
- DuckDB の executemany に関する互換性対応（空リスト渡さないガード）。
- 市場カレンダーが未整備な場合は曜日ベースのフォールバックを利用し、next/prev/get_trading_days の振る舞いが一貫するよう実装。

### Known issues / 今後の検討点
- OpenAI API キーや各種トークンは環境変数管理が前提。運用時の秘密管理（Vault 等）導入は検討余地あり。
- news_nlp/regime_detector の LLM プロンプトやモデル選択は将来的にチューニング可能（現状 gpt-4o-mini を想定）。
- 一部の SQL/実装は DuckDB のバージョン差分に敏感な箇所があり、互換性テストが必要（特に配列バインドや executemany の挙動）。
- strategy, execution, monitoring パッケージの公開はあるが、本リリースでの実装詳細は限定的（各モジュールの追加・拡張は今後のリリースで実施予定）。

---

（注）本 CHANGELOG は提示されたコードベースからの推測に基づいて作成しています。実際のリリースノートや公開 API と差異がある場合は適宜修正してください。