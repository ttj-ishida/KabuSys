# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog 準拠のフォーマットを採用しています。  
現在のパッケージバージョン: 0.1.0

## [0.1.0] - 2026-03-28
最初の公開リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報の追加（kabusys.__version__ = "0.1.0"）。
  - モジュール公開インターフェースの定義（__all__ に data / strategy / execution / monitoring）。

- 環境変数・設定管理（kabusys.config）
  - .env ファイルおよび環境変数を読み込む自動ローダーを実装（自動ロードの無効化は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
  - プロジェクトルートの検出ロジック（.git または pyproject.toml を起点に探索）を導入し、CWD に依存しない動作を実現。
  - .env 解析機能を強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - インラインコメント処理（クォートあり/なしの挙動を区別）
  - .env と .env.local の読み込み優先度管理（OS環境変数 > .env.local > .env）、既存 OS 環境変数の保護（protected keys）。
  - アプリケーション設定ラッパー Settings を提供。主要な設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須取得）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス
    - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL の検証ユーティリティ
    - is_live / is_paper / is_dev の便宜プロパティ

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメント分析（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へ送信しセンチメントを算出。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの記事数・文字数上限（デフォルト: 最大記事数 10 件、最大文字数 3000）によるトークン制御。
    - JSON Mode レスポンスのバリデーション機構を実装（results 配列の検証、未知コード無視、スコア数値化・クリップ ±1.0）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
    - 出力を ai_scores テーブルへ冪等的に書き込む（該当 date, code を DELETE → INSERT）。DuckDB executemany の空リスト制約を考慮。
    - テスト容易性: OpenAI 呼び出し箇所は _call_openai_api を内部に用意し、単体テストで差し替え可能。
    - ニュース収集ウィンドウ計算 calc_news_window を公開（JST ベースの前日 15:00 ～ 当日 08:30 相当を UTC naive datetime で返す）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）に基づく 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull / neutral / bear）を判定。
    - マクロキーワードによる raw_news フィルタリング、最大記事件数制限、OpenAI（gpt-4o-mini）呼び出し、JSON パース、リトライ・フェイルセーフを実装。
    - レジームスコア計算と閾値判定、market_regime への冪等トランザクション書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - API キー解決（引数優先、なければ環境変数 OPENAI_API_KEY）。未設定時は ValueError を発生させる。
    - 設計上、datetime.today() 等の参照を避け、ルックアヘッドバイアスを防止する実装方針を採用。

- データプラットフォーム機能（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを基に営業日判定 / 前後の営業日取得 / 期間内営業日リスト取得 / SQ 日判定などのユーティリティを実装。
    - DB の登録値を優先し、未登録日は曜日ベースのフォールバックを一貫して適用。
    - calendar_update_job を実装（J-Quants API からの差分取得 → 保存、バックフィル、健全性チェックを備える）。
    - 最大探索日数やバックフィル日数、先読み日数等の定数で安全策を導入。

  - ETL パイプライン基盤（kabusys.data.pipeline / etl）
    - ETLResult データクラスの追加（ETL 実行結果・品質問題・エラー概要の集約、辞書変換ユーティリティを含む）。
    - 差分取得、idempotent な保存（jquants_client の save_* を想定）、品質チェック（quality モジュール連携）の設計に則した実装方針を提示。
    - DuckDB に対する最大日付取得・テーブル存在チェック等のユーティリティ実装。

  - jquants_client / quality との連携設計（クライアントは外部モジュールとして想定、fetch/save の利用を前提）。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB の prices_daily / raw_financials テーブルから計算する関数を実装。
    - データ不足時の None 戻し、クエリは window/buffer を用いて過不足のないスキャンを実現。
    - 関数は (date, code) をキーとする dict のリストを返す設計。

  - 特徴量解析ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 多数ホライズン（デフォルト [1,5,21]）に対応、入力検証付き。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（同順位は平均ランク）。
    - rank, factor_summary 等の統計ユーティリティを実装（外部ライブラリに依存しない純 Python 実装）。
    - zscore_normalize を data.stats から再エクスポートするインターフェースを提供。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI / 外部 API キーは環境変数で管理する設計（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN 等）。コード内にハードコードしないことを想定。

Notes / 設計上の重要ポイント
- ルックアヘッドバイアス防止: ほとんどの処理で datetime.today() / date.today() を内部参照せず、明示的な target_date を受け取る API 設計を採用。
- フェイルセーフ: OpenAI 等の外部 API 失敗時はスコアを 0.0 にフォールバックする、あるいは該当チャンクをスキップすることでパイプライン全体の中断を防ぐ。
- テスト容易性: OpenAI 呼び出しを内部関数で囲い、unittest.mock.patch 等で差し替え可能にしている（_call_openai_api を差し替え）。
- DuckDB 特性考慮: executemany に空リストを渡せないバージョンへの対応（空チェックを入れてから executemany を呼ぶ）など互換性対策を行っている。
- DB 書き込みの冪等性: DELETE → INSERT のパターンや ON CONFLICT を想定する保存ロジックで再実行可能に設計。

今後の予定（例）
- strategy / execution / monitoring モジュールの具体実装・統合テスト
- J-Quants / kabu API クライアントの具現化と本番接続テスト
- 監視周り（Slack 通知等）の仕組み追加・改善

------
（補注）この CHANGELOG はコードベースから推測して作成したものであり、リリースノートの正式版は実際のリリース作業時に調整してください。