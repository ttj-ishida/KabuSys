# Changelog

すべての重要な変更履歴はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-28

初期リリース。日本株自動売買システムのコア機能群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージ識別子と公開 API を設定（kabusys.__init__、バージョン 0.1.0）。
  - モジュール構成: data, research, ai, execution, strategy, monitoring（__all__ 定義）。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local ファイルの自動読み込み機能を実装（プロジェクトルート検出は .git または pyproject.toml を基準）。
  - .env のパースを堅牢化（export 構文対応、クォート内のエスケープ、インラインコメント処理）。
  - 上書き制御（override）と OS 環境変数を保護する protected セットの仕組み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
  - Settings クラスを提供し、以下の設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL の検証
    - ヘルパーメソッド: is_live, is_paper, is_dev

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ投げ。
    - チャンク処理（最大 20 コード／API コール）と 1 銘柄あたりの文字・記事数制限（トークン肥大対策）。
    - JSON Mode を利用したレスポンス検証と堅牢なパースロジック（前後余計なテキストの取り扱い含む）。
    - 再試行（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。API 失敗時はフェイルセーフ（スキップ）で継続。
    - DuckDB への書き込みは部分置換（該当コードのみ DELETE→INSERT）で冗長性・部分失敗耐性を確保。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api をパッチ可能）。
    - 公開 API: score_news(conn, target_date, api_key=None)

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事はマクロキーワードでフィルタ（日本・米国系キーワード定義）。
    - OpenAI 呼び出しはニュースモジュールとは別実装。リトライ・フェイルセーフを備える。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
    - 公開 API: score_regime(conn, target_date, api_key=None)

- 研究（Research）モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: mom_1m / mom_3m / mom_6m、ma200_dev（200日MA乖離）
    - ボラティリティ / 流動性: atr_20（20日 ATR）、atr_pct、avg_turnover、volume_ratio
    - バリュー: per、roe（raw_financials からの最新報告）
    - DuckDB を用いた SQL ベース実装（prices_daily / raw_financials を参照）、結果は (date, code) をキーとする dict リストで返却
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト 1,5,21 営業日）に対応
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関
    - ランク変換ユーティリティ（rank）: 同順位は平均ランクで処理
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を計算
  - 研究用ユーティリティ再エクスポート（zscore_normalize など）

- データ基盤（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日ユーティリティを実装
    - DB に calendar データがない場合は曜日ベースのフォールバック（平日を営業日と見なす）を採用
    - calendar_update_job により J-Quants から差分取得し market_calendar を冪等保存（バックフィルや健全性チェックを実装）
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを導入（取得件数・保存件数・品質チェック結果・エラーの集約）
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client, quality モジュールとの連携ポイント）
    - DuckDB テーブルの最大日付取得等のユーティリティを提供
  - jquants_client への依存点を設け、fetch/save 処理を外部クライアントに委譲（J-Quants API 連携設計）

- テスト性・堅牢性に関する設計上の配慮
  - ルックアヘッドバイアス対策として datetime.today()/date.today() をコアロジック内で参照しない設計（target_date を必須引数で受け取る）。
  - OpenAI 呼び出し等をパッチ可能にして単体テストを容易にする設計。
  - DuckDB の executemany の制約（空リスト不可）に対する回避ロジックを実装。
  - 各モジュールで発生しうる API エラーに対しフェイルセーフ（デフォルト値やスキップ）を採用。

### 変更 (Changed)
- 初リリースのため該当なし。

### 修正 (Fixed)
- 初リリースのため該当なし。

### 削除 (Removed)
- 初リリースのため該当なし。

### セキュリティ / 注意事項 (Security / Notes)
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を利用する機能では OPENAI_API_KEY が必要（score_news / score_regime の api_key 引数か環境変数で指定）
- .env 自動読み込みはデフォルトで有効。.env を自動で読み込ませたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB / SQLite の既定パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db

### 既知の制限 (Known limitations)
- 一部機能（jquants_client、quality、monitoring、execution 等）はこの変更履歴の範囲で外部実装を想定しており、環境に依存する部分がある（外部 API キーや DB スキーマが必要）。
- OpenAI のレスポンスが想定外の形式の場合はスコア取得をスキップする設計（安全寄り）。必要に応じて strict モード等の追加を検討してください。

---

今後のリリースでは、運用向け監視・実行（execution, monitoring）関連の具体実装、テストカバレッジ強化、パフォーマンス改善や追加ファクターの実装を予定しています。