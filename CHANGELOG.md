# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従っています。  
セマンティック バージョニングを使用します。

## [0.1.0] - 2026-03-28

### Added
- 初回リリース。日本株自動売買・データ基盤向けのコアライブラリを追加。
  - パッケージエントリポイント
    - `kabusys.__version__ = "0.1.0"`
    - `__all__` に主要サブパッケージを公開: `data`, `strategy`, `execution`, `monitoring`
- 環境設定/ロード機能（kabusys.config）
  - `.env` / `.env.local` ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - プロジェクトルート判定は `.git` または `pyproject.toml` を上位ディレクトリから探索して決定（CWD に依存しない）。
  - `.env` パーサの強化:
    - コメント・空行を無視
    - `export KEY=val` 形式に対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - クォートなしでの行末コメント処理（直前が空白/タブの場合のみ）
  - 環境変数取得用の `Settings` クラスを提供（プロパティ経由）:
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティ（必須項目は未設定時に ValueError を送出）
    - `KABUSYS_ENV` の検証（`development` / `paper_trading` / `live`）
    - `LOG_LEVEL` の検証（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`）
    - `is_live` / `is_paper` / `is_dev` のユーティリティプロパティ
- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成
    - OpenAI（gpt-4o-mini）を用いたバッチ評価（JSON Mode）を実装
    - バッチサイズ、記事数・文字数制限（トークン肥大化対策）、チャンク処理を実装
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ実装
    - レスポンスバリデーション（JSON パース回復処理、results 配列検査、コード/スコア検証）
    - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的に書き換え（DELETE → INSERT）
    - テスト容易性のため内部の OpenAI 呼び出し関数をモック可能に設計
    - 時間ウィンドウ計算ユーティリティ `calc_news_window(target_date)` を提供（JST ベース → UTC naive datetime を返す）
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（`bull`/`neutral`/`bear`）を判定
    - MA 計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）による JSON 出力取得とパース
    - API エラーやパース失敗時はフェイルセーフで macro_sentiment=0.0 を使用
    - 冪等的に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - リトライポリシー（最大試行回数、指数バックオフ）
- データ関連（kabusys.data）
  - ETL パイプラインインターフェース（kabusys.data.pipeline）
    - ETL 実行結果を表すデータクラス `ETLResult` を追加（取得件数、保存件数、品質問題、エラー一覧など）
    - DB 最大日付取得、テーブル存在チェック等のユーティリティを実装
    - 市場カレンダー補助（_adjust_to_trading_day 等の内部関数の土台を実装）
  - calendar 管理（kabusys.data.calendar_management）
    - JPX カレンダーの取得・管理ロジックを実装
    - 営業日判定 API:
      - `is_trading_day(conn, d)`, `is_sq_day(conn, d)`
      - `next_trading_day(conn, d)`, `prev_trading_day(conn, d)`
      - `get_trading_days(conn, s, e)`
    - データがない場合は曜日（平日）ベースでフォールバック
    - 夜間バッチ更新ジョブ `calendar_update_job(conn, lookahead_days)` を実装（J-Quants クライアント呼び出し、バックフィル、健全性チェック）
  - ETL 再エクスポート（kabusys.data.etl）:
    - `ETLResult` を再エクスポート
- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: `calc_momentum(conn, target_date)`（1M/3M/6M リターン、MA200 乖離）
    - ボラティリティ/流動性: `calc_volatility(conn, target_date)`（20日 ATR、相対 ATR、平均売買代金、出来高比率）
    - バリュー: `calc_value(conn, target_date)`（PER、ROE）
    - DuckDB を用いた SQL ベース実装。prices_daily / raw_financials テーブルのみ参照（実際の発注 API へアクセスしない設計）
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: `calc_forward_returns(conn, target_date, horizons=[...])`
    - IC（Information Coefficient）計算: `calc_ic(factor_records, forward_records, factor_col, return_col)`（Spearman の ρ じっさいのランク相関を計算）
    - ランク関数 `rank(values)`（同順位は平均ランク）
    - 統計サマリー `factor_summary(records, columns)`（count/mean/std/min/max/median）
  - `kabusys.research.__init__` で主要 API をエクスポート（`zscore_normalize` は data.stats から再エクスポート）
- テスト設計の配慮
  - OpenAI 呼び出し部分を個別関数 `_call_openai_api` として切り出し、unittest.mock で差し替えやすく設計

### Changed
- 初期リリースのため変更履歴は特になし（初出の機能追加中心）。

### Fixed
- 初期リリースのため修正履歴は特になし。

### Notes / Requirements / Database expectations
- 必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AI 機能利用時）
- DuckDB スキーマ（想定される主なテーブル）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar, など
  - 各モジュールはこれらのテーブル構造に依存（テーブル/カラム名はコード内クエリ参照）
- OpenAI との連携
  - gpt-4o-mini を利用する前提
  - レスポンスは JSON Mode（厳密な JSON）を期待するが、パース耐性を持つ実装
- フェイルセーフ方針
  - 外部 API エラーやレスポンスパース失敗時は例外を投げずフェイルセーフ（ログ出力して処理を継続/0扱い）する箇所があるため、呼び出し側での結果確認（返り値・ログ）を推奨

---

今後の予定（例）
- テーブル作成スクリプトやマイグレーション、サンプルデータ・統合テストの追加
- strategy / execution / monitoring の具体的実装（現状はパッケージ骨子をエクスポート）
- OpenAI モデル/パラメータのチューニングおよび追加の品質チェック機能

（この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートはビルド・テスト結果に基づき調整してください。）