# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

- リリースポリシー: すべての公開リリースはセマンティックバージョニングに従います。

## [Unreleased]

（現在未リリースの変更点はここに記載します）

## [0.1.0] - 2026-04-09

### Added
- パッケージ初回リリース (kabusys 0.1.0)
  - 基本パッケージ情報
    - src/kabusys/__init__.py にてパッケージ名説明と __version__ を追加。
    - __all__ で主要サブパッケージ（data, strategy, execution, monitoring）を公開。

  - 環境設定管理
    - src/kabusys/config.py
      - .env ファイルおよびOS環境変数から設定を読み込む自動ロード機能を実装。
      - プロジェクトルートの自動検出（.git または pyproject.toml を基準）を実装し、CWD に依存しないロードを実現。
      - .env のパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメントの扱い等）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
      - Settings クラスを提供し、J-Quants / kabuAPI / LINE / DB パス / 監視設定 / システム設定等のプロパティを環境変数から安全に取得。
      - env, log_level, paper_fill_mode 等の値検証と有効値チェック（不正な値は ValueError を送出）。
      - 保護された OS 環境変数を上書きしないロジック（.env 読み込み時の protected 処理）。

  - AI 系機能（OpenAI 統合）
    - src/kabusys/ai/news_nlp.py
      - ニュース記事を銘柄単位に集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントを -1.0〜1.0 のスコアで評価。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
      - バッチ処理（最大 20 銘柄/APIコール）や記事数・文字数トリム制御を実装（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライ処理を実装。
      - レスポンスの堅牢なバリデーション (_validate_and_extract) とスコアの ±1.0 クリップ。
      - 書き込みは部分冪等性を考慮し、取得できたコードのみ DELETE→INSERT で置換（DuckDB の executemany 空リスト制約に配慮）。
      - テスト容易性向上のため OpenAI 呼び出しは _call_openai_api で切り出し、テスト用にモック差替えが可能。

    - src/kabusys/ai/regime_detector.py
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
      - prices_daily, raw_news, market_regime テーブルを参照・更新（冪等的な BEGIN / DELETE / INSERT / COMMIT トランザクション）。
      - マクロニュース抽出（キーワードベース）と LLM 呼び出しのリトライ・フェイルセーフ（失敗時 macro_sentiment = 0.0）を実装。
      - ルックアヘッドバイアス回避のため、date 未満のデータのみを参照し、datetime.today() を参照しない設計。
      - OpenAI 呼び出しは内部で切り出し、news_nlp と実装を分離（モジュール結合を低減）。

  - Data / ETL / カレンダー管理
    - src/kabusys/data/pipeline.py
      - ETL パイプライン向けの ETLResult データクラスを実装（取得数・保存数・品質問題・エラー一覧等を保持）。
      - 差分更新、バックフィル、品質チェックの設計方針を反映（定数やデフォルト動作を定義）。
      - ETLResult.to_dict() により品質問題を辞書化して監査ログ用途に利用可能。

    - src/kabusys/data/etl.py
      - pipeline.ETLResult を公開インターフェースとして再エクスポート。

    - src/kabusys/data/calendar_management.py
      - JPX カレンダー管理機能を実装（market_calendar テーブルの読み書き、J-Quants からの差分取得ジョブ calendar_update_job）。
      - 営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
      - DB 登録がない場合の曜日ベースのフォールバック、DB 値優先の一貫した挙動、最大探索日数による無限ループ防止を実装。
      - calendar_update_job はバックフィル、健全性チェック、J-Quants からの取得・保存処理のエラーハンドリングを実装。

  - Research / ファクター計算と特徴量探索
    - src/kabusys/research/factor_research.py
      - モメンタム, ボラティリティ（ATR・平均売買代金・出来高比率）, バリュー（PER, ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
      - DuckDB 上の SQL ウィンドウ関数を活用して効率的に計算。データ不足時の None 扱いなど堅牢な設計。
      - 計算結果は (date, code) をキーとする dict のリストで返す。

    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）: 任意ホライズンのリターンをまとめて取得できる SQL ベース実装。
      - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関に基づくファクター有効性評価（欠損レコードや同順位対応に配慮）。
      - ランク変換ユーティリティ rank（同順位は平均ランク、丸め誤差対策あり）。
      - 統計サマリー機能 factor_summary（count/mean/std/min/max/median）。

  - モジュール再エクスポート
    - src/kabusys/ai/__init__.py で score_news を公開。
    - src/kabusys/research/__init__.py で主要関数群と zscore_normalize を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー等の秘匿情報は環境変数経由で取得する設計（.env を直接埋め込むことを避ける運用を想定）。
- .env 読み込みでは既存 OS 環境変数の保護機構を備える（protected set）。

### Notes / 設計上の重要な判断
- ルックアヘッドバイアス防止:
  - AI 解析およびファクター計算は内部で datetime.today() / date.today() を参照しない方針を採用。常に明示的な target_date を受け取り、prices_daily のクエリは target_date 未満などの排他条件を利用。
- フェイルセーフ:
  - OpenAI や外部 API の一時的障害に対してはリトライやフォールバック値（例: macro_sentiment=0.0）で処理を継続する設計を採用。
- テスト容易性:
  - OpenAI への生 API 呼び出しを行う関数は内部で切り出しており、単体テスト時に unittest.mock.patch で差し替え可能。
- DuckDB 互換性配慮:
  - executemany に空リストを与えないチェックなど、DuckDB の既知の挙動に配慮した実装を行っている。

（以降のリリースでは、バグ修正・API 変更・性能改善・新しいファクター追加等を個別のセクションで記載します）