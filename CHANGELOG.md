# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

（該当なし）

## [0.1.0] - 2026-03-31

最初の公開リリース。日本株自動売買プラットフォームのコアライブラリを含む初期実装を追加。

### Added
- パッケージの基本情報
  - パッケージ名 kabusys、バージョン 0.1.0 を src/kabusys/__init__.py に定義。
  - __all__ で主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定・自動ロード
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ローダを実装（src/kabusys/config.py）。
  - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索して行うため CWD に依存せず配布後も動作。
  - .env パーサは export KEY=val 形式、クォート文字（' "）およびバックスラッシュエスケープ、インラインコメントを考慮して正しくパース。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスで主要設定値をプロパティとして提供（J-Quants、kabu API、Slack、DB パス、環境・ログレベル判定など）。必須値未設定時は ValueError を送出。

- AI / ニュース処理（kabusys.ai）
  - news_nlp モジュールを実装（src/kabusys/ai/news_nlp.py）。
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を評価して ai_scores テーブルへ書き込む。
    - バッチ処理（最大 _BATCH_SIZE＝20 銘柄）や 1 銘柄あたりの最大記事数/文字数制限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）を実装。
    - JSON Mode を使った API 呼び出し、レスポンスのバリデーション／パース、数値化・クリップ（±1.0）を実装。
    - 429・ネットワーク切断・タイムアウト・5xx に対する指数バックオフリトライを実装。その他のエラーはログ記録して当該チャンクをスキップするフェイルセーフ設計。
    - タイムウィンドウは JST 基準（前日 15:00 〜 当日 08:30）を UTC に変換して計算する calc_news_window を提供。
    - テスト容易性を考慮し、内部の OpenAI 呼び出し関数（_call_openai_api）をモック可能に設計。

  - regime_detector モジュールを実装（src/kabusys/ai/regime_detector.py）。
    - ETF コード 1321 の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定。
    - マクロニュース抽出（キーワードベース）→ OpenAI でセンチメント評価 → スコア合成 → market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API エラー時のフォールバック（macro_sentiment=0.0）やリトライロジック、JSON パース例外ハンドリングを実装。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を内部で参照しない設計。

- Data モジュール（kabusys.data）
  - ETL パイプラインの公開インターフェース ETLResult を追加（src/kabusys/data/pipeline.py / etl.py）。
    - ETL 実行結果を表す dataclass（target_date, fetched/saved カウント, quality_issues, errors, ヘルパー属性）を実装。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - J-Quants API からの差分取得を行う calendar_update_job とバックフィル／健全性チェック実装。
    - DB 登録が不十分な場合は曜日ベースでフォールバックする等、堅牢な挙動を確保。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py）
    - 差分更新、バックフィル、品質チェックフック（quality モジュール連携）を想定した ETLResult を中心とした基盤実装（J-Quants クライアント経由の保存処理を想定）。

- Research モジュール（kabusys.research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum：1M/3M/6M リターン、200 日 MA 乖離の算出。
    - Volatility / Liquidity：20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - Value：PER（EPS が 0 または欠損時は None）、ROE（raw_financials からの最終値）。
    - DuckDB を用いた SQL ベース実装で、外部 API へはアクセスしない設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（スピアマンランク相関）calc_ic、ランク変換ユーティリティ rank、ファクター統計要約 factor_summary を実装。
    - pandas 等に依存せず標準ライブラリのみで処理。

- 汎用実装・設計方針の共有
  - 多くのモジュールで「ルックアヘッドバイアス防止」の方針を採用（date.today()/datetime.today() を直接参照しない）。
  - DuckDB を主要なストレージとして想定（型変換・日付処理のユーティリティを提供）。
  - 各種 DB 書き込みは冪等性（DELETE→INSERT、ON CONFLICT）やトランザクション（BEGIN/COMMIT/ROLLBACK）を考慮して実装。
  - ロギング（warnings / logger）を適切に配置し、API 失敗や部分失敗時にも継続するフェイルセーフ設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### Notes / Implementation details
- OpenAI クライアントは openai.OpenAI を用いており、API キーは引数注入または環境変数 OPENAI_API_KEY から解決される。未設定時は ValueError を送出するため呼び出し側で管理が必要。
- .env のロードでは OS 環境変数を保護するため .env の上書きを制御し、.env.local を用いて上書き可能にしている。
- DuckDB の executemany は空リストバインドに注意（コード内で空チェックを行っている）。
- テスト容易性のため、OpenAI 呼び出し関数はモック可能な独立関数として実装されている（unittest.mock.patch 等で差し替え可能）。

---

今後の予定（例）
- strategy / execution / monitoring サブパッケージの実装拡充（実際の発注ロジック、監視・アラート機能）。
- J-Quants / kabu API クライアントの詳細実装・安定化。
- テストカバレッジ拡充と CI の導入。