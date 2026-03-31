# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。  
現在のパッケージバージョン: 0.1.0

## [0.1.0] - 2026-03-31

初期リリース。日本株自動売買システムのコアライブラリを公開します。以下の主要機能と設計上の重要点を含みます。

### 追加 (Added)
- パッケージ基礎
  - パッケージエントリポイントを追加（kabusys.__init__）。主要サブパッケージを公開: data, research, ai, monitoring, strategy, execution（実装済み/エクスポート済みのものを含む）。
  - バージョン: 0.1.0 を設定。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート判定: .git または pyproject.toml）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - 高度な .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - 必須設定チェックを提供する Settings クラス（プロパティ経由で取得）。主な環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb), SQLITE_PATH (デフォルト: data/monitoring.db)
    - KABUSYS_ENV (development/paper_trading/live)、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - Settings は値検証を実施し、不正値時に明確な例外を送出。

- AI 関連 (`kabusys.ai`)
  - ニュースセンチメント集計 / 銘柄別スコアリング (`news_nlp.score_news`)
    - 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して前日 06:00 〜 23:30）を対象とするウィンドウで raw_news を収集。
    - 銘柄ごとに最新記事を最大 10 件、1 銘柄あたり最大 3000 文字にトリムしてまとめ、バッチ単位（最大 20 銘柄）で OpenAI (gpt-4o-mini) に JSON モードで送信。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフ（最大試行回数を設定）。
    - レスポンスの堅牢なバリデーションとスコアクリッピング（±1.0）。部分成功に備え、書き込み時は既存コードのみ置換（DELETE → INSERT）することで部分失敗時のデータ保護を実現。
    - API キー未設定時は ValueError を送出。
  - 市場レジーム判定 (`ai.regime_detector.score_regime`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジームを 'bull' / 'neutral' / 'bear' で判定。
    - マクロニュースは raw_news のマクロキーワードでフィルタ（キーワードリスト内蔵）。
    - OpenAI 呼び出しは独立実装。API レスポンスパース失敗や API 障害時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。OpenAI API キー未設定時は ValueError。

- データ処理・ETL (`kabusys.data`)
  - ETL 結果のデータクラス `ETLResult` を公開（kabusys.data.etl から再エクスポート）。
  - ETL パイプライン基盤 (`data.pipeline`)
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）を想定した ETLResult を提供。
    - DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティを実装。
  - マーケットカレンダー管理 (`data.calendar_management`)
    - market_calendar を基に営業日判定ロジックを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベース（平日のみ営業）でフォールバック。
    - 夜間バッチジョブ calendar_update_job を用意し J-Quants API から差分取得→保存（バックフィル、健全性チェックを含む）。

- リサーチ関連 (`kabusys.research`)
  - ファクター計算群 (`research.factor_research`)
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB 内の prices_daily / raw_financials から計算する関数を提供。
    - データ不足時は None を返す設計。返り値は (date, code) を含む辞書リスト。
  - 特徴量探索 (`research.feature_exploration`)
    - 将来リターン計算（任意ホライズン：デフォルト [1,5,21]）: calc_forward_returns
    - IC（Spearman ランク相関）計算: calc_ic（最小有効レコード数 3）
    - ランク関数（同順位は平均ランク）: rank
    - ファクター統計サマリ: factor_summary
    - 実装は標準ライブラリのみで DuckDB を使用、pandas 等に未依存。

### 変更 (Changed)
- 設計方針・ベストプラクティスの適用
  - すべての分析/スコアリング関数で datetime.today() / date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。外部から target_date を明示的に渡す方式を採用。
  - DuckDB を中心としたデータアクセスに統一。SQL と Python ロジックの組合せでパフォーマンスと互換性を重視。
  - OpenAI 呼び出し部分はテストしやすいように内部関数を patch できる形で抽象化（例: _call_openai_api を unittest.mock.patch で差し替え可能）。

### 修正 (Fixed)
- .env 読み込みの堅牢化
  - ファイル読み込み失敗時に warnings.warn を発行して安全に継続するように実装。
  - .env の行パースで export, 引用符、バックスラッシュエスケープ、インラインコメントなどの一般的なパターンに対応。

### 注意事項 / マイグレーションノート (Notes)
- 必要な外部リソース・前提
  - DuckDB（接続オブジェクトを関数に渡す前提）、OpenAI Python SDK（OpenAI クライアントを利用）、J-Quants クライアントモジュール（data.jquants_client）を利用。
  - OpenAI API キーは関数呼び出し時に引数として渡すか、環境変数 `OPENAI_API_KEY` を設定する必要がある。未設定の場合、score_news / score_regime は ValueError を送出する。
  - J-Quants 用のトークンや kabu API のパスワード、Slack トークンなどは Settings で必須指定となる（未設定時は ValueError）。
- 自動 .env ロード
  - 開発時の利便性のためプロジェクトルートの .env/.env.local を自動ロードするが、テスト等で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すること。
- データベーススキーマ
  - 各モジュールは特定の DuckDB テーブル（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime など）を前提としている。実運用前にスキーマ準備が必要。
- フェイルセーフ設計
  - AI API 呼び出し失敗時（リトライ上限到達、パース失敗等）は例外を投げずにデフォルト値（macro_sentiment=0.0、スコア未取得 → スキップ）で継続する実装方針。部分失敗時にも既存データを極力保護する（書き込みはコードを絞って DELETE → INSERT）。

### テスト・拡張性
- OpenAI 呼び出しは内部で _call_openai_api を使うため、unittest.mock.patch による差し替えが可能（テスト容易性を考慮）。
- DB 操作は冪等化（DELETE→INSERT、ON CONFLICT 的保存）を意識しており、部分失敗を考慮した実装になっている。

---

未記載の細かな実装や内部 API 仕様についてはソースコードの docstring を参照してください。質問があれば、特定モジュールについての詳細な変更説明や使用例（サンプルコード）を追加で作成します。