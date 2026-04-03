# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-04-03

### Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ: src/kabusys/__init__.py によるバージョン管理と公開モジュール定義（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能実装（プロジェクトルート検出は .git または pyproject.toml ベース）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env の行パーサ実装（export プレフィックス対応、クォート内のエスケープ、インラインコメントの取り扱いルールなど）。
  - protected（OS側既存環境変数）を考慮した上書き制御。
  - Settings クラスでアプリケーション設定をプロパティとして公開（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定 等）。
  - 設定値バリデーション（KABUSYS_ENV、LOG_LEVEL の許容値チェック）と必須環境変数取得用の _require()。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC に変換して DB 比較）。
    - バッチ処理、銘柄ごとのトリム（最大記事数・最大文字数）によるトークン爆発対策。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフとリトライ。
    - レスポンスの厳密バリデーション（JSON 抽出、"results" 構造チェック、コード照合、数値検証）、スコアは ±1.0 にクリップ。
    - idempotent な DB 書き込み（該当 date/code を DELETE → INSERT）で部分失敗時の既存データ保護。
    - テスト容易性のため OpenAI 呼び出しラッパー関数を提供（patch による差し替えを想定）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio とマクロ記事タイトル抽出を行い、OpenAI（gpt-4o-mini）で macro_sentiment を取得。
    - API 障害時は macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
    - レジームスコアの合成と閾値に基づくラベリング、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT と ROLLBACK ハンドリング）。
    - API 呼び出しは独立実装でモジュール間の結合を避け、リトライ・エラー処理を強化。

  - 共通設計方針（AI 周り）
    - datetime.today()/date.today() を参照せず、target_date 指定による実行でルックアヘッドバイアスを防止。
    - OpenAI 呼び出しを安全に扱うためのエラーハンドリングとログ出力。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定 / SQ 判定 / next/prev_trading_day / get_trading_days の実装。
    - DB にデータがない場合は曜日ベース（平日のみ営業）でフォールバックする一貫した設計。
    - next/prev_trading_day の最大探索日数制限（_MAX_SEARCH_DAYS）による無限ループ防止。
    - calendar_update_job による J-Quants からの差分/バックフィル取得および保存（健全性チェック・バックフィル日数を考慮）。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスによる ETL 実行結果管理（取得数、保存数、品質問題、エラーの集約）。
    - 差分取得、backfill（デフォルト 3 日）による後出し修正吸収、品質チェック統合の設計。
    - jquants_client を用いた保存処理の呼び出しとエラー保護。

  - etl.py は pipeline.ETLResult を公開エクスポート。

- Research ツール群（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER、ROE）等の計算関数を実装。
    - DuckDB 上の SQL + Python による実装で外部 API に依存しない。
    - データ不足時の None 扱いやログ出力など健全な挙動。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（複数ホライズン対応、horizons のバリデーション）。
    - Information Coefficient（Spearman ρ）計算、ランク変換ユーティリティ（同順位は平均ランク）実装。
    - factor_summary による基本統計量算出（count/mean/std/min/max/median）。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

### Changed
- （初回公開につき該当なし）

### Fixed
- （初回公開につき該当なし）

### Notes / 実装上の重要ポイント
- DB 書き込みは冪等性を意識しており、部分失敗時に既存データを不必要に消さない設計（ai_scores / market_regime 等）。
- OpenAI とのやり取りはいずれも JSON Mode を期待しつつ、余計な前後テキスト混入への耐性（最外の {} を抽出して復元）を持たせている。
- テスト容易性を考慮し、OpenAI 呼び出しはモジュール内でラップしており、unittest.mock.patch による差し替えが可能。
- ルックアヘッドバイアスを避けるため、すべての解析手順は target_date 引数に依存しており、内部で現在日時を直接参照しない設計を徹底している。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの追加実装と統合テスト
- ドキュメント（API リファレンス・運用手順）の整備
- CI 上での自動テスト・型チェック・静的解析の導入

（この CHANGELOG はコードから推測して作成しています。実際のリリースノートには追加のコンテキストや既知の制限事項を含めることを推奨します。）