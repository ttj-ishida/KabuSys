CHANGELOG
=========

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

[0.1.0] - 2026-03-28
-------------------

初回リリース。日本株自動売買プラットフォーム「KabuSys」の基盤機能を実装しました。主な追加点、設計上の注意点、外部依存や必要な環境変数などをまとめます。

Added
- パッケージ基盤
  - パッケージ名: kabusys。バージョン __version__ = "0.1.0" を定義。
  - 公開サブパッケージ: data, research, ai, などを __all__ で整理。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読込（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサ実装:
    - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - 上書き制御（override）と OS 環境変数保護（protected）をサポート。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得（必須変数未設定時は ValueError）。
    - J-Quants / kabuステーション / Slack / DB パスなどの設定項目を定義。
    - KABUSYS_ENV / LOG_LEVEL のバリデーションとユーティリティプロパティ（is_live / is_paper / is_dev）。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (calendar_management):
    - market_calendar テーブルを用いた営業日判定 (is_trading_day, is_sq_day)。
    - 前後営業日探索 (next_trading_day, prev_trading_day)、期間内営業日列挙 (get_trading_days)。
    - DB データが無い場合は曜日ベースでフォールバック（週末を非営業日とする）。
    - calendar_update_job: J-Quants から差分取得して冪等的に保存（バックフィル、健全性チェック、例外ハンドリング）。
  - ETL パイプライン (pipeline, etl):
    - ETLResult データクラスによる ETL 結果の構造化（品質チェック結果・エラーメッセージ含む）。
    - 差分取得、バックフィル、品質チェックの設計方針を実装用ユーティリティでサポート。
    - etl モジュールで ETLResult を公開再エクスポート。

- ニュース NLP / AI (kabusys.ai)
  - news_nlp:
    - raw_news と news_symbols を集約して銘柄ごとに記事テキストを作成。
    - OpenAI (gpt-4o-mini) の JSON Mode を用いたバッチスコアリング（最大バッチサイズ・トークン対策・チャンク処理）。
    - 再試行（429/接続エラー/タイムアウト/5xx）を指数バックオフで実装。
    - レスポンスの厳密なバリデーション（JSON パース、results リスト、code/score の検証）、スコアを ±1.0 にクリップ。
    - ai_scores テーブルへ冪等的（DELETE → INSERT）に書き込み。部分失敗時に他銘柄スコアを保護。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算ユーティリティを提供（テスト・バイアス対策に日付参照を外部化）。
  - regime_detector:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、ニュース NLP によるマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出（キーワード一覧）・LLM 呼び出し・JSON パース・リトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して上位へ例外伝播。

- リサーチ機能 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離の算出（データ不足時は None、DuckDB SQL ベース）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率など。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（最新財務レコードの取得ロジック含む）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて取得。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装。有効レコードが 3 件未満の場合は None。
    - rank: 平均ランク（同順位は平均ランク）を計算。丸めにより ties の判定を安定化。
    - factor_summary: 各列の count/mean/std/min/max/median を計算。

- 実装上の共通設計方針
  - すべての時系列計算で datetime.today() / date.today() を直接参照しない（ルックアヘッドバイアス防止）。
  - DuckDB を主要なローカル分析 DB として使用。SQL と Python を組み合わせて効率的に処理。
  - OpenAI の呼び出しはテストのためにモジュール内 private 関数を patch できるよう設計（テスト容易性の確保）。
  - API 呼び出し失敗時はフェイルセーフ（スコア 0.0、処理継続）を採用し、致命的な失敗は上位へ伝播する設計。
  - ロギングと警告を充実させて運用時のデバッグを容易に。

Fixed
- 初版のため該当なし（バグ修正履歴は今後追加）。

Changed
- 初版のため該当なし。

Security
- 環境変数から機密情報（API キー等）を取得する設計。自動読み込みを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
- Settings.require 実装により、未設定の必須環境変数は早期に検出して ValueError を送出。

Notes / Requirements / Migration
- 必須環境変数（例）
  - OPENAI_API_KEY（AI スコア/レジーム判定で必須）
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabuステーション API）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知）
  - （DB パスはデフォルトが提供されるが環境変数で上書き可能: DUCKDB_PATH / SQLITE_PATH）
- 外部依存
  - DuckDB、openai SDK（v1 系想定）などが必要。
- 自動 .env 読込はプロジェクトルート検出（.git or pyproject.toml）に依存するため、配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用するか明示的に環境変数を設定してください。

既知の制限 / 今後の課題
- 一部の DB バインドや executemany の挙動は DuckDB バージョンに依存するため、互換性テストが必要（pipeline モジュール内に注意喚起あり）。
- AI レスポンスの厳密な JSON 出力に依存しているため、モデルの挙動変化や JSON mode の仕様変更に対するフォールバック強化を検討する余地あり。
- 現時点では PBR・配当利回り等のバリューファクターは未実装（calc_value にて注記あり）。

作者
- KabuSys チーム

(以降のリリースでは Changed / Fixed / Removed / Deprecated / Security に追記します)