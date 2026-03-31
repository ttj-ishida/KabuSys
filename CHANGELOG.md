CHANGELOG
=========

すべての注目すべき変更点をこのファイルで管理します。本ファイルは「Keep a Changelog」の形式に準拠します。
バージョン番号はパッケージの __version__ (src/kabusys/__init__.py) を基にしています。

[0.1.0] - 2026-03-31
-------------------

Initial release — 日本株自動売買 / 研究・データ基盤の初期実装。

Added
- パッケージ基盤
  - パッケージ初期化を追加（kabusys.__init__）: __version__ = "0.1.0"、主要サブパッケージを __all__ で公開。
- 環境設定 (kabusys.config)
  - .env 自動読み込み機能を実装:
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを扱う堅牢な実装。
    - 既存の OS 環境変数を保護する protected set を用いた上書き制御。
  - Settings クラスを実装してアプリケーション設定を型付きプロパティで取得:
    - J-Quants / kabuステーション / Slack / DB（DuckDB / SQLite） / 監視閾値 / ログレベル / 環境モード（development/paper_trading/live）等のプロパティを提供。
    - 必須環境変数未設定時は明確な ValueError を送出。
    - env / log_level のバリデーションを実装。
- AI（自然言語処理） (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news):
    - タイムウィンドウ計算 (前日15:00 JST ～ 当日08:30 JST を UTC に変換) を提供する calc_news_window。
    - raw_news と news_symbols を用いて銘柄ごとに記事を集約（1銘柄最大記事数・文字数によるトリムを実装）。
    - OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信（チャンクサイズ 20 銘柄）してスコア取得。
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code/score 型チェック、未知コードの無視、スコアの有限性検査）。
    - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等書き込み（DELETE→INSERT、トランザクション管理）。
    - テスト容易性のため _call_openai_api の差し替えを想定。
  - 市場レジーム判定 (regime_detector.score_regime):
    - ETF 1321 の 200 日移動平均乖離 (ma200_ratio) とマクロセンチメント（LLM）を合成して日次レジーム（bull/neutral/bear）を判定。
    - 重み付け: MA 系 70%、マクロセンチメント 30%（スコア合成後クリップ）。
    - マクロキーワードで raw_news をフィルタ、OpenAI（gpt-4o-mini）で JSON 応答を期待。
    - API 失敗時は macro_sentiment=0.0（フェイルセーフ）。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）およびロールバック処理。
- データ基盤 (kabusys.data)
  - カレンダー管理 (calendar_management):
    - market_calendar を基に営業日判定・前後営業日探索・期間内営業日取得・SQ判定などのユーティリティを実装。
    - DB 未登録日は曜日ベース（平日）でフォールバックする一貫した挙動。
    - calendar_update_job を実装し、J-Quants から差分取得して market_calendar を冪等更新（バックフィル・健全性チェック付き）。
  - ETL パイプライン (pipeline, etl):
    - ETLResult データクラスを公開（target_date、取得/保存件数、品質問題、エラー一覧などを含む）。
    - pipeline モジュール設計: 差分更新、backfill（デフォルト 3 日）、品質チェック（quality モジュール連携）等の方針を反映。
    - etl モジュールは pipeline.ETLResult を再エクスポート。
- 研究／リサーチ (kabusys.research)
  - ファクター計算 (factor_research):
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率（NULL 処理を考慮）。
    - calc_value: raw_financials の target_date 以前の最新財務データを使った PER / ROE 計算。
    - 各関数は DuckDB SQL を中心に実装し、lookback バッファを確保（ルックアヘッドバイアス回避）。
  - 特徴量探索 (feature_exploration):
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算、horizons 入力検証あり。
    - calc_ic: スピアマンランク相関（IC）計算（十分なサンプルがない場合は None）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクとなるランク関数（丸め対策あり）。
  - 研究モジュールは内部ユーティリティ（データ参照限定）を前提に設計。
- 共通設計上の注意点（全体）
  - ルックアヘッドバイアス防止のため、主要処理は datetime.today() / date.today() を直接参照しない設計。
  - DuckDB をデータ層として想定、トランザクション（BEGIN/COMMIT/ROLLBACK）を明示的に使用して冪等性・整合性を確保。
  - OpenAI 呼び出しは再試行・タイムアウト・エラーハンドリングを備え、テスト時のモック差し替えを想定。
  - ロギングを適所に配置し、失敗時は警告/情報を出力して可能な限り処理を継続するフェイルセーフ方針。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Deprecated
- N/A（初回リリース）

Removed
- N/A（初回リリース）

Security
- 外部 API キー（OpenAI/J-Quants 等）は環境変数で管理。必須キー未設定時は明確な例外を発するように実装。

Known limitations / Notes
- 実行には以下の外部依存・前提が存在します:
  - DuckDB スキーマ（prices_daily / raw_news / news_symbols / ai_scores / market_calendar / raw_financials 等）の存在。
  - OPENAI_API_KEY（または api_key 引数）、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、Slack トークン等の環境変数。
  - jquants_client（DataPlatform 連携）の実装は外部に依存。
- news_nlp / regime_detector は gpt-4o-mini の JSON Mode を前提にプロンプト/応答を厳格に扱うため、モデル仕様変更や API レスポンス差異に対しては追加対応が必要になる可能性があります。
- 一部のモジュール実装はテスト用に差し替え可能な内部関数（例: _call_openai_api）を用意していますが、外部 API 呼び出しを伴う箇所の単体テストはモックを推奨します。

作者注 / 今後の予定（想定）
- strategy / execution / monitoring の実装と統合（発注ロジック・実行モニタリング）。
- DB スキーマのマイグレーションスクリプト、サンプルデータ、CI 用のテストケース整備。
- OpenAI モデルの切り替えやローカル推論器との互換性強化。