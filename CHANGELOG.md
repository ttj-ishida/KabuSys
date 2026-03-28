# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

初回リリース。ライブラリ全体の基本機能を実装しました。主な追加点・設計上の注意点は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期版を追加。バージョンは src/kabusys/__init__.py の __version__ = "0.1.0"。
  - パッケージ公開インターフェースとして data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理
  - 環境変数/.env 読み込みユーティリティを追加（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込み。
    - .env のパースは export 形式・クォート・エスケープ・インラインコメント等に対応。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 実行環境等の設定プロパティを取得（必須変数は未設定時に ValueError を送出）。
    - 設定値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプライン用の基盤（src/kabusys/data/pipeline.py）を実装。
    - ETLResult データクラス（取得件数・保存件数・品質問題・エラー一覧など）を提供。
    - DBテーブルの最終日付取得やテーブル存在チェックといったユーティリティを実装。
    - 差分更新、バックフィル、品質チェック方針を実装設計として明示。
  - ETLResult を再エクスポートする etl モジュールを追加（src/kabusys/data/etl.py）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）を追加。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar が未登録の場合は曜日（平日）ベースでフォールバックする挙動。
    - calendar_update_job: J-Quants クライアント経由で差分取得して冪等に保存。バックフィル・健全性チェック実装。
    - 最大探索日数を設定して無限ループを防止。

- リサーチ（ファクター計算・特徴量解析）
  - research パッケージを追加（src/kabusys/research/*）。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）を計算（対象日ベース）。
    - ボラティリティ/流動性: 20日 ATR, ATR の割合, 平均売買代金, 出来高比率を計算。
    - バリュー: PER, ROE（raw_financials からの最新財務データを利用）。
    - 各関数は duckdb 接続を受け取り SQL を中心に計算。結果は date/code を含む dict リストで返す。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン）を実装。
    - IC（Spearman）を計算する calc_ic、rank、factor_summary（統計サマリ）を実装。
    - 外部依存（pandas 等）に依存せず標準ライブラリのみで実装。
  - research パッケージの __all__ で主要 API を公開。

- AI（ニュースNLP と市場レジーム判定）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を基に銘柄ごとに記事を集約し、OpenAI API（gpt-4o-mini, JSON mode）でセンチメントを評価。
    - チャンク処理（最大20銘柄/リクエスト）、1銘柄あたり記事数・文字数上限を実装。
    - 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ。その他はスキップして継続。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
    - DuckDB の executemany に関する空リスト制約を考慮した安全な DB 書き込み（DELETE → INSERT、部分書き換え）。
    - テスト容易化のため _call_openai_api を patch 可能。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とニュース LLM マクロセンチメント（重み 30%）を合成して日次レジームを判定（bull/neutral/bear）。
    - prices_daily / raw_news / market_regime を参照し、冪等に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出し失敗時は macro_sentiment=0.0 で継続するフェイルセーフ、OpenAI 呼び出しのリトライ/バックオフを実装。
    - テスト用に _call_openai_api を差し替え可能。
  - ai パッケージの __all__ で score_news / score_regime 等を公開。

- その他ユーティリティ
  - data パッケージで jquants_client など外部クライアントを利用する設計（実装ファイルは参照）。
  - ロギングを各モジュールで利用。重要な分岐や警告・エラーは logger に記録。

### 変更 (Changed)
- N/A（初回リリースにつき履歴なし）

### 修正 (Fixed)
- N/A（初回リリースにつき履歴なし）

### 注意点 / 既知の制約 (Notes / Known limitations)
- 多くの関数は target_date を引数として受け取り内部で datetime.today()/date.today() を参照しない設計。ルックアヘッドバイアス防止のためです。
- research モジュールは外部 API を呼ばず、DuckDB の prices_daily/raw_financials のみ参照するため安全にローカルで分析可能。
- OpenAI（LLM）呼び出しは gpt-4o-mini を想定しており、JSON mode（response_format）を利用。API レスポンスの形式に強く依存するため、モデルや API の挙動変更に注意が必要です。
- DuckDB のバージョン依存挙動（executemany の空配列不可や配列バインドの不安定さ）に対する対策を実装済みだが、環境差異による検証が必要です。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後やインストール環境では KABUSYS_DISABLE_AUTO_ENV_LOAD により明示的に無効化できる。

### セキュリティ (Security)
- API キー等の必須機密情報は Settings クラス経由で環境変数から取得。必須変数未設定時は明示的に ValueError を発生させるため、誤設定を検出しやすくしています。

---

今後のリリース案（例）
- strategy / execution / monitoring の具体実装とテストカバレッジ追加
- jquants_client の詳細実装・モック/テスト用フックの充実
- ai モジュールでのモデル切替やローカルモデルサポート
- パフォーマンス改善（DuckDB クエリ最適化、バッチサイズ自動調整）