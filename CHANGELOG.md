# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを用います。

※このCHANGELOGは提供されたコードベースの内容から推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-29
初回リリース。本バージョンでは日本株自動売買システムのコアライブラリ群をまとめて導入しています。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。バージョン情報を `__version__ = "0.1.0"` として公開し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で露出。

- 設定管理
  - 環境変数／.env 読込みモジュール（src/kabusys/config.py）。
    - プロジェクトルート検出（.git / pyproject.toml）に基づく .env 自動ロード。
    - .env と .env.local の優先度（OS 環境変数 > .env.local > .env）を実装。
    - export 形式やシングル/ダブルクォート、エスケープ、インラインコメント等に対応した堅牢な行パーサー。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 必須環境変数チェック `_require` と Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 実行環境・ログレベル検証等）。
    - 有効な実行環境（development/paper_trading/live）・ログレベル（DEBUG/INFO/...）のバリデーション実装。

- AI（自然言語処理）機能
  - ai パッケージ初期化（src/kabusys/ai/__init__.py）。
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - 指定タイムウィンドウの raw_news を集約して銘柄単位にまとめ、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大20銘柄/チャンク）、記事数/文字数のトリム、JSON Mode 出力のバリデーション、スコアのクリップ処理を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、API呼び出しの差し替えを想定した設計（テスト用に _call_openai_api をモック可能）。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）で冪等性と部分失敗耐性を確保。
    - ルックアヘッドバイアス対策のため datetime.today() を直接参照しない設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、news_nlp によるマクロセンチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - OpenAI 呼び出し（JSON mode）とリトライ／エラーハンドリング、API失敗時のフェイルセーフ（macro_sentiment=0.0）。
    - DuckDB からのデータ取得、レジームスコア合成、market_regime テーブルへの冪等トランザクション書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - news_nlp とモジュール結合しない方針（_call_openai_api 等をそれぞれ独立実装）でテストと保守性を向上。

- データプラットフォーム（DuckDBベース）
  - data パッケージと ETL 周りの実装（src/kabusys/data/...）
    - ETL 結果データクラス ETLResult と再エクスポート（src/kabusys/data/etl.py, pipeline.py）。
      - ETLResult に品質チェック結果やエラー一覧を格納、has_errors / has_quality_errors 等のヘルパー、辞書化メソッドを提供。
    - ETL パイプラインユーティリティ（src/kabusys/data/pipeline.py）
      - 差分取得、バックフィル、品質チェック統合のためのユーティリティを提供。
      - DuckDB のテーブル存在チェックや最終日取得などの内部ユーティリティを実装。
    - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
      - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
      - DB にカレンダー情報がない/不完全な場合は曜日ベースのフォールバックを行う一貫した設計。
      - JPX カレンダー差分取得ジョブ calendar_update_job を実装し、J-Quants クライアント経由でのフェッチ → 保存フローを提供。バックフィル、健全性チェックを実装。

- リサーチ（ファクター計算・特徴量解析）
  - research パッケージ初期化（src/kabusys/research/__init__.py）。
  - ファクター計算群（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日ATR、相対ATR、20日平均売買代金、出来高比率）、Value（PER/ROE）を DuckDB 上で計算する関数を追加。
    - データ不足時の None 処理、営業日スキャンバッファ、SQL ウィンドウ関数を活用した実装。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン、範囲チェック）、IC（Spearman の ρ）計算 calc_ic、rank 関数、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存しない純標準ライブラリ実装。ランクの同順位処理は平均ランクを返す。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの取扱いは引数注入または環境変数 OPENAI_API_KEY を使用する設計とし、キーが未設定の場合は明示的に ValueError を発生させることで安全なフェールを実現。

### Notes / Implementation details
- DuckDB を主要なローカルデータストアとして利用。多くの処理は SQL（ウィンドウ関数等）で記述され、結果は Python dict/list 形式で返却。
- 外部 API 呼び出し（J-Quants / OpenAI）は例外処理とリトライ、フェイルセーフを組み込み、部分失敗がシステム全体を停止させない設計。
- ルックアヘッドバイアス防止のため、各スコアリング/計算関数は target_date を受け取り内部で date.today() 等を直接参照しない実装。
- テスト容易性を考慮し、OpenAI 呼び出しを差し替えられるようにしている（unittest.mock.patch など）。

---

既知の未実装・今後の改善点（コードから推測）
- PBR や配当利回りなど、バリューファクターの追加（コメントで未実装と明記）。
- jquants_client モジュールの実装詳細（ここでは呼び出しを使用しているが、実体は別ファイルで提供される想定）。
- strategy / execution / monitoring サブパッケージの詳細は本差分では含まれておらず、今後の拡張対象。

（以上）