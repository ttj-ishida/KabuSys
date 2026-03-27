# Changelog

すべての重要な変更点をこのファイルに記録します。形式は「Keep a Changelog」に準拠します。  
詳細: https://keepachangelog.com/ja/1.0.0/

※本リポジトリの初期バージョン 0.1.0 のリリースノートです（リポジトリ内の src/kabusys/__init__.py の __version__ に基づく）。

## [Unreleased]

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買・データ基盤・リサーチ用のコアライブラリ群を実装。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（version 0.1.0）。公開モジュール: data, research, ai, config 等を含む。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動読み込み機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
  - .env パーサー: export KEY=val, シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数保護: OS 環境変数を保護して .env 上書きを制御可能。
  - Settings クラスを提供（プロパティ経由で必要設定を取得）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev の便宜プロパティ。

- AI モジュール（src/kabusys/ai）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols テーブルを集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）の JSON Mode でセンチメントスコアを取得。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST の記事を対象）を calc_news_window 関数で提供。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1 銘柄あたりの最大記事数・文字数制限でトークン肥大化を抑制。
    - API エラー（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフリトライを実装。
    - レスポンスバリデーション（JSON 抽出、results 配列、code/score 検証）とスコアの ±1.0 クリップ。
    - ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）し、部分失敗時に既存スコアを保護。
    - API キーは関数引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。
    - テスト容易性のため _call_openai_api をパッチ可能に実装。

  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出はホワイトリスト的なマクロキーワードでフィルタ。
    - OpenAI 呼び出しは JSON レスポンスを期待し、リトライ/バックオフおよびサーバーエラーの取り扱いを実装。
    - レジームスコアの算出とクリップ、閾値に基づくラベリング、および market_regime テーブルへの冪等書き込みを行う。
    - API キー解決は引数または OPENAI_API_KEY。未設定時は ValueError。

- データモジュール（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを利用した営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB 未取得時のフォールバック（曜日ベース、土日は非営業日扱い）。
    - next/prev/get_trading_days は DB 登録値を優先し、未登録日は曜日ベースで一貫した結果を返す。
    - 夜間バッチ calendar_update_job を実装し、J-Quants API から差分取得・バックフィル・健全性チェックを行う（jquants_client を利用）。
    - 探索上限・バックフィル・先読み日数等の定数を設定して安全性を確保。

  - pipeline / etl（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラス（ETL 実行結果の構造）を定義（取得件数・保存件数・品質問題・エラー一覧等）。
    - 差分取得のためのユーティリティ（最終日取得、テーブル存在チェック）を実装。
    - ETL の設計方針を踏まえ、品質チェックは問題を収集するが処理自体は継続（呼び出し元で扱う）。
    - data.etl モジュールで ETLResult を再エクスポート。

- Research モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム、ボラティリティ（ATR）、バリュー（PER/ROE）等の定量ファクター計算関数を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
      - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金・出来高比率を計算。
      - calc_value: raw_financials から直近の財務情報を取得して PER/ROE を計算。
    - すべて DuckDB の prices_daily / raw_financials を参照して SQL 主導で計算。外部 API へはアクセスしない。

  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。3 件未満で計算不能なら None。
    - rank: 値リストをランクに変換（同順位は平均ランク、丸め処理で ties の検出精度向上）。
    - factor_summary: カラムごとの基本統計量（count/mean/std/min/max/median）を計算。
    - Pandas 等に依存せず、標準ライブラリと DuckDB で実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI / 外部 API キーは引数経由または環境変数（OPENAI_API_KEY）で供給。必須チェックを実施し未設定時は明示的にエラー。

### Notes / Implementation details / 設計上の考慮点
- ルックアヘッドバイアス防止:
  - 各処理（score_news, score_regime, factor 計算等）は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - DB クエリは target_date 未満・未満等の排他条件を用いて将来情報を参照しないようにしている。
- フェイルセーフ:
  - OpenAI 呼び出しや外部 API の失敗は基本的に例外暴露ではなくログ出力してフェイルセーフ（ゼロスコアやスキップ）で継続する設計。ただし DB 書き込みの失敗は上位へ伝播する（トランザクション内で ROLLBACK 実行）。
- 冪等性:
  - 各種テーブルへの書き込みは DELETE→INSERT などの手法で冪等に行い、部分失敗時に既存データを不必要に上書きしない。
- DuckDB 互換性:
  - executemany に空リストを渡せない挙動を考慮して空チェックを行っている等の実装上の配慮あり。
- テスト容易性:
  - OpenAI への実際の呼び出しを差し替え可能（_call_openai_api を patch）とすることで単体テストが容易。
- 依存:
  - duckdb, openai を使用。

---

今後のリリースでは、API 実装の追加（kabu ステーション連携・注文実行ロジック）、モニタリング・Slack 通知、より豊富な品質チェックとドキュメンテーションを予定しています。