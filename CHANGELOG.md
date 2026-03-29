# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは "Keep a Changelog" の方針に従い、意味のある変更のみを記載します。Semantic Versioning を使用します。

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買・データ基盤・リサーチ支援を目的としたコア機能を実装しています。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージ（バージョン 0.1.0）を追加。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local の自動ロード機能を実装（プロジェクトルート探索は .git または pyproject.toml を基準）。
  - OS 環境変数を保護する読み込み順序（OS env > .env.local > .env）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードの無効化が可能。
  - .env パーサー実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント対応。
  - Settings クラスを提供: J-Quants / kabu ステーション / Slack / DB パス / 環境種別・ログレベル検証（許容値チェック・エラー時は ValueError）。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（ai_scores）を計算・保存する機能。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたり記事数・文字数制限、JSON Mode 応答のバリデーション、スコアクリップ ±1.0、エクスポネンシャルバックオフ付きリトライを実装。
    - レスポンスの救済処理（JSON に前後テキストが混入する場合の {} 抽出）を実装。
    - テスト用に _call_openai_api をパッチ可能に設計。
    - ルックアヘッドバイアス防止のため datetime.today() を参照しない設計（target_date ベース）。
  - regime_detector.score_regime: ETF (1321) の 200 日移動平均乖離とマクロニュースの LLM センチメント（news_nlp.calc_news_window と連携）を合成して市場レジーム（bull/neutral/bear）を daily に計算・market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出（マクロキーワード群）、OpenAI 呼び出し、再試行・エラーハンドリング（5xx/タイムアウト/レートリミット等）を実装。
    - API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar ベースの営業日判定／次営業日／前営業日／期間内営業日取得／SQ判定ロジックを実装。
    - DB データが不完全な場合は曜日ベース（平日）フォールバック。最大探索日数制限を導入して無限ループ回避。
    - calendar_update_job: J-Quants から差分取得して冪等保存、バックフィル・健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の取得件数・保存件数・品質問題・エラー集約）。
    - 差分更新、バックフィル、品質チェックの設計方針を盛り込んだ骨組みを提供。
  - jquants_client（参照）との連携設計を前提にした ETL 用ユーティリティ。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を銘柄別に計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務を取得して PER / ROE を計算（EPS が 0/欠損時は None）。
    - 全関数は DuckDB 接続を受け取り SQL ベースで計算（prices_daily / raw_financials のみ参照）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）で将来リターンを計算（LEAD を使用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（ties を平均ランクで処理）。
    - rank / factor_summary: ランク変換、基本統計量（count/mean/std/min/max/median）を実装。
  - 研究用ユーティリティは外部依存を避け標準ライブラリ + DuckDB のみで実装。

### Changed
- （該当なし）初回リリースのため過去の変更はありません。

### Fixed
- （該当なし）初回リリースのためバグ修正履歴はありません。

### Security
- OpenAI API キーを明示的に引数で渡すことが可能。環境変数 OPENAI_API_KEY を利用する場合は Settings/関数で明示的に参照する設計。
- .env 読み込みは OS 環境を保護する方式で行われます（既存 OS 環境変数が優先）。

### Notes / Implementation details / 制限事項
- 全体的に「ルックアヘッドバイアス防止」の設計方針を採用し、内部実装は target_date を明示的に渡すことで過去データのみを使用します。
- DuckDB を主要な格納/集計基盤として想定。関数群は DuckDB 接続を受け取るインターフェースです。
- OpenAI 呼び出しは gpt-4o-mini を使用し JSON Mode（response_format）を想定。API レスポンスの不正・ネットワーク問題は基本的にフェイルセーフ（スコアを 0.0 にするか該当銘柄をスキップ）で処理を継続します。
- news_nlp/regime_detector 内の _call_openai_api はテスト用にパッチ可能に設計されています（unittest.mock.patch で差し替え可）。
- ai_scores の書き込みは「対象コードのみ」DELETE → INSERT を行うことで部分失敗時に既存データを保護します。
- DuckDB executemany に空リストを渡せないバージョン（0.10 等）への互換性を考慮した処理を実装しています。
- 現時点で PBR・配当利回りなどのバリューファクターは未実装。

---

今後の予定（例）
- strategy / execution / monitoring のコア実装とテストカバレッジ拡充
- ai モデル評価の自動化・モデル選択機能
- ETL の実行スケジューリング・監視ジョブの統合
- 細かな性能改善と大規模データに対するチューニング

もし特定モジュール（例: news_nlp の応答バリデーションや calendar_update_job の J-Quants 統合）について詳細な変更履歴や利用上の注意を追加して欲しい場合は教えてください。