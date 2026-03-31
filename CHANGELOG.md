# Changelog

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。  
配布済みバージョンはセマンティックバージョニングに従います。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed / Deprecated / Security: 必要に応じて使用

## [0.1.0] - 2026-03-31

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基盤機能群を追加。
  - パッケージ公開バージョンは `kabusys.__version__ = "0.1.0"`。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数からの設定値自動読み込み機能を実装。
    - 自動読み込みの探索はパッケージファイル位置からプロジェクトルート（`.git` または `pyproject.toml`）を辿って判定。CWD に依存しない方式。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 環境変数自動読み込みを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサーの実装:
    - `export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント処理に対応。
    - 不正行や空行、コメントを安全にスキップ。
  - `Settings` クラスを提供（単一インスタンス `kabusys.config.settings`）。
    - J-Quants / kabuAPI / Slack / DB パス 等のプロパティを用意。
    - `env`（development, paper_trading, live）と `log_level` の値検証を実装。
    - 必須値未設定時は明確な `ValueError` を送出する設計。

- AI モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`kabusys.ai.news_nlp`)
    - 指定タイムウィンドウ（JST 前日15:00〜当日08:30）に基づく記事集約、銘柄ごとのテキスト結合・トリムを行い、OpenAI（gpt-4o-mini, JSON mode）でバッチ評価。
    - バッチサイズ、記事上限、文字数上限、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンスの厳密なバリデーションを実施（JSON抽出、型検証、未知コードの無視、数値検証、スコアの ±1.0 クリップ）。
    - スコアは `ai_scores` テーブルへ冪等的に書き込む（部分失敗時に既存スコアを保護するためコード単位で DELETE → INSERT）。
    - テストしやすさのため、OpenAI 呼び出しは差し替え可能（モックポイントを用意）。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF（1321）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し `market_regime` テーブルへ冪等書き込み。
    - マクロ記事抽出はニュース NLP のウィンドウ関数を利用（キーワードフィルタ）。
    - OpenAI 呼び出しは独立実装（モジュール間でプライベート関数を共有しない設計）。
    - API エラー・パースエラー時はフェイルセーフとして macro_sentiment = 0.0 を採用し処理継続。
    - リトライ・バックオフ、非5xx と 5xx の扱いを分離した堅牢な実装。

- データ関連モジュール (`kabusys.data`)
  - ETL パイプライン（`kabusys.data.pipeline`）
    - 差分取得、保存（Idempotent）、品質チェックの骨格を実装。
    - ETL 実行結果を表す dataclass `ETLResult` を提供（品質問題・エラー収集、to_dict によるシリアライズをサポート）。
    - テーブル存在チェック、最大日付取得ユーティリティを追加。
    - デフォルトのバックフィル日数などの設定を定義（安全な初期読み込みや修正取り込みを想定）。
  - カレンダー管理（`kabusys.data.calendar_management`）
    - JPX カレンダーの夜間差分取得ジョブ（`calendar_update_job`）を実装。J-Quants クライアント経由で取得 → `market_calendar` へ保存（保存件数を返す）。
    - 営業日判定 API を公開:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB にカレンダーがない場合は曜日ベースのフォールバック（週末除外）で一貫性を保つ。
    - 最大探索日数の上限を設けて無限ループを防止。バックフィル・健全性チェックを実装。

- リサーチモジュール (`kabusys.research`)
  - ファクター計算（`kabusys.research.factor_research`）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）などを計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB による SQL + Python の組合せで効率的に処理。結果は (date, code) をキーとする dict リストで返却。
    - データ不足時の None 扱い、ログ出力を実装。
  - 特徴量探索（`kabusys.research.feature_exploration`）
    - 将来リターン計算（calc_forward_returns、ホライズン指定・入力検証あり）。
    - IC（Information Coefficient）計算（スピアマンの ρ、rank を内部実装）。
    - ランク変換、統計サマリー関数（factor_summary）を提供。
    - pandas 等の外部ライブラリに依存しない純標準ライブラリ実装を採用。

- パッケージ公開 API
  - 主要サブパッケージをエクスポート: `kabusys.data`, `kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring`（`__all__` に設定）。
  - AI、data、research 各モジュールで外部から利用可能な関数・クラスを整備（例: `kabusys.ai.score_news`, `kabusys.ai.score_regime`, `kabusys.data.pipeline.ETLResult`, `kabusys.config.settings` など）。

### Changed
- 初期リリースのため、既存コードからの「変更」はなし。今後のリリースで API 安定化および互換性ポリシーを明確化予定。

### Fixed
- 初期リリースのため、過去のバグ修正は無し（ただし設計上、API失敗時のフォールバックやリトライ・ロールバック処理など堅牢性を意識した実装を導入）。

### Notes / Known limitations
- OpenAI クライアントの利用に際しては `OPENAI_API_KEY` の設定が必須。API キーが未設定の場合、`ValueError` を発生させる設計。
- DuckDB との相互作用で一部バインド（リストの executemany 等）に互換性差異があるため、空リストを渡すと失敗する DB バージョンに配慮した実装（空チェックを挟む）になっている。
- 時刻処理は意図的に timezone-naive（UTC 前提）で統一。JST/UTC の変換はコメント・処理で明示しているが、運用時は DB に保存されているタイムゾーンに注意すること。
- 本バージョンは研究／データ基盤の機能をメインに提供しており、実際の発注ロジック（strategy / execution）の実装は今後のリリースで追加・公開予定（public エクスポートは用意済み）。

---

今後のリリースでは以下を想定しています:
- strategy / execution の実装と、モックを使った統合テストの追加
- CI での DuckDB テストセットアップ、OpenAI 呼び出しのテスト戦略改善
- API の安定化に伴う Breaking Changes の明示的な移行ガイド

（以上）