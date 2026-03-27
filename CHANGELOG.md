# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

最新更新日: 2026-03-27

## [Unreleased]
- なし

## [0.1.0] - 2026-03-27
最初の公開リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期実装。トップレベルで data / research / ai / その他モジュールを公開。
  - バージョン番号を `__version__ = "0.1.0"` として定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml を検索）。
  - .env と .env.local の読み込み順序をサポート（.env.local が優先して上書き）。
  - 読み込み無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト等で自動ロードを無効化可能）。
  - 複雑な .env パース処理を実装（export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等）。
  - 必須設定を簡単に取得する `Settings` クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 実行環境等）。
  - 設定値の検証を実装（KABUSYS_ENV の許容値、LOG_LEVEL の許容値等）。
  - デフォルトの DB パス（DuckDB, SQLite）と kabu API ベース URL を設定。

- データ層 (kabusys.data)
  - ETL インターフェース: `pipeline.ETLResult` を公開（ETL の結果集約）。
  - マーケットカレンダー管理モジュール（calendar_management）
    - market_calendar テーブルを用いた営業日判定・次/前営業日取得・営業日リスト取得。
    - DB未取得時の曜日ベースフォールバックや、最大探索日数制限を実装。
    - 夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants から差分取得して保存、バックフィル/健全性チェック等）。
  - ETL パイプライン基盤（pipeline）
    - 差分取得、保存、品質チェックのためのユーティリティと ETLResult クラスを実装。

- 研究用ユーティリティ (kabusys.research)
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、200日MA乖離）
    - ボラティリティ / 流動性（20日ATR、ATR比、20日平均売買代金、出来高比）
    - バリュー（PER, ROE を raw_financials から取得）
    - DuckDB 上の SQL とウィンドウ関数を用いたバッチ処理を採用
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（任意のホライズン、デフォルト [1,5,21]）
    - IC（Spearman ランク相関）計算
    - ランク変換ユーティリティ、ファクター統計サマリー
  - z-score 正規化ユーティリティを data.stats から再エクスポート

- AI / NLP 機能 (kabusys.ai)
  - ニュースセンチメント（news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチで問い合わせてセンチメントスコアを生成。
    - 入力トリム（記事数・文字数の上限）、バッチサイズ、JSON Mode 利用。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）と指数バックオフ。
    - レスポンス検証（JSON パース、results 配列、既知コードのみ採用、スコア finite 判定、±1.0 でクリップ）。
    - スコア結果を ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225 連動 ETF）の 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime を参照し、結果を market_regime テーブルへ冪等書き込み。
    - LLM 呼び出しは専用実装、API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフを実装。
  - テスト容易性
    - OpenAI 呼び出しの内部関数 (_call_openai_api) は unittest.mock で差し替え可能に設計（モック可能ポイントを明示）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- API キーや機密情報は環境変数から取得する設計を採用。Settings 経由で必須キーが未設定の場合は ValueError を投げることで誤った実行を防止。

### Notes / Design Decisions / 備考
- ルックアヘッドバイアス防止
  - AI モジュール・研究モジュール共に datetime.today() / date.today() を内部処理で参照せず、必ず外部から target_date を与える設計。
  - DB クエリは target_date 未満／未満等の排他条件を明示して将来データ参照を防止。
- DuckDB を主要な分析 DB として利用（テーブル名の前提: prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials, news_symbols 等）。
- フォールバックとフェイルセーフ
  - 外部 API（OpenAI / J-Quants）失敗時は極力処理を継続し、影響範囲を限定する方針（スコアは 0.0、該当銘柄はスキップ等）。
- 互換性
  - DuckDB の executemany に関する既知の制約（空リスト不可など）に対して対処済み。
- ログ
  - 詳細なログ出力（warning/info/debug）を各処理に挿入し問題発見を容易に。

### Known issues / Limitations
- PBR や配当利回り等、一部のバリューファクターは未実装。
- OpenAI のレスポンスパースは一定のリスク（LLM の不確実性）があるため、検証ロジックで不正レスポンスを安全にスキップする実装にしているが、完全な保証はできない。
- calendar_update_job 等は J-Quants クライアント実装（jquants_client）に依存するため、それらの実装が必要。

## 既知の運用メモ（移行／設定）
- OpenAI API キーは環境変数 `OPENAI_API_KEY` または各 API 呼び出し時の引数で提供する必要あり。未設定時は ValueError が発生する。
- 自動で .env を読み込みたくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- デフォルトの DuckDB ファイルパスは `data/kabusys.duckdb`、SQLite 監視 DB は `data/monitoring.db`。必要に応じて環境変数で上書き可能（DUCKDB_PATH / SQLITE_PATH）。
- 実行環境は `KABUSYS_ENV`（development / paper_trading / live）で切替可能。`is_live`, `is_paper`, `is_dev` プロパティで判定可能。

---

今後のリリースでは、以下を予定しています（例）:
- 追加ファクター（PBR、配当利回り）の実装
- jquants_client の実装詳細と ETL ワークフローの拡充
- 発注（execution）・ストラテジー（strategy）・モニタリング（monitoring）モジュールの実装と結合テスト

（必要であれば、この CHANGELOG を英語版や詳細なコミット対応表に拡張します。）