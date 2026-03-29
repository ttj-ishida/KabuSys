# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買 / データプラットフォームのコア機能を実装しています。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として公開。
  - エクスポートモジュール: data, strategy, execution, monitoring を __all__ に追加。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロードを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは .git または pyproject.toml を基準に自動検出（CWD 非依存）。
    - 自動読み込みを無効にするためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサを実装（コメント、export プレフィックス、引用符とエスケープ対応、インラインコメント取り扱い等）。
  - 環境変数上書きポリシー:
    - override フラグと protected セットにより OS 環境変数保護に対応。
  - Settings クラスで主要設定をプロパティ化して提供:
    - J-Quants / kabuステーション / Slack / DB パス / システム設定など
    - デフォルト値（例: KABUS_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH）を提供
    - KABUSYS_ENV (development / paper_trading / live) と LOG_LEVEL の入力検証
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI (gpt-4o-mini) に JSON mode でバッチ評価を依頼。
    - タイムウィンドウ定義（JST基準: 前日 15:00 ～ 当日 08:30、UTC に変換して処理）。
    - 1チャンク最大 20 銘柄、各銘柄は最新 10 記事・最大 3000 文字にトリム。
    - リトライポリシー（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
    - 成功した銘柄のみ ai_scores テーブルへ置換（DELETE → INSERT、部分失敗時の既存データ保護）。
    - テスト容易性: OpenAI 呼び出しをラップして unittest.mock.patch による差し替えを想定。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull / neutral / bear）を判定して market_regime テーブルへ冪等書き込み。
    - マクロニュースは news_nlp.calc_news_window と raw_news を用いて抽出。
    - OpenAI 連携は gpt-4o-mini、JSON 出力を想定。失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - API エラーに対するリトライとログ出力。DB 書込みは BEGIN/DELETE/INSERT/COMMIT の冪等操作、失敗時は ROLLBACK を試行。

- リサーチ / ファクター分析 (kabusys.research)
  - factor_research:
    - モメンタム (1M/3M/6M)、200日移動平均乖離、ATR、流動性（20日平均売買代金・出来高比率）などのファクターを DuckDB 上で計算。
    - raw_financials を用いたバリューファクター（PER・ROE）の計算。
    - 欠損やデータ不足時の None ハンドリング。
  - feature_exploration:
    - 将来リターン計算 (calc_forward_returns)：複数ホライズンのリターンを一度のクエリで取得。
    - IC (calc_ic)：スピアマンランク相関（ランクは同順位を平均ランクで処理）。
    - 統計サマリー (factor_summary)：count/mean/std/min/max/median を算出（None を除外）。
    - rank ユーティリティ：丸めによる ties の安定化を含むランク計算。
  - research パッケージは必要なユーティリティ（zscore_normalize の再エクスポート等）をまとめて公開。

- データプラットフォーム / ETL (kabusys.data)
  - calendar_management:
    - market_calendar テーブルを利用した営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合は曜日ベース（土日休）でフォールバックする一貫したロジック。
    - 夜間バッチ更新 job (calendar_update_job)：J-Quants から差分取得 → 保存、バックフィル、健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（target_date, fetched/saved counts, quality issues, errors 等を集約）。
    - ETL パイプライン設計に基づくユーティリティ群（差分取得、保存、品質チェックを想定）。
    - DuckDB テーブル存在確認や最大日付取得の補助関数を実装。
  - jquants_client などの外部クライアントはモジュール境界で扱い、save_* / fetch_* を通じて冪等保存を行う設計。

### Changed
- 設計原則・実装ポリシー（全体）
  - ルックアヘッドバイアス回避のため、datetime.today()/date.today() をアルゴリズム内部で直接参照しない設計を採用（target_date に依存した計算）。
  - 外部 API（OpenAI / J-Quants）呼び出しはフェイルセーフ（失敗時に処理継続）とし、致命的例外は上位へ伝播する運用とする（ログに注記）。
  - テスト容易性を重視して、OpenAI 呼び出しを内部ラッパーで分離しモック可能にした。
  - DuckDB のバージョン差異（executemany の空リスト等）に対する互換性処理を導入。

### Fixed
- N/A（初回リリースのため特定のバグ修正履歴はなし）

### Removed
- N/A（初回リリースのためなし）

### Security
- 注意事項:
  - OpenAI API キーは環境変数 OPENAI_API_KEY または各関数の api_key 引数で渡す必要がある。未設定時は ValueError を送出する実装（悪用防止のためキーが明示的に必要）。
  - .env 自動ロードはデフォルト有効。CI/テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を利用すること。

### Notes / Usage hints
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings の各プロパティ参照）
- DB デフォルトパス:
  - DUCKDB_PATH defaults to data/kabusys.duckdb
  - SQLITE_PATH defaults to data/monitoring.db
- OpenAI 呼び出しの挙動:
  - JSON mode を利用し、レスポンスが不正な場合はスコア 0.0 を採用して処理を続行するフェイルセーフ実装。
- テスト面:
  - news_nlp/regime_detector の OpenAI 呼び出しは内部関数をモック可能（unittest.mock.patch の想定パスをコード内コメントで明示）。

---

今後のリリースで想定している改善点（予定）
- strategy / execution / monitoring モジュールの具体的な売買ロジックと実行層の追加
- J-Quants / kabu ステーションのクライアント拡張と認証ワークフローの整備
- より細かなログ/メトリクス出力と運用用ダッシュボード連携

（以上）