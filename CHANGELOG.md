# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

- 初期リリース以降の変更はここに記載します。

## [0.1.0] - 2026-04-09

初回リリース。本バージョンでは日本株自動売買システムのコア機能群を実装しています。主な追加点・設計方針は以下のとおりです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの公開（__version__ = 0.1.0）。
  - パッケージ API: data, strategy, execution, monitoring を __all__ で公開。

- 設定管理（kabusys.config）
  - .env/.env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
  - 拡張された .env パーサ（コメント、export プレフィクス、引用符内のエスケープ処理、インラインコメント処理などをサポート）。
  - 環境変数保護（既存 OS 環境変数を上書きしない、.env.local で上書き可能）。
  - Settings クラスによる型付きアクセサ（J-Quants / kabuステーション / LINE / DB パス / paper trading / 監視閾値 / 環境設定等）。
  - 値検証ロジック（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の有効値チェック）。
  - ユーティリティプロパティ（is_live / is_paper / is_dev）。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込み。
  - タイムウィンドウ計算（JST: 前日15:00〜当日08:30）を calc_news_window として実装。
  - バッチ処理（最大 20 銘柄/リクエスト）、記事トリム（最大記事数／文字数制限）を実装。
  - JSON Mode（厳密な JSON 出力）を前提としたパースと頑健なバリデーション（レスポンスの補正や部分失敗の保護）。
  - 再試行戦略（429, ネットワーク断, タイムアウト, 5xx に対する指数バックオフ）およびフォールバック（失敗時は当該チャンクをスキップ）。
  - DuckDB への冪等書き込み（DELETE → INSERT、空パラメータに対する互換性考慮）。
  - 公開 API: score_news(conn, target_date, api_key=None)。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を用いて日次レジーム（bull/neutral/bear）を判定。
  - マクロキーワードで raw_news をフィルターし、OpenAI によるセンチメント取得を実装（JSON レスポンス期待、リトライ / フェイルセーフ）。
  - レジームスコア合成と閾値判定、market_regime テーブルへの冪等書き込みを提供。
  - 公開 API: score_regime(conn, target_date, api_key=None)。

- リサーチ（kabusys.research）
  - ファクター計算: calc_momentum, calc_value, calc_volatility を実装。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None を返す挙動）。
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、平均売買代金、出来高比率。
    - Value: raw_financials を参照して PER / ROE を算出（EPS 欠損/0 の場合は None）。
  - 特徴量探索: calc_forward_returns（将来リターン）、calc_ic（スピアマンランク相関による IC）、factor_summary（統計サマリ）、rank（同順位は平均ランク）。
  - 研究ユーティリティとして zscore_normalize を data.stats から再エクスポート。
  - 公開 API を __all__ で整理。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベースのフォールバック（週末除外）。
    - calendar_update_job: J-Quants からの差分取得、バックフィル、健全性チェック、冪等保存を実装。
  - ETL 基盤（pipeline / etl）
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー等を収集・出力可能）。
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client と quality モジュールとの連携を前提）。

- モジュールエクスポート
  - ai パッケージから score_news を公開（kabusys.ai）。
  - research パッケージは主要関数を __all__ で整理。
  - data.etl は ETLResult を再エクスポート。

### 変更 (Changed)
- 設計方針全体
  - ルックアヘッドバイアス回避のため、各処理は datetime.today() / date.today() を参照せず、target_date ベースで処理する方針を徹底。
  - DuckDB を主要なローカル DB として採用し、SQL と Python 組合せでの処理を実装。
  - 外部 API 呼び出し（OpenAI / J-Quants）は失敗してもシステム全体を止めないフェイルセーフ動作（部分的スキップやデフォルト値で継続）。

### 修正 (Fixed)
- 初期実装段階の堅牢性対応
  - .env 読み込みエラー時の警告（warnings.warn）を追加。
  - OpenAI レスポンスの JSON パース失敗や API エラーに対して詳細ログとフォールバック（macro_sentiment=0.0 / チャンクスキップ）を実装。
  - DuckDB executemany の空リスト問題への対処（空時は実行しない）。

### 注記 (Notes)
- OpenAI クライアント呼び出しはテスト容易性のため内部で差し替え可能（ユニットテストでのモックを想定）。
- paper trading 関連（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）や監視設定（PID/KILL フラグ、リソース閾値）が設定可能。
- 一部機能（jquants_client, quality 等）は本コードでの参照を前提にしており、外部実装や接続設定が必要。

---

今後のリリースでは以下を優先的に検討します:
- strategy / execution / monitoring の詳細実装と統合テスト。
- ドキュメント整備（API 使用例、DB スキーマ、ETL 実行手順）。
- 性能改善（ETL パイプラインの並列化、DuckDB クエリ最適化）。
- 追加ユニットテストおよび CI/CD の整備。

（本 CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴の公式記録がある場合はそちらに合わせてください。）