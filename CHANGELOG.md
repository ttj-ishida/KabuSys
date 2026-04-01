# CHANGELOG

すべての変更は Keep a Changelog の慣例に準拠します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

すべてのバージョンはセマンティックバージョニングに従います。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-01
初回リリース。本パッケージは日本株のデータプラットフォーム・リサーチ・AI支援スコアリング・運用支援を目的としたモジュール群を提供します。

### Added
- パッケージ基本情報
  - kabusys パッケージを導入。__version__ = 0.1.0、公開サブパッケージ: data, research, ai, monitoring, execution, strategy（__all__ に基づく）。
- 環境設定 / 設定管理
  - kabusys.config:
    - .env/.env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み（自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - export KEY=val 形式やクォート・エスケープ、インラインコメントに対応した堅牢なパーサを実装。
    - protected（既存 OS 環境変数）を尊重する上書きロジック。
    - 必須環境変数チェック（_require）と Settings クラスを提供。J-Quants / kabu / Slack / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）等を管理。
- AI モジュール
  - kabusys.ai.news_nlp:
    - raw_news / news_symbols からニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出し ai_scores テーブルへ書き込む機能。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で提供。
    - バッチ化（最大 20 銘柄/回）、記事数・文字数トリム、JSON Mode レスポンスのバリデーション、スコアの ±1.0 クリップ、エクスポネンシャルバックオフによるリトライを実装。
    - テスト容易性のため OpenAI 呼出し箇所は差し替え可能（関数単位で patch 可能）。
  - kabusys.ai.regime_detector:
    - ETF（1321）200日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次市場レジーム（bull/neutral/bear）を計算し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出、OpenAI 呼出し、リトライ、フェイルセーフ（API 失敗時に macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止を考慮したデータ参照方針を採用（date 未満条件など）。
- Data / ETL / カレンダー管理
  - kabusys.data.pipeline / ETLResult:
    - ETL 実行の結果構造体（ETLResult）を提供し、取得数・保存数・品質問題・エラー概要を集約。品質問題は辞書化して出力可能。
    - 差分更新・バックフィル・品質チェック方針に沿った実装方針を採用。
  - kabusys.data.calendar_management:
    - market_calendar テーブルを用いた営業日判定ユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック、探索上限で無限ループ防止等の安全策を実装。
    - calendar_update_job により J-Quants からの差分取得→冪等保存を行う仕組みを用意（バックフィル・健全性チェック含む）。
- Research（ファクター / 特徴量探索）
  - kabusys.research.factor_research:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）の計算関数を提供（prices_daily / raw_financials 参照）。
    - DuckDB を用いた SQL + Python 実装。データ不足時の None 扱い等の設計を採用。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic, Spearman）計算、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等非依存の標準ライブラリのみで実装。
  - kabusys.research.__init__ で主要関数を再公開。
- DB / DuckDB に関する互換性と注意点
  - DuckDB 0.10 の executemany の制約に配慮した実装（空リストチェックを実装して空の executemany を回避）。
  - market_regime / ai_scores 等への「DELETE -> INSERT」方式による部分更新（冪等性重視）。
- ロギング / フェイルセーフ / テスト性
  - OpenAI API エラー（RateLimit / Connection / Timeout / 5xx）に対する再試行とログ出力、非リトライ対象エラーは安全にスキップして継続する設計。
  - JSON パース失敗などは警告ログを出し、フェイルセーフ（0.0 や空辞書）で継続。
  - テスト時に差し替え可能な内部呼び出し関数（_call_openai_api 等）を用意。

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Removed
- 初回リリースのため該当なし

### Notes / Limitations
- OpenAI モデル: gpt-4o-mini を使用する想定。API キーは OPENAI_API_KEY（あるいは api_key 引数）で提供する必要あり。
- news_nlp の JSON Mode でも前後余計なテキストが混在する可能性を想定して復元ロジックを実装しているが、完全保険ではないため出力フォーマットは厳密に JSON を返すことが推奨される。
- calc_value では PBR・配当利回りは未実装（今後の拡張ポイント）。
- raw_news.datetime は UTC で保存されていることを前提に設計。
- 自動 .env ロードはプロジェクトルートの検出に依存する（.git または pyproject.toml）。配布後に適切な環境変数の設定方法をドキュメント化することを推奨。
- DuckDB の日付型戻り値等に対して互換性変換を行っている（_to_date 等）。

### Required environment variables（主な必須項目）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- （OpenAI を利用する場合）OPENAI_API_KEY

---

脚注: ここに記載した内容は現コードベースの実装および docstring から推測して作成しています。実運用前に README / ドキュメントを参照し、実際の環境変数や DB スキーマ（prices_daily, raw_news, raw_financials, market_calendar, ai_scores, market_regime 等）が正しくセットアップされていることを確認してください。