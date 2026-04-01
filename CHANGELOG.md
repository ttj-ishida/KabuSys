# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-01

初期リリース。日本株自動売買・データ基盤のための基本機能群を実装しました。
主要な追加点・設計方針・注意点は以下の通りです。

### Added
- 全体
  - パッケージ kabusys を v0.1.0 として公開。
  - パッケージ構成（モジュール群）を整備（data, research, ai, config など）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定値を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサを独自実装（export プレフィックス対応、クォート内のエスケープ処理、コメント取り扱いの改善）。
  - Settings クラスを提供し、必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）や各種パス・閾値・実行環境（development/paper_trading/live）を型付きプロパティで取得可能に。
  - 環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL など）。

- AI（kabusys.ai）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - OpenAI（gpt-4o-mini）を用いたニュースベースの銘柄別センチメントスコアリング機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事収集ロジック（calc_news_window）。
    - 銘柄ごとに記事を集約し、1銘柄あたり最大記事数・最大文字数でトリムしてバッチ（最大 20 銘柄/コール）で API に送信。
    - JSON Mode を利用した厳格なレスポンス検証とフォールバック（パース失敗時は該当チャンクをスキップ）。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）をエクスポネンシャルバックオフで実装。
    - 成果は ai_scores テーブルへ冪等的に（DELETE → INSERT）保存。
    - テスト容易性: _call_openai_api をモック差替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を用いたデータ取得、ma200_ratio 計算、マクロキーワードでのニュース抽出を実装。
    - OpenAI 呼び出しは独立実装で、API エラー時は macro_sentiment=0.0 とするフェイルセーフ。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER、ROE）等の定量ファクター計算関数を実装。
    - DuckDB を用いた SQL ベースの計算。lookahead バイアスを避ける設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）などの解析ユーティリティを実装。
  - zscore_normalize を data.stats から再エクスポート。

- データ基盤（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar）と営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB に登録のない日は曜日ベース（平日）でフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等更新。バックフィルおよび健全性チェック実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult）。
    - ETL パイプライン骨組みの実装（差分取得、保存、品質チェック呼び出し、バックフィルの扱い方針）。
    - quality モジュールと連携して品質問題を収集し、処理継続方針を採用。

### Changed
- 設計方針（全域）
  - 全てのデータ処理関数はルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
  - DuckDB を主なオンボード分析 DB として利用し、SQL と Python を併用した実装を採用。
  - DB への書き込みは可能な限り冪等性（DELETE → INSERT / ON CONFLICT）を意識。

### Fixed / Robustness
- .env パーサの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
  - ファイル読み込み失敗時に warnings.warn を出力して安全にフォールバック。
- OpenAI API 呼び出し周りの耐障害性向上
  - RateLimitError / APIConnectionError / APITimeoutError / APIError の扱い分け、5xx 系はリトライ、非 5xx はフォールバックする挙動を実装。
  - JSON パース失敗時に最外の { } を抽出して復元を試みるフォールバックロジックを追加。
- DuckDB 互換性考慮
  - executemany に空リストを渡すと失敗する点を考慮して事前チェックを追加（ai_scores への書き込み等で対応）。
  - SQL 文での NULL 伝播やウィンドウ関数の扱いを明確化（ATR の true_range 計算等）。

### Security / Requirements
- OpenAI・J-Quants・Kabu ステーション・Slack などの外部サービス連携には環境変数による API キー / トークン設定が必要（Settings で必須項目は _require によってチェック）。
- 自動 .env ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を用意し、テスト環境等でのキー漏洩リスクを低減可能。

### Notes / Known limitations
- 実行には DuckDB、OpenAI SDK、J-Quants クライアント（kabusys.data.jquants_client）等の外部依存が必要。
- AI 部分は外部 API（OpenAI）に依存するため、呼び出し回数制限やレイテンシに依存する。フェイルセーフ（スコア 0.0 やチャンクスキップ）を設けているが、運用時はレート管理・リトライ設定の調整が必要。
- 一部モジュールは外部の実装（jquants_client, quality 等）と連携する前提で実装されており、スタブ／テスト用モックでの検証を推奨。

---

もしリリースノートに追加してほしい詳細（例: 対象テーブルスキーマ、環境変数一覧、運用手順、互換性情報）があれば指示してください。