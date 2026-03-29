# Changelog

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠しています。  
次のバージョン体系は semver を想定しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-29

初期リリース。日本株の自動売買プラットフォーム「KabuSys」のコア機能群を実装・公開します。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョン情報を追加（__version__ = "0.1.0"）。
  - パッケージの公開モジュール一覧を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に検出し、CWD に依存しない実装。
  - .env のパース機能を強化:
    - 空行・コメント（#）スキップ、export KEY=val 形式対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理をサポート。
    - インラインコメント判定のための空白・タブルール処理。
  - .env ロードの優先順を実装: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - Settings クラスを実装し、J-Quants / kabuAPI / Slack / DB パス / 実行環境等の設定プロパティを提供。
  - 設定値のバリデーションを追加（KABUSYS_ENV の許容値、LOG_LEVEL の許容値、必須 env の _require による検証）。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp モジュール:
    - raw_news と news_symbols を使ったニュース記事の銘柄別集約。
    - タイムウィンドウ計算（JST 基準：前日 15:00 ～ 当日 08:30 相当の UTC 範囲）。
    - OpenAI（gpt-4o-mini、JSON mode）を用いたバッチセンチメント評価（最大バッチサイズ 20）。
    - 入力トリム（1 銘柄あたり最大記事数・最大文字数）やレスポンス検証・スコアクリップ（±1.0）。
    - API 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx）と指数バックオフ。
    - DuckDB への安全な書き込み（対象コードのみ DELETE → INSERT、部分失敗に配慮）。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出（マクロキーワード群）・OpenAI 呼び出し・リトライ/フェイルセーフ（API 失敗時 macro_sentiment を 0.0 にフォールバック）。
    - レジームスコアの合成ロジック、閾値設定、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - LLM 呼び出しは news_nlp と意図的に独立した実装でモジュール結合を回避。

- Data（データ基盤）モジュール（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダーの管理ロジック（market_calendar を用いる営業日判定）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - DB にカレンダーがない場合は曜日ベース（土日除外）のフォールバックを提供。
    - カレンダー取得の夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック）。
    - 最大探索日数やバックフィル期間、先読み日数、健全性チェックなどの安全装置を導入。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果の集約・品質チェック・エラー情報を保持）。
    - 差分更新・バックフィル・品質チェック・idempotent 保存を想定した ETL 基盤設計（jquants_client と quality モジュールを使用）。
    - DuckDB に依存するユーティリティ（テーブル有無チェック、最大日付取得など）を実装。
    - ETL 処理上の注意点をコード内に明記（例: DuckDB 0.10 の executemany 空リスト制約への対応など）。

- Research（研究）モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER、ROE）等のファクター計算を実装。
    - DuckDB を用いた SQL ベース実装で外部 API 呼び出しなし、結果は (date, code) ベースの dict リストで返却。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns：任意ホライズン対応）、IC（Spearman の ρ）計算、rank（同順位は平均ランク）関数、統計サマリー（factor_summary）を提供。
    - 外部ライブラリに依存せずに実装。

- モジュール公開の調整
  - kabusys.research.__init__ で主要関数を再エクスポートし、使いやすく整理。
  - kabusys.data.etl は pipeline.ETLResult を再エクスポート。

### Changed
- 設計/実装方針（全体）
  - ルックアヘッドバイアス防止のため、いずれの処理も datetime.today() / date.today() を直接参照しない設計（関数呼び出し側で target_date を渡す形）。
  - OpenAI 呼び出しに対しては JSON Mode を利用し、レスポンスの堅牢なバリデーションを行う。
  - DB 書き込みは冪等性を考慮（DELETE → INSERT、transaction での COMMIT / ROLLBACK ハンドリング）。
  - API エラー時のフェイルセーフ挙動を各所に定義（LLM 失敗時はスコア 0.0 で継続、ETL は品質問題を収集して上位で判断）。

### Fixed / Notes
- エラー・例外ハンドリング
  - OpenAI SDK の APIError について status_code の有無に対応する安全な扱いを追加（getattr を利用）。
  - DuckDB 周りの特殊制約（executemany に空リスト不可）を回避するガードを追加。
  - 各種 JSON パース失敗や API レスポンス不整合時に明確な WARN ログを出して継続する実装により、単一外部依存の障害が全体停止を引き起こさないようにしている。

### Known limitations / 注意事項
- OpenAI API キーは関数引数（api_key）で注入可能。未指定時は環境変数 OPENAI_API_KEY を使用するが、未設定の場合は ValueError を発生させる設計。
- news_nlp・regime_detector ともに gpt-4o-mini を前提にしたプロンプト設計・JSON Mode 用出力を要求するため、モデルや API 仕様の大幅な変更があると調整が必要。
- DuckDB のバージョン差異（特に配列バインドや executemany の振る舞い）に注意。コード内に互換性対策を盛り込んでいるが、実行環境の DuckDB バージョンによっては追加対応が必要となる可能性がある。
- market_calendar が未取得の場合は曜日ベースのフォールバックを行うため、祝日や SQ 日の厳密判定はカレンダー取得後でないと正確ではない。

----

もし CHANGELOG に追加してほしい詳細（例: 各関数の API シグネチャ変更点、マイグレーション手順、既知のバグや将来の改善案など）があれば指定してください。必要に応じてリリースノートの英文版も作成できます。