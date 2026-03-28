Keep a Changelog 準拠 — CHANGELOG.md

すべての変更は https://keepachangelog.com/ja/ に従って記載しています。

[0.1.0] - 2026-03-28
===================

Added
-----
- パッケージ初期リリース "KabuSys" を追加。
  - パッケージメタ: __version__ = "0.1.0"、トップレベル __all__ に data, strategy, execution, monitoring を公開。

- 環境設定 / 起動周り
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装（kabusys.config）。
    - プロジェクトルートの検出はパッケージ内ファイル位置を起点に .git または pyproject.toml を探索するため、CWD に依存しない。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサに次を実装:
    - 空行・コメント行（#）のスキップ、export プレフィックスのサポート。
    - シングル/ダブルクォート対応（バックスラッシュエスケープ考慮）。
    - クォートなし値のインラインコメント処理（直前がスペース/タブの '#' をコメントとみなす）。
  - Settings クラスを追加し、主要設定をプロパティで取得（必須キーは未設定時に ValueError を送出）。
    - J-Quants, kabu API, Slack, データベースパス、環境名（development/paper_trading/live）やログレベル検証など。

- AI モジュール（kabusys.ai）
  - news_nlp モジュールを実装:
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を評価し ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（最大 20 銘柄／リクエスト）、1 銘柄あたり最大記事数・文字数のトリム、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンスの堅牢なバリデーションとスコアの ±1.0 クリップ、部分成功時の DB 置換戦略（DELETE → INSERT）で既存データ保護。
    - テスト容易性のため _call_openai_api 等の差し替え差分を考慮。
  - regime_detector モジュールを実装:
    - ETF コード 1321（Nikkei 225 連動型）200 日移動平均乖離（重み 70%）と news_nlp 由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - LLM によるマクロセンチメント評価は最大 N 記事を抽出し gpt-4o-mini を利用。API エラー／パース失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を行い、失敗時は ROLLBACK を試みる。
    - ルックアヘッドバイアス回避設計（datetime.today() を参照しない、prices_daily のクエリは date < target_date を使用）。

- データ / ETL（kabusys.data）
  - ETL パイプライン基盤を実装（pipeline.ETLResult を公開）。
    - 差分取得、backfill（デフォルト 3 日）、品質チェック（quality モジュールと連携）という設計方針を実装。
    - ETLResult dataclass: 実行統計、品質問題、エラーメッセージ、便利な has_errors / has_quality_errors / to_dict を提供。
  - calendar_management モジュールを実装:
    - market_calendar を用いた営業日判定ヘルパー（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - market_calendar 未取得時は曜日ベース（土日除外）でフォールバックし、一貫した挙動を確保。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル期間や健全性チェック（future date の上限）を実装。
    - 最大探索範囲の上限（_MAX_SEARCH_DAYS）で無限ループを防止。
  - ETL とカレンダー更新ジョブは jquants_client 経由の fetch/save を利用する設計。

- リサーチ（kabusys.research）
  - factor_research モジュールを実装:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）を DuckDB 上で計算する関数（calc_momentum, calc_volatility, calc_value）。
    - 入力は DuckDB 接続（prices_daily, raw_financials 等）で、外部発注やネットワークアクセスは行わない。
  - feature_exploration モジュールを実装:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: スピアマンランク相関）、rank（同順位は平均ランク）、統計サマリー（factor_summary）を提供。
    - pandas 等に依存せず標準ライブラリのみで実装。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Deprecated
----------
- （初回リリースのため該当なし）

Removed
-------
- （初回リリースのため該当なし）

Security
--------
- 環境変数必須値（OpenAI API キー、Slack トークン等）は未設定時に ValueError を投げることで明示的な失敗を行い、誤動作を防止。
- .env 読み込みは既存 OS 環境変数を上書きしないデフォルト挙動を採用し、.env.local を使った上書き制御を可能に。

Notes / 実装上の留意点
--------------------
- 多くの箇所で「ルックアヘッドバイアス防止」のために datetime.today() / date.today() を直接参照しない設計を採用（score_news / score_regime 等）。外部から target_date を与えることで deterministic なバッチ処理を目指しています。
- OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を使用しつつ、実際のレスポンスで余計な前後テキストが混入することを考慮した復元ロジックを備えています。
- テスト容易性を考慮して、OpenAI 呼び出しや時間待機（sleep）等を差し替え可能な内部実装となっています（unittest.mock.patch を想定）。
- DuckDB のバージョン互換性（executemany に空リストを渡せない等）を考慮した防御的実装を行っています。

今後の TODO（想定）
------------------
- strategy / execution / monitoring モジュールの具体実装（現状トップレベルで公開のみ）。
- 更なる品質チェックルール追加とアラート（Slack）連携。
- テストカバレッジ拡充（ユニット・統合テスト）。
- OpenAI 呼び出しの抽象化オプション（Local LLM や別プロバイダ対応）。

バージョン 0.1.0 に関する問題報告や改善提案はリポジトリの Issue にお願いします。